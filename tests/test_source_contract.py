import copy
import unittest
from tests import test_sqlite_adapter
from business_performance_agent.data_contract.sqlite_adapter import SQLiteDatasetAdapter
from business_performance_agent.tools.sqlite_query_tool import SQLiteQueryTool
from business_performance_agent.runtime.engine import Runtime
from business_performance_agent.models.schemas import BoundaryError
from business_performance_agent.workflows.definition import load_workflow


class SourceContractTests(unittest.TestCase):
    def setUp(self):
        test_sqlite_adapter.SQLiteTests.setUp(self)
        self.definition = load_workflow(self.settings.workflow)

    def source_mapping(self):
        mapping = copy.deepcopy(self.adapter.mapping)
        del mapping["semantic_mapping"]["payment_success"]
        mapping["source_contract"] = {
            "transaction_validity": "completed_purchase_receipts",
            "approval_reference": "test explicit approval",
            "limitations": ["Household entity; refund lifecycle unobserved."],
        }
        return mapping

    def test_source_validity_without_physical_payment_mapping(self):
        adapter = SQLiteDatasetAdapter(
            self.knowledge, self.path, mapping=self.source_mapping()
        )
        self.assertEqual(adapter.metric("gross_gmv", self.current, {}), 700)
        result = Runtime(
            self.knowledge, SQLiteQueryTool(adapter), self.definition, self.settings
        ).run(self.input)["result"]
        self.assertNotEqual(result["stop_reason"], "data_quality_boundary")
        self.assertTrue(any("Household" in x for x in result["limitations"]))

    def test_missing_approval_and_conflicting_status_rejected(self):
        for mutation in ("approval", "physical"):
            mapping = self.source_mapping()
            if mutation == "approval":
                del mapping["source_contract"]["approval_reference"]
            else:
                mapping["semantic_mapping"]["payment_success"] = "payment_success"
            with self.assertRaises(BoundaryError):
                SQLiteDatasetAdapter(self.knowledge, self.path, mapping=mapping)

    def test_explicit_unavailable_dimension_stops_safely(self):
        mapping = self.source_mapping()
        del mapping["semantic_mapping"]["channel"]
        adapter = SQLiteDatasetAdapter(self.knowledge, self.path, mapping=mapping)
        raw = dict(self.input, context={"preferred_dimension": "channel"})
        result = Runtime(
            self.knowledge, SQLiteQueryTool(adapter), self.definition, self.settings
        ).run(raw)["result"]
        self.assertEqual(result["stop_reason"], "data_quality_boundary")
        self.assertTrue(any("channel" in x for x in result["limitations"]))

    def test_period_cache_preserves_multifilter_results(self):
        expected = self.adapter.metric(
            "gross_gmv", self.current, {"channel": "paid_search"}
        )
        self.assertEqual(
            expected,
            self.adapter.segments("gross_gmv", "channel", self.current, {})[
                "paid_search"
            ],
        )
