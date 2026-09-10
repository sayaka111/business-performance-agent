import hashlib
from pathlib import Path

from business_performance_agent.runtime.state import WorkflowState
from business_performance_agent.llm.client import MockLLMClient
from business_performance_agent.models.schemas import BoundaryError
from business_performance_agent.skills import (
    contribution_analysis,
    dimension_drilldown,
    evidence_validate,
    metric_decompose,
    anomaly_evaluate,
)

from tests.helpers import Harness


class KnowledgeSkillTests(Harness):
    def test_knowledge_defensive_copy_and_unchanged_sources(self):
        metric = self.knowledge.get_metric("aov")
        metric["formula"] = "0"
        self.assertEqual(
            self.knowledge.get_metric("aov")["formula"], "gross_gmv / orders"
        )
        self.run_agent(MockLLMClient())
        for path, digest in self.engine.trace["spec_fingerprints"].items():
            self.assertEqual(
                hashlib.sha256(Path(path).read_bytes()).hexdigest(), digest
            )

    def test_unsupported_ids_block(self):
        with self.assertRaises(BoundaryError):
            self.knowledge.get_metric("invented")

    def test_no_relationship_selection_inside_skill(self):
        result = metric_decompose.execute(
            self.knowledge, self.query, **self.comparison_args()
        )
        self.assertEqual(
            set(result.result["available_relationships"]),
            {"orders_buyers_frequency", "orders_new_returning"},
        )

    def test_nonadditive_dimension_is_descriptive(self):
        for dimension in ("category", "product"):
            with self.subTest(dimension=dimension):
                result = dimension_drilldown.execute(
                    self.knowledge,
                    self.query,
                    **self.comparison_args(),
                    dimension_id=dimension,
                )
                self.assertFalse(result.result["contribution_supported"])
                self.assertTrue(result.limitations)
                blocked = contribution_analysis.execute(
                    self.knowledge,
                    self.query,
                    target_metric="orders",
                    target_baseline=100,
                    target_current=75,
                    components=result.result["segments"],
                    dimension_id=dimension,
                )
                self.assertEqual(blocked.reason, "non_additive_metric_dimension_pair")
                self.assertNotIn("effects", blocked.result)

    def test_knowledge_contract_and_initial_state(self):
        self.assertEqual(self.knowledge.get_metric("gross_gmv")["id"], "gross_gmv")
        relationship = self.knowledge.get_relationship("gross_gmv_orders_aov")
        self.assertEqual(relationship["target_metric"], "gross_gmv")
        self.assertTrue(
            self.knowledge.get_dimension("channel")["contribution_support"]["orders"]
        )
        state = WorkflowState()
        self.assertEqual(state.workflow_status, "initialized")
        self.assertEqual(state.current_node, "validate_input")
        self.assertEqual(state.depth, 0)
        self.assertEqual(state.evidence, [])
        state.validate(self.definition["state_schema"])

    def test_closure_conflict_blocks(self):
        result = contribution_analysis.execute(
            self.knowledge,
            self.query,
            target_metric="gross_gmv",
            target_baseline=1000,
            target_current=800,
            relationship_id="gross_gmv_orders_aov",
            components=[
                dict(metric_id="orders", baseline=10, current=8),
                dict(metric_id="aov", baseline=100, current=90),
            ],
        )
        self.assertEqual(result.reason, "semantic_conflict")

    def test_unknown_preserved_and_closes(self):
        result = dimension_drilldown.execute(
            self.knowledge, self.query, **self.comparison_args(), dimension_id="channel"
        )
        self.assertIn("unknown", [x["id"] for x in result.result["segments"]])
        self.assertEqual(sum(x["current"] for x in result.result["segments"]), 75)

    def test_period_level_customer_classification(self):
        p = self.raw["current_period"]
        new = self.adapter.metric("new_buyer_orders", p, {})
        buyers = self.adapter.metric("new_buyers", p, {})
        self.assertGreater(new, buyers)
        self.assertEqual(new + self.adapter.metric("returning_buyer_orders", p, {}), 75)

    def test_refund_does_not_change_gross(self):
        mapping = self.adapter.mapping["semantic_mapping"]
        row = self.adapter.rows[0]
        row[mapping["refunded_merchandise_amount"]] = 20
        period = self.raw["baseline_period"]
        self.assertEqual(self.adapter.metric("gross_gmv", period, {}), 10000)
        self.assertEqual(self.adapter.metric("net_gmv", period, {}), 9980)

    def test_threshold_boundaries(self):
        for relative, severity in [
            (0.1, "warning"),
            (-0.2, "critical"),
            (0.099, "normal"),
        ]:
            result = anomaly_evaluate.execute(
                self.knowledge,
                self.query,
                metric_compare_result={
                    "metric_id": "gross_gmv",
                    "relative_change": relative,
                },
                anomaly_policy=self.definition["policy"]["anomaly_policy"],
            )
            self.assertEqual(result.result["severity"], severity)

    def test_unsupported_causal_claim_rejected(self):
        self.assertEqual(
            evidence_validate.execute(
                self.knowledge,
                self.query,
                claim="Competitor bidding caused decline",
                evidence=[],
            ).status,
            "blocked",
        )
