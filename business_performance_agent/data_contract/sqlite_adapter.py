"""Configurable single-table SQLite adapter. Mapping is supplied by the operator."""

import hashlib
import json
import math
import re
import sqlite3
import time
from contextlib import closing
from pathlib import Path
from datetime import date
from .record_adapter import SemanticRecordAdapter
from .sql_utils import quote
from ..config.settings import ReadOnlyPolicy
from ..models.schemas import BoundaryError, Period


class SQLiteDatasetAdapter(SemanticRecordAdapter):
    def __init__(self, knowledge, database, policy=None, *, mapping):
        self.knowledge = knowledge
        self.path = Path(database).resolve()
        self.mapping = (
            json.loads(Path(mapping).read_text(encoding="utf-8"))
            if isinstance(mapping, (str, Path))
            else dict(mapping)
        )
        required = {
            "dataset_id",
            "table",
            "semantic_mapping",
            "capabilities",
            "complete_periods",
            "data_origin",
        }
        if not required <= self.mapping.keys() or self.mapping.keys() - required - {
            "source_contract",
            "read_limits",
        }:
            raise BoundaryError(
                "data_unavailable", "Incomplete SQLite mapping contract"
            )
        contract = self.mapping.get("source_contract", {})
        if contract and (
            contract.get("transaction_validity") != "completed_purchase_receipts"
            or not contract.get("approval_reference")
        ):
            raise BoundaryError(
                "semantic_conflict",
                "Source validity requires explicit approval reference",
            )
        if contract and "payment_success" in self.mapping["semantic_mapping"]:
            raise BoundaryError(
                "semantic_conflict",
                "Do not mix source validity and physical payment status",
            )
        if self.mapping["data_origin"] not in (
            "synthetic",
            "public_historical",
            "user_supplied",
        ):
            raise BoundaryError("data_unavailable", "Invalid data_origin")
        known = {d["id"] for d in knowledge.all("dimensions")}
        for metric in knowledge.all("metrics"):
            known.update(metric.get("required_fields", []))
            aggregate = re.match(
                r"(?:SUM|COUNT)\((?:DISTINCT )?(\w+)", metric["formula"]
            )
            if aggregate:
                known.add(aggregate.group(1))
        for dimension in knowledge.all("dimensions"):
            known.update(dimension.get("required_fields", []))
            if dimension.get("field_semantics"):
                known.add(dimension["field_semantics"])
        if set(self.mapping["semantic_mapping"]) - known:
            raise BoundaryError("semantic_conflict", "Unknown semantic mapping fields")
        self.capabilities = self.mapping["capabilities"]
        self.complete_periods = set()
        for value in self.mapping["complete_periods"]:
            period = Period(**value)
            self.complete_periods.add((period.start, period.end))
        self.semantic_consistent = True
        table = self.mapping["table"]
        columns = sorted(set(self.mapping["semantic_mapping"].values()))
        quote(table)
        for column in columns:
            quote(column)
        if not columns:
            raise BoundaryError("data_unavailable", "Empty semantic mapping")
        self.fingerprint = hashlib.sha256(self.path.read_bytes()).hexdigest()
        self._file_signature = (self.path.stat().st_size, self.path.stat().st_mtime_ns)
        self.policy = policy or ReadOnlyPolicy(
            query_timeout=self.mapping.get("read_limits", {}).get("query_timeout", 15),
            max_rows=self.mapping.get("read_limits", {}).get("max_rows", 250000),
            table_allowlist=(table,),
            column_allowlist=tuple(f"{table}.{c}" for c in columns),
        )
        self.operations = []
        values = self._select(
            "SELECT " + ", ".join(map(quote, columns)) + " FROM " + quote(table)
        )
        self.rows = [dict(zip(columns, row)) for row in values]
        paid = self.mapping["semantic_mapping"].get("payment_success")
        for row in self.rows:
            if paid and row.get(paid) is not None:
                if row[paid] not in (0, 1):
                    raise BoundaryError(
                        "data_quality_boundary", "payment_success must be boolean"
                    )
                row[paid] = bool(row[paid])
            for semantic in (
                "paid_at",
                "first_valid_paid_at",
                "original_order_paid_at",
            ):
                field = self.mapping["semantic_mapping"].get(semantic)
                value = row.get(field)
                if value is not None:
                    try:
                        if (
                            not isinstance(value, str)
                            or date.fromisoformat(value).isoformat() != value
                        ):
                            raise ValueError
                    except ValueError:
                        raise BoundaryError(
                            "data_quality_boundary", "Dates must use ISO YYYY-MM-DD"
                        ) from None
            for semantic in (
                "merchandise_amount",
                "valid_order_item_merchandise_amount",
                "quantity",
                "refunded_merchandise_amount",
                "confirmed_refunded_merchandise_amount",
            ):
                value = row.get(self.mapping["semantic_mapping"].get(semantic))
                if value is not None and (
                    not isinstance(value, (int, float)) or not math.isfinite(value)
                ):
                    raise BoundaryError(
                        "data_quality_boundary",
                        "Amounts and quantities must be finite numbers",
                    )
        self._source_query_id = self.operations[-1]["query_id"]
        self._period_cache = {}
        self._dimension_cache = {}
        self._quality_cache = {}

    def _record_read(self):
        self._check_snapshot()
        self.operations.append(
            {
                "query_id": f"SQL{len(self.operations) + 1:05d}",
                "operation": "cache_read",
                "source_query_id": self._source_query_id,
                "read_only": True,
                "status": "success",
            }
        )

    def _rows(self, metric, period, filters):
        self._record_read()
        key = (metric.get("time_attribution", "paid_at"), period.start, period.end)
        if key not in self._period_cache:
            self._period_cache[key] = super()._rows(metric, period, {})
        rows = self._period_cache[key]
        for dim, value in filters.items():
            index_key = (key, dim)
            if index_key not in self._dimension_cache:
                groups = {}
                for row in self._period_cache[key]:
                    groups.setdefault(self.dimension(row, dim, period), []).append(row)
                self._dimension_cache[index_key] = groups
            if len(filters) == 1:
                return self._dimension_cache[index_key].get(value, [])
            rows = [row for row in rows if self.dimension(row, dim, period) == value]
        return rows

    def quality(self, scope):
        self._record_read()
        import copy

        key = json.dumps(scope, sort_keys=True)
        if key not in self._quality_cache:
            self._quality_cache[key] = super().quality(scope)
        return copy.deepcopy(self._quality_cache[key])

    def _select(self, sql, parameters=()):
        self._check_snapshot()
        if not re.match(r"^\s*(SELECT|WITH)\b", sql, re.I):
            raise BoundaryError("data_unavailable", "Only SELECT / WITH SELECT allowed")
        if self.policy.query_timeout <= 0 or self.policy.max_rows <= 0:
            raise BoundaryError("data_unavailable", "Invalid query limits")
        started = time.monotonic()
        event = {
            "query_id": f"SQL{len(self.operations) + 1:05d}",
            "sql": sql,
            "parameters": list(parameters),
            "read_only": True,
            "status": "failed",
        }
        self.operations.append(event)

        def authorize(action, arg1, arg2, *_):
            if action == sqlite3.SQLITE_READ:
                return (
                    sqlite3.SQLITE_OK
                    if arg1 in self.policy.table_allowlist
                    and (not arg2 or f"{arg1}.{arg2}" in self.policy.column_allowlist)
                    else sqlite3.SQLITE_DENY
                )
            if action == sqlite3.SQLITE_SELECT:
                return sqlite3.SQLITE_OK
            if action == sqlite3.SQLITE_FUNCTION and arg2 in ("count", "min", "max"):
                return sqlite3.SQLITE_OK
            return sqlite3.SQLITE_DENY

        try:
            with closing(
                sqlite3.connect(self.path.as_uri() + "?mode=ro", uri=True)
            ) as db:
                db.execute("PRAGMA query_only=ON")
                db.set_authorizer(authorize)
                db.set_progress_handler(
                    lambda: int(time.monotonic() - started > self.policy.query_timeout),
                    1000,
                )
                result = db.execute(sql, parameters).fetchmany(self.policy.max_rows + 1)
                if len(result) > self.policy.max_rows:
                    raise BoundaryError(
                        "data_unavailable", "max_rows exceeded; no truncation permitted"
                    )
            if time.monotonic() - started > self.policy.query_timeout:
                raise BoundaryError("data_unavailable", "query_timeout")
            event.update(status="success", returned_rows=len(result))
            return result
        except sqlite3.Error:
            raise BoundaryError(
                "data_unavailable",
                "SQLite query denied, timed out, or invalid source data",
            ) from None

    def _check_snapshot(self):
        current = self.path.stat()
        if (current.st_size, current.st_mtime_ns) != self._file_signature:
            raise BoundaryError(
                "semantic_conflict",
                "SQLite snapshot changed during analysis; restart against a stable database",
            )
