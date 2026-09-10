import sqlite3
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from evals.live_runner import provider_metrics
from evals.support.holdout_fixture import construct, prepare
from evals.support.case_fixture import FixtureReviewRequired


class Phase2EvalTests(unittest.TestCase):
    periods = [
        dict(start="2026-07-01", end="2026-07-31"),
        dict(start="2026-08-01", end="2026-08-31"),
    ]

    def test_unit_offset_construction_from_input_constraints(self):
        rows, _ = construct(
            dict(
                description="保持Orders稳定",
                construction_requirements=[
                    "基期UPO=2.0 price=50",
                    "本期UPO=1.4 price=60",
                ],
            ),
            self.periods,
        )
        baseline = [r for r in rows if r["paid_at"] == self.periods[0]["start"]]
        current = [r for r in rows if r["paid_at"] == self.periods[1]["start"]]
        self.assertEqual(len(baseline), len(current))
        self.assertEqual(sum(r["quantity"] for r in current) / len(current), 1.4)
        self.assertEqual(
            sum(r["merchandise_amount"] for r in current) / len(current), 84
        )

    def test_missing_dimension_is_physically_absent(self):
        case = dict(
            case_id="physical_absence_probe",
            periods=dict(
                baseline="2026-07-01/2026-07-31", current="2026-08-01/2026-08-31"
            ),
            fixture_spec=dict(description="故意缺失channel语义字段"),
        )
        with TemporaryDirectory() as directory:
            database, mapping, metadata = prepare(case, Path(directory))
            with closing(sqlite3.connect(database)) as db:
                columns = [r[1] for r in db.execute("PRAGMA table_info(order_items)")]
            self.assertNotIn("channel", columns)
            self.assertNotIn('"channel"', mapping.read_text())

    def test_unsupported_recipe_requires_review(self):
        with self.assertRaises(FixtureReviewRequired):
            construct(dict(description="arbitrary unsupported data"), self.periods)

    def test_provider_errors_are_separate_from_structured_compliance(self):
        events = [
            dict(purpose="report", status="failed", http_status=503, attempt=1),
            dict(purpose="report", status="failed", http_status=429, attempt=2),
            dict(purpose="intent", status="success", attempt=1),
            dict(
                purpose="routing", status="failed", error_type="ValueError", attempt=1
            ),
        ]
        stats = provider_metrics(
            [
                dict(
                    actual=dict(
                        events=events,
                        report_metadata=dict(report_renderer="deterministic_fallback"),
                    )
                )
            ]
        )
        self.assertEqual(stats["provider_attempts"], 4)
        self.assertEqual(stats["provider_failures"], 2)
        self.assertEqual(stats["structured_output_compliance"]["value"], 0.5)
        self.assertEqual(stats["fallback_count"], 1)
        self.assertEqual(stats["retry_count"], 1)
        self.assertIsNone(provider_metrics([])["provider_success_rate"]["value"])
