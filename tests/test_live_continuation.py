import unittest

from evals.continue_live import completed, select_pending, provenance


class ContinuationTests(unittest.TestCase):
    def record(self, case_id, passed=True, **overrides):
        return (
            dict(
                case_id=case_id,
                execution_status="completed",
                grading_status="completed",
                overall_pass=passed,
                review_required=[],
                actual={"result": {}, "events": []},
            )
            | overrides
        )

    def test_preserves_pass_and_fail(self):
        records = [
            self.record("pass"),
            self.record("fail", False),
            self.record("interrupted", provider_interrupted=True),
            self.record("new", execution_status="not_run"),
        ]
        entries = [{"case_id": r["case_id"]} for r in records]
        self.assertEqual(
            [e["case_id"] for e in select_pending(entries, records)],
            ["interrupted", "new"],
        )

    def test_missing_result_is_not_completed(self):
        self.assertFalse(completed(self.record("a", actual={"result": None})))
        self.assertFalse(completed(self.record("a", review_required=["review"])))

    def test_inventory_mismatch_stops(self):
        with self.assertRaises(ValueError):
            select_pending([{"case_id": "a"}], [])

    def test_provenance_counts_fallback_without_changing_grade(self):
        record = self.record(
            "a",
            False,
            actual={
                "result": {},
                "events": [
                    {
                        "purpose": "report",
                        "status": "failed",
                        "attempt": 1,
                        "http_status": 503,
                    },
                    {
                        "purpose": "report",
                        "status": "failed",
                        "attempt": 2,
                        "http_status": 503,
                    },
                ],
                "report_metadata": {"report_renderer": "deterministic_fallback"},
            },
        )
        source = provenance(record, "deepseek", "run", "model")
        self.assertEqual(source["provider_attempts"], 2)
        self.assertEqual(source["provider_failures"], 2)
        self.assertEqual(source["retry_count"], 1)
        self.assertTrue(source["fallback_used"])
        self.assertFalse(record["overall_pass"])
