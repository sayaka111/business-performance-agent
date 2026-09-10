"""Software checks for Eval machinery, not assertions that Golden Cases pass."""

import copy
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from evals.runner import (
    ROOT,
    contracts,
    load_manifest,
    run_suite,
    aggregate,
    write_json,
)
from evals.support.case_fixture import (
    prepare_fixture,
    FixtureReviewRequired,
    workflow_input,
)
from evals.support.expected_gate import ExpectedGate
from evals.graders import CalculationGrader, WorkflowPathGrader, OverallCaseGrader


def sample_actual():
    scope = dict(metric_id="gross_gmv", filters={})
    fact = dict(
        target_metric="gross_gmv",
        relationship_id="gross_gmv_orders_aov",
        dimension_id=None,
        target_change=-20,
        effects=[
            dict(id="aov", effect=-20, role="aligned_driver"),
            dict(id="orders", effect=0, role="neutral"),
        ],
    )
    return dict(
        result=dict(
            target=dict(
                metric_id="gross_gmv",
                baseline_value=100,
                current_value=80,
                absolute_change=-20,
                relative_change=-0.2,
            ),
            workflow_status="completed",
            stop_reason="target_coverage_reached",
            primary_driver={"metric_id": "aov"},
            diagnostic_path=[
                dict(
                    metric_id="gross_gmv",
                    relationship_id="gross_gmv_orders_aov",
                    dimension_id=None,
                )
            ],
            evidence=[
                dict(
                    evidence_id="E1",
                    evidence_level="derived",
                    payload=dict(kind="contribution", scope=scope, fact=fact),
                )
            ],
            key_findings=[
                dict(
                    claim_id="C1",
                    claim="aov is the internal contribution driver of gross_gmv",
                    evidence_level="derived",
                    evidence_refs=["E1"],
                )
            ],
            warnings=[],
            limitations=[],
        ),
        trace=dict(
            state={"aligned_coverage": 1, "depth": 1},
            skills_called=[],
            router_decisions=[],
            query_operations=[],
        ),
        report="",
        isolation={"denied_operations": 0},
        execution_mode={"llm": "mock"},
    )


class EvalFrameworkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.contract = contracts(ROOT)

    def case(self, group, name):
        return json.loads(
            (ROOT / "evals/cases" / group / (name + ".json")).read_text(
                encoding="utf-8"
            )
        )

    def test_manifest_loads_twelve_without_expected_access(self):
        original = Path.read_text

        def guarded(path, *args, **kwargs):
            self.assertNotIn("expected", path.parts)
            return original(path, *args, **kwargs)

        with patch.object(Path, "read_text", guarded):
            self.assertEqual(len(load_manifest(ROOT / "evals/manifest.json")), 12)

    def test_fixture_bytes_do_not_depend_on_case_identity_or_focus(self):
        case = self.case("decomposition", "gmv_orders_driver_001")
        a, _, _ = prepare_fixture(case, self.path / "one")
        variant = dict(
            case,
            case_id="opaque_alternate",
            title="unrelated title",
            evaluation_focus=["CANARY_ANSWER"],
        )
        b, _, _ = prepare_fixture(variant, self.path / "two")
        self.assertEqual(a.read_bytes(), b.read_bytes())
        self.assertNotIn(b"CANARY_ANSWER", b.read_bytes())
        with closing(sqlite3.connect(a)) as db:
            values = db.execute(
                "SELECT paid_at,COUNT(DISTINCT order_id),SUM(merchandise_amount) FROM order_items GROUP BY paid_at ORDER BY paid_at"
            ).fetchall()
        self.assertEqual([(n, v) for _, n, v in values], [(100, 10000), (80, 7840)])

    def test_boundary_fixtures_are_physical_data_not_prompt_hints(self):
        case = self.case("constraint", "category_orders_illegal_contribution_001")
        path, _, _ = prepare_fixture(case, self.path)
        with closing(sqlite3.connect(path)) as db:
            self.assertGreater(
                db.execute(
                    "SELECT COUNT(*) FROM (SELECT order_id FROM order_items GROUP BY order_id HAVING COUNT(DISTINCT category)>1)"
                ).fetchone()[0],
                0,
            )
            groups = db.execute(
                "SELECT paid_at,category,COUNT(DISTINCT order_id) FROM order_items GROUP BY paid_at,category ORDER BY paid_at,category"
            ).fetchall()
            self.assertEqual([x[2] for x in groups], [70, 50, 45, 45])
        case = self.case("data_quality", "missing_paid_at_001")
        path, _, _ = prepare_fixture(case, self.path)
        with closing(sqlite3.connect(path)) as db:
            cols = {r[1] for r in db.execute("PRAGMA table_info(order_items)")}
            self.assertTrue({"created_at", "delivered_at"} <= cols)
            self.assertEqual(
                db.execute(
                    "SELECT COUNT(paid_at),COUNT(first_valid_paid_at) FROM order_items"
                ).fetchone(),
                (0, 0),
            )
        case = self.case("numeric_boundary", "zero_baseline_001")
        path, _, _ = prepare_fixture(case, self.path)
        with closing(sqlite3.connect(path)) as db:
            self.assertEqual(
                db.execute(
                    "SELECT COUNT(*) FROM order_items WHERE paid_at<'2026-08-01'"
                ).fetchone()[0],
                0,
            )
            self.assertEqual(
                db.execute(
                    "SELECT SUM(merchandise_amount) FROM order_items"
                ).fetchone()[0],
                1000,
            )

    def test_impossible_buyer_counts_require_review_not_fake_records(self):
        case = self.case("decomposition", "orders_frequency_driver_001")
        # Negative builder test remains impossible independently of Golden Set revisions.
        case["user_query"] = "订单量下降主要是什么导致的？"
        case["fixture_spec"]["description"] = (
            "基期 Buyers=100、Orders=120；本期 Buyers=100、Orders=90。"
        )
        with self.assertRaisesRegex(
            FixtureReviewRequired, "Orders=90, distinct Buyers=100"
        ):
            prepare_fixture(case, self.path)
        self.assertFalse(list(self.path.glob("*.db")))
        self.assertEqual(workflow_input(case)["metric_id"], "orders")

    def test_expected_gate_requires_completed_actual(self):
        expected = self.path / "expected.json"
        expected.write_text('{"canary":"PRIVATE_EXPECTED"}')
        checkpoint = self.path / "actual.json"
        write_json(checkpoint, {"execution_status": "pending", "lifecycle": []})
        gate = ExpectedGate()
        with self.assertRaises(PermissionError):
            gate.load(expected, checkpoint)
        with self.assertRaises(RuntimeError):
            gate.close_execution([checkpoint])
        write_json(
            checkpoint, {"execution_status": "completed", "lifecycle": ["actual_saved"]}
        )
        gate.close_execution([checkpoint])
        self.assertEqual(gate.load(expected, checkpoint)["canary"], "PRIVATE_EXPECTED")

    def test_audit_blocks_expected_files_directory_sqlite_and_network(self):
        inside = self.path / "worker"
        inside.mkdir()
        outside = self.path / "expected"
        outside.mkdir()
        secret = outside / "answer.json"
        secret.write_text("PRIVATE_EXPECTED")
        script = """
import sys,os,socket,sqlite3
from pathlib import Path
from evals.support.isolation import install_guard
root=Path(sys.argv[1]);outside=Path(sys.argv[2]);stats=install_guard(root)
operations=[lambda: outside.read_text(),lambda: os.listdir(outside.parent),lambda: sqlite3.connect(outside),lambda: socket.socket()]
for operation in operations:
    try: operation()
    except PermissionError: pass
    else: raise AssertionError('Isolation allowed forbidden access')
(root/'proof.txt').write_text('safe')
assert stats['denied_operations']==4
"""
        run = subprocess.run(
            [sys.executable, "-c", script, str(inside), str(secret)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual((inside / "proof.txt").read_text(), "safe")

    def test_graders_detect_math_hard_constraint_and_unsupported_claim(self):
        actual = sample_actual()
        expected = {
            "expected": {
                "target_metric": "gross_gmv",
                "primary_driver": "aov",
                "closure_required": True,
            },
            "forbidden": {},
        }
        self.assertTrue(
            OverallCaseGrader().evaluate(actual, expected, self.contract)[
                "overall_pass"
            ]
        )
        broken = copy.deepcopy(actual)
        broken["result"]["evidence"][0]["payload"]["fact"]["effects"][0]["effect"] = -19
        self.assertFalse(
            CalculationGrader().evaluate(broken, expected, self.contract)["passed"]
        )
        broken = copy.deepcopy(actual)
        fact = broken["result"]["evidence"][0]["payload"]["fact"]
        fact.update(
            target_metric="orders", relationship_id=None, dimension_id="category"
        )
        graded = OverallCaseGrader().evaluate(broken, expected, self.contract)
        self.assertFalse(graded["overall_pass"])
        self.assertGreater(graded["hard_constraint_violations"], 0)
        broken = copy.deepcopy(actual)
        broken["result"]["key_findings"][0]["evidence_level"] = "unsupported"
        graded = OverallCaseGrader().evaluate(broken, expected, self.contract)
        self.assertFalse(graded["overall_pass"])
        self.assertEqual(graded["graders"]["EvidenceGrader"]["unsupported_claims"], 1)

    def test_additive_and_multiplicative_reference_checks(self):
        for rel, metric, parts in [
            (
                "gross_gmv_orders_aov",
                "gross_gmv",
                [
                    dict(metric_id="orders", baseline=2, current=2),
                    dict(metric_id="aov", baseline=50, current=40),
                ],
            ),
            (
                "buyers_new_returning",
                "buyers",
                [
                    dict(metric_id="new_buyers", baseline=40, current=20),
                    dict(metric_id="returning_buyers", baseline=60, current=60),
                ],
            ),
        ]:
            actual = sample_actual()
            effect_values = [0, -20] if metric == "gross_gmv" else [-20, 0]
            actual["trace"]["skills_called"] = [
                dict(
                    skill="contribution_analysis",
                    input=dict(
                        target_baseline=100,
                        target_current=80,
                        relationship_id=rel,
                        components=parts,
                    ),
                    output=dict(
                        status="success",
                        result={
                            "effects": [
                                dict(id=p["metric_id"], effect=v)
                                for p, v in zip(parts, effect_values)
                            ]
                        },
                    ),
                )
            ]
            self.assertTrue(
                CalculationGrader().evaluate(actual, {}, self.contract)["passed"]
            )
            actual["trace"]["skills_called"][0]["output"]["result"]["effects"][0][
                "effect"
            ] += 1
            self.assertFalse(
                CalculationGrader().evaluate(actual, {}, self.contract)["passed"]
            )

    def test_business_path_does_not_require_identical_internal_nodes(self):
        actual = sample_actual()
        expected = {"expected": {"required_relationships": ["gross_gmv_orders_aov"]}}
        actual["trace"]["nodes_executed"] = ["arbitrary_internal_detail"]
        self.assertTrue(
            WorkflowPathGrader().evaluate(actual, expected, self.contract)["passed"]
        )

    def test_causal_denial_is_not_scored_as_causal_assertion(self):
        actual = sample_actual()
        expected = {"expected": {}, "forbidden": {"claims": ["广告预算减少"]}}
        actual["report"] = "没有证据证明广告预算减少。"
        self.assertTrue(
            OverallCaseGrader().evaluate(actual, expected, self.contract)[
                "overall_pass"
            ]
        )
        actual["report"] = "广告预算减少导致销量下降。"
        result = OverallCaseGrader().evaluate(actual, expected, self.contract)
        self.assertFalse(result["overall_pass"])
        self.assertGreater(result["hard_constraint_violations"], 0)

    def test_na_metrics_do_not_become_perfect_scores(self):
        from evals.runner import unscored

        record = dict(
            execution_status="review_required", **unscored("infeasible", review=True)
        )
        summary = aggregate([record])
        self.assertEqual(summary["metrics"]["Overall Case Pass Rate"]["value"], 0)
        self.assertIsNone(summary["metrics"]["Calculation Accuracy"]["value"])

    def test_runner_continues_and_all_execution_precedes_expected(self):
        entries = load_manifest(ROOT / "evals/manifest.json")[:2]
        manifest = self.path / "manifest.json"
        write_json(manifest, {"case_count": 2, "cases": entries})
        calls = []
        original = Path.read_text

        def fake_worker(*args):
            calls.append("executed")
            if len(calls) == 1:
                raise RuntimeError("injected framework failure")
            return sample_actual()

        def guarded(path, *args, **kwargs):
            if "expected" in path.parts:
                self.assertEqual(len(calls), 2)
                self.assertEqual(
                    len(list((self.path / "results").glob("*/actual/*.json"))), 2
                )
            return original(path, *args, **kwargs)

        with (
            patch("evals.runner.execute_agent", side_effect=fake_worker),
            patch.object(Path, "read_text", guarded),
        ):
            summary, output = run_suite(
                manifest=manifest,
                fixture_dir=self.path / "fixtures",
                results_dir=self.path / "results",
            )
        self.assertEqual(summary["total_cases"], 2)
        self.assertEqual(summary["framework_error_cases"], 1)
        self.assertEqual(len(list((output / "cases").glob("*.json"))), 2)
        self.assertTrue((output / "summary.md").exists())

    def test_real_worker_never_receives_case_identity(self):
        from evals.runner import execute_agent

        case = self.case("numeric_boundary", "zero_baseline_001")
        db, mapping, _ = prepare_fixture(case, self.path)
        actual = execute_agent(db, mapping, workflow_input(case))
        serialized = json.dumps(actual)
        self.assertNotIn(case["case_id"], serialized)
        self.assertNotIn('"case_id"', serialized)
        self.assertEqual(actual["isolation"]["denied_operations"], 0)
        self.assertEqual(actual["execution_mode"]["llm"], "mock")


if __name__ == "__main__":
    unittest.main()
