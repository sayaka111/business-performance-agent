from abc import ABC, abstractmethod
from dataclasses import asdict
import re
import time
import math
from ..config.settings import ReadOnlyPolicy
from ..models.schemas import BoundaryError


class QueryTool(ABC):
    @abstractmethod
    def metric(self, metric_id, period, filters): ...
    @abstractmethod
    def segments(self, metric_id, dimension_id, period, filters): ...
    @abstractmethod
    def quality(self, scope): ...
    @abstractmethod
    def relationship_available(self, relationship): ...
    @abstractmethod
    def dimension_available(self, dimension_id): ...


def validate_read_only_sql(sql, policy):
    """Conservative mock grammar, not a production SQL authorization parser."""
    identifier = r"[A-Za-z_][A-Za-z0-9_]*"
    select = rf"SELECT\s+({identifier}(?:\s*,\s*{identifier})*)\s+FROM\s+({identifier})"
    query = sql.strip()
    simple = re.fullmatch(select, query, re.I)
    cte = re.fullmatch(
        rf"WITH\s+({identifier})\s+AS\s*\(\s*{select}\s*\)\s*{select}", query, re.I
    )
    if simple:
        columns, table = simple.groups()
    elif cte:
        alias, inner_columns, table, columns, outer_table = cte.groups()
        if alias != outer_table or not set(map(str.strip, columns.split(","))) <= set(
            map(str.strip, inner_columns.split(","))
        ):
            raise BoundaryError("data_unavailable", "SQL CTE outside read-only grammar")
        columns = inner_columns
    else:
        raise BoundaryError(
            "data_unavailable",
            "Only restricted SELECT / WITH SELECT is accepted; writes and other SQL fail closed.",
        )
    if table not in policy.table_allowlist:
        raise BoundaryError("data_unavailable", "Table not allowlisted")
    if not policy.column_allowlist or not set(
        map(str.strip, columns.split(","))
    ) <= set(policy.column_allowlist):
        raise BoundaryError("data_unavailable", "Column not allowlisted")
    return True


class MockQueryTool(QueryTool):
    def __init__(self, adapter, policy=None):
        self.adapter = adapter
        self.policy = policy or ReadOnlyPolicy(
            column_allowlist=tuple(adapter.schema()[adapter.mapping["table"]])
        )
        self.calls = []

    def _run(self, operation, request, callback):
        table = self.adapter.mapping["table"]
        if table not in self.policy.table_allowlist:
            raise BoundaryError("data_unavailable", "Table not allowlisted")
        if self.policy.query_timeout <= 0:
            raise BoundaryError("data_unavailable", "query_timeout")
        if self.adapter.scan_size() > self.policy.max_rows:
            raise BoundaryError(
                "data_unavailable", "max_rows exceeded; no truncation permitted"
            )
        # This in-memory adapter scans a single table; require its full mapped schema.
        if not set(self.adapter.schema()[table]) <= set(self.policy.column_allowlist):
            raise BoundaryError("data_unavailable", "Column not allowlisted")
        started = time.monotonic()
        value = callback()
        if time.monotonic() - started > self.policy.query_timeout:
            raise BoundaryError("data_unavailable", "query_timeout")

        def finite(item):
            if isinstance(item, float) and not math.isfinite(item):
                raise BoundaryError("semantic_conflict", "Nonfinite query value")
            if isinstance(item, dict):
                for v in item.values():
                    finite(v)
            if isinstance(item, list):
                for v in item:
                    finite(v)

        finite(value)
        provenance = dict(
            query_id=f"Q{len(self.calls) + 1:05d}",
            dataset_id=self.adapter.mapping["dataset_id"],
            operation=operation,
            request=request,
            read_only=True,
        )
        self.calls.append(provenance)
        return value, provenance

    def metric(self, metric_id, period, filters):
        request = dict(metric_id=metric_id, period=period, filters=filters)
        value, provenance = self._run(
            "metric", request, lambda: self.adapter.metric(metric_id, period, filters)
        )
        return dict(value=value, provenance=provenance)

    def segments(self, metric_id, dimension_id, period, filters):
        value, provenance = self._run(
            "segments",
            dict(
                metric_id=metric_id,
                dimension_id=dimension_id,
                period=period,
                filters=filters,
            ),
            lambda: self.adapter.segments(metric_id, dimension_id, period, filters),
        )
        return dict(values=value, provenance=provenance)

    def quality(self, scope):
        value, _ = self._run("quality", scope, lambda: self.adapter.quality(scope))
        return value

    def relationship_available(self, relationship):
        metrics = relationship.get(
            "drivers", [c["metric"] for c in relationship.get("components", [])]
        )
        return all(
            self.adapter.capabilities.get(r, False)
            for r in relationship.get("requirements", [])
        ) and all(self.adapter.metric_available(m) for m in metrics)

    def dimension_available(self, dimension_id):
        return self.adapter.dimension_available(dimension_id)
