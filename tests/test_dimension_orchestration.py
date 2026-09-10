"""Small integration regressions; no Golden Set imports or fixture identities."""

from unittest.mock import patch

from business_performance_agent.llm.client import MockLLMClient
from business_performance_agent.runtime.engine import Runtime
from business_performance_agent.runtime.router import Router
from business_performance_agent.llm.constrained_router import ConstrainedRouter
from tests.helpers import Harness


class DimensionOrchestrationTests(Harness):
    @staticmethod
    def contributions(result):
        return [
            e["payload"]["fact"]
            for e in result["evidence"]
            if e["payload"].get("kind") == "contribution"
        ]

    def test_explicit_gmv_dimensions_preserve_primary_without_llm(self):
        for dimension in ("channel", "category"):
            with self.subTest(dimension=dimension):
                self.raw["context"] = {"preferred_dimension": dimension}
                result = self.run_agent()
                self.assertEqual(result["primary_driver"]["metric_id"], "orders")
                self.assertTrue(
                    any(
                        f["target_metric"] == "gross_gmv"
                        and f.get("dimension_id") == dimension
                        and f["closed"]
                        for f in self.contributions(result)
                    )
                )
                self.assertTrue(
                    any(
                        d.get("rationale") == "explicit_legal_dimension"
                        and d["mode"] == "deterministic"
                        for d in self.engine.trace["router_decisions"]
                    )
                )

    def test_open_diagnosis_preserves_nested_math_then_localizes_orders(self):
        result = self.run_agent(MockLLMClient())
        path = result["diagnostic_path"]
        nested = next(
            i
            for i, p in enumerate(path)
            if p.get("relationship_id") == "orders_buyers_frequency"
        )
        dimension = next(
            i
            for i, p in enumerate(path)
            if p["metric_id"] == "orders" and p.get("dimension_id") == "channel"
        )
        self.assertLess(nested, dimension)
        self.assertEqual(sum(p.get("dimension_id") is not None for p in path), 1)
        self.assertTrue(
            any(
                f["target_metric"] == "orders"
                and f.get("dimension_id") == "channel"
                and f["closed"]
                for f in self.contributions(result)
            )
        )
        self.assertTrue(
            any("外部原因" in line and "无法" in line for line in result["limitations"])
        )
        self.assertTrue(
            all(
                c["evidence_level"] in ("direct", "derived") and c["evidence_refs"]
                for c in result["key_findings"]
            )
        )

    def test_orders_category_is_descriptive_without_strict_contribution(self):
        engine = Runtime(self.knowledge, self.query, self.definition, self.settings)

        def select_orders_category():
            engine.state.current_metric = "orders"
            engine.state.selected_relationship = None
            engine.state.selected_dimension = "category"
            return "dimension_drilldown"

        with patch.object(
            engine, "node_select_primary_driver", side_effect=select_orders_category
        ):
            result = engine.run(self.raw)["result"]
        self.assertTrue(
            any(
                p["metric_id"] == "orders" and p.get("dimension_id") == "category"
                for p in result["diagnostic_path"]
            )
        )
        self.assertFalse(
            any(
                f["target_metric"] == "orders" and f.get("dimension_id") == "category"
                for f in self.contributions(result)
            )
        )
        self.assertTrue(
            any("strict contribution prohibited" in x for x in result["limitations"])
        )

    def test_candidates_obey_knowledge_and_availability(self):
        self.run_agent(MockLLMClient())
        self.engine.state.current_metric = "buyers"
        self.engine.state.current_filters = {}
        self.engine.visited.clear()
        self.assertNotIn("channel", self.engine.dimensions())
        with patch.object(self.query, "dimension_available", return_value=False):
            self.assertEqual(self.engine.dimensions(), [])
        self.raw["context"] = {"preferred_dimension": "weather"}
        self.assertEqual(self.run_agent()["stop_reason"], "invalid_input")

    def test_preference_cannot_expand_allowed_set(self):
        router = Router(self.definition, ConstrainedRouter())
        trace = {"router_decisions": []}
        self.assertEqual(
            router.select(
                ["category"],
                {"preferred_dimension": "channel"},
                "select_next_dimension",
                trace,
            ),
            "category",
        )
        self.assertEqual(
            trace["router_decisions"][0]["allowed_candidates"], ["category"]
        )

    def test_explicit_dimension_still_respects_max_depth_and_no_anomaly(self):
        self.raw["context"] = {"preferred_dimension": "channel"}
        self.definition["policy"]["diagnosis_policy"]["max_depth"] = 1
        result = self.run_agent()
        self.assertEqual(result["stop_reason"], "max_depth_reached")
        self.assertNotIn("dimension_drilldown", self.engine.trace["nodes_executed"])
        for row in self.adapter.rows:
            if row["mock_paid_date"] == "2026-09-01":
                row["mock_goods_amount"] = 10000 / 75
        result = self.run_agent()
        self.assertEqual(result["stop_reason"], "not_anomaly")
        self.assertNotIn("dimension_drilldown", self.engine.trace["nodes_executed"])
