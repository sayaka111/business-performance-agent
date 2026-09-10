"""Generic SQLite contracts and synthetic data support; no Golden Set grading."""

import hashlib
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from business_performance_agent.config.settings import Settings
from business_performance_agent.data_contract.sqlite_adapter import SQLiteDatasetAdapter
from business_performance_agent.models.schemas import BoundaryError
from business_performance_agent.tools.knowledge_loader import KnowledgeLoader
from business_performance_agent.tools.sqlite_query_tool import SQLiteQueryTool
from business_performance_agent.runtime.engine import Runtime
from business_performance_agent.workflows.definition import load_workflow
from business_performance_agent.llm.client import MockLLMClient
from evals.support.fixture_builder import build_fixture, smoke_records, SMOKE_PERIODS
from evals.support.eval_sqlite_adapter import CanonicalEvalSQLiteAdapter


class SQLiteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "fixture.db"
        self.mapping = build_fixture(self.path, smoke_records(), SMOKE_PERIODS)
        self.settings = Settings(logs=Path(self.temp.name) / "logs")
        self.knowledge = KnowledgeLoader(self.settings.business / "knowledge")
        self.adapter = SQLiteDatasetAdapter(
            self.knowledge, self.path, mapping=self.mapping
        )
        self.baseline, self.current = SMOKE_PERIODS
        self.input = dict(
            metric_id="gross_gmv",
            baseline_period=self.baseline,
            current_period=self.current,
            filters={},
        )

    def test_metrics_and_canonical_dimensions(self):
        for metric, value in [
            ("gross_gmv", 700),
            ("orders", 7),
            ("buyers", 4),
            ("units", 14),
            ("aov", 100),
        ]:
            self.assertEqual(self.adapter.metric(metric, self.current, {}), value)
        self.assertEqual(
            self.adapter.segments("orders", "customer_type", self.current, {}),
            {"new": 7},
        )
        for dim in ("region", "channel", "campaign", "category", "product"):
            self.assertTrue(self.adapter.dimension_available(dim))
        self.assertEqual(self.adapter.metric("new_buyers", self.current, {}), 4)

    def test_readonly_limits_and_identifiers(self):
        digest = hashlib.sha256(self.path.read_bytes()).hexdigest()
        for sql in [
            "DELETE FROM order_items",
            "WITH x AS (SELECT 1) DELETE FROM order_items",
            "SELECT load_extension('evil')",
            "SELECT * FROM sqlite_master",
        ]:
            with self.assertRaises(BoundaryError):
                self.adapter._select(sql)
        for policy in [
            replace(self.adapter.policy, max_rows=1),
            replace(self.adapter.policy, query_timeout=0),
            replace(self.adapter.policy, column_allowlist=()),
        ]:
            with self.assertRaises(BoundaryError):
                SQLiteDatasetAdapter(
                    self.knowledge, self.path, policy, mapping=self.mapping
                )
        mapping = json.loads(self.mapping.read_text())
        mapping["table"] = "order_items; DROP TABLE order_items"
        with self.assertRaises(BoundaryError):
            SQLiteDatasetAdapter(self.knowledge, self.path, mapping=mapping)
        self.assertEqual(digest, hashlib.sha256(self.path.read_bytes()).hexdigest())

    def test_snapshot_and_quality_boundary(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("UPDATE order_items SET paid_at=NULL WHERE order_id=?", ("c0",))
        with self.assertRaises(BoundaryError):
            self.adapter.metric("orders", self.current, {})
        adapter = SQLiteDatasetAdapter(self.knowledge, self.path, mapping=self.mapping)
        runtime = Runtime(
            self.knowledge,
            SQLiteQueryTool(adapter),
            load_workflow(self.settings.workflow),
            self.settings,
            MockLLMClient(),
        )
        self.assertEqual(
            runtime.run(self.input)["result"]["workflow_status"], "blocked"
        )

    def test_workflow_and_trace(self):
        runtime = Runtime(
            self.knowledge,
            SQLiteQueryTool(self.adapter),
            load_workflow(self.settings.workflow),
            self.settings,
            MockLLMClient(),
        )
        output = runtime.run(self.input)
        self.assertEqual(output["result"]["workflow_status"], "completed")
        self.assertEqual(output["result"]["target"]["absolute_change"], -300)
        self.assertTrue(runtime.trace["query_operations"])

    def test_explicit_physical_mapping_and_origin(self):
        mapping = json.loads(self.mapping.read_text(encoding="utf-8"))
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("ALTER TABLE order_items RENAME TO sales")
            db.execute(
                "ALTER TABLE sales RENAME COLUMN merchandise_amount TO goods_total"
            )
        mapping["table"] = "sales"
        mapping["data_origin"] = "user_supplied"
        mapping["semantic_mapping"] = {
            k: "goods_total" if v == "merchandise_amount" else v
            for k, v in mapping["semantic_mapping"].items()
        }
        adapter = SQLiteDatasetAdapter(self.knowledge, self.path, mapping=mapping)
        self.assertEqual(adapter.metric("gross_gmv", self.current, {}), 700)
        self.assertEqual(adapter.mapping["data_origin"], "user_supplied")
        mapping["case_id"] = "not-allowed"
        with self.assertRaises(BoundaryError):
            SQLiteDatasetAdapter(self.knowledge, self.path, mapping=mapping)

    def test_filter_injection_and_unknown(self):
        self.assertEqual(
            self.adapter.metric("orders", self.current, {"channel": "x' OR 1=1 --"}), 0
        )
        self.assertEqual(self.adapter.metric("orders", self.current, {}), 7)

    def test_builder_reproducibility_and_no_answer_access(self):
        other = Path(self.temp.name) / "other.db"
        original = Path.read_text

        def guarded(path, *args, **kwargs):
            self.assertNotIn("expected", path.parts)
            self.assertNotIn("cases", path.parts)
            return original(path, *args, **kwargs)

        with patch.object(Path, "read_text", guarded):
            build_fixture(other, smoke_records(), SMOKE_PERIODS)
            adapter = CanonicalEvalSQLiteAdapter(self.knowledge, other)
            self.assertEqual(adapter.metric("orders", self.current, {}), 7)
        self.assertEqual(self.path.read_bytes(), other.read_bytes())
        with self.assertRaises(FileExistsError):
            build_fixture(other, [], SMOKE_PERIODS)
        with self.assertRaises(ValueError):
            build_fixture(
                Path(self.temp.name) / "bad.db", [{"expected": "answer"}], SMOKE_PERIODS
            )


if __name__ == "__main__":
    unittest.main()
