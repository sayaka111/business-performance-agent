"""Offline suite: run all Agents first, persist Actual, then load Expected."""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

from .support.case_fixture import prepare_fixture, workflow_input, FixtureReviewRequired

ROOT = Path(__file__).resolve().parents[1]


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    temporary.replace(path)


def load_manifest(path, root=ROOT):
    manifest = read_json(path)
    cases = manifest["cases"]
    ids = [c["case_id"] for c in cases]
    if any(not isinstance(i, str) or not re.fullmatch(r"[a-z0-9_]+", i) for i in ids):
        raise ValueError("Unsafe case identifier")
    if len(ids) != len(set(ids)) or manifest.get("case_count") != len(cases):
        raise ValueError("Manifest case count or uniqueness mismatch")
    for entry in cases:
        for field, folder in [("case_file", "cases"), ("expected_file", "expected")]:
            source = (root / entry[field]).resolve()
            if not source.is_relative_to((root / "evals" / folder).resolve()):
                raise ValueError("Manifest path outside its boundary")
        case = read_json(root / entry["case_file"])
        if case["case_id"] != entry["case_id"]:
            raise ValueError("Case identity mismatch")
    return cases


def contracts(root):
    specs = root / "specs"
    state = read_json(specs / "workflows/gmv_diagnosis/state_schema.json")["state"]
    return dict(
        relationships={
            r["id"]: r
            for r in read_json(specs / "knowledge/metric_relationships.json")[
                "relationships"
            ]
        },
        dimensions={
            d["id"]: d
            for d in read_json(specs / "knowledge/dimensions.json")["dimensions"]
        },
        allowed_targets=state["target_metric"]["allowed"],
        stop_reasons=state["stop_reason"]["enum"],
        policy=read_json(specs / "workflows/gmv_diagnosis/policy.json")[
            "diagnosis_policy"
        ],
    )


def execute_agent(database, mapping, request, root=ROOT):
    """No case_id parameter. Child has no Cases, Expected, manifest or graders."""
    with tempfile.TemporaryDirectory(prefix="bpa-agent-") as directory:
        work = Path(directory)
        for folder in ("business_performance_agent", "specs"):
            shutil.copytree(
                root / folder,
                work / folder,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
        for name in ("worker.py", "isolation.py"):
            shutil.copy2(root / "evals/support" / name, work / name)
        shutil.copy2(database, work / "data.db")
        shutil.copy2(mapping, work / "mapping.json")
        write_json(work / "input.json", request)
        env = {
            k: v
            for k, v in os.environ.items()
            if not any(
                word in k.upper() for word in ("API_KEY", "TOKEN", "SECRET", "PASSWORD")
            )
        }
        env.update(BPA_RUN_LIVE_TESTS="0", PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
        process = subprocess.run(
            [sys.executable, "-I", "-B", str(work / "worker.py")],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if process.returncode:
            raise RuntimeError("Offline worker failed: " + process.stderr[-2400:])
        actual = read_json(work / "actual.json")
        if actual["isolation"]["denied_operations"]:
            raise RuntimeError("Worker attempted an operation outside isolation")
        return actual


def review_expectation(expected, request, contract):
    reviews = []
    e = expected.get("expected", {})
    target = e.get("target_metric", request["metric_id"])
    if target not in contract["allowed_targets"]:
        reviews.append(
            f"Frozen gmv_diagnosis accepts {contract['allowed_targets']}, but Case/Expected requests {target}; no substitute workflow or retargeting was used."
        )
    for rel in e.get("required_relationships", []):
        if rel not in contract["relationships"]:
            reviews.append("Expected relationship is not in Knowledge: " + rel)
    if "strict_contribution_allowed" in e:
        actual = (
            contract["dimensions"]
            .get(e.get("selected_dimension"), {})
            .get("contribution_support", {})
            .get(target)
        )
        if actual is not e["strict_contribution_allowed"]:
            reviews.append(
                "Expected contribution applicability conflicts with Knowledge"
            )
    return reviews


def unscored(reason, review=False):
    from .graders import OverallCaseGrader

    result = {
        cls.__name__: dict(applicable=False, passed=None, checks=[], failures=[])
        for cls in OverallCaseGrader.GRADERS
    }
    result["OverallCaseGrader"] = dict(
        applicable=True, passed=False, checks=[], failures=[reason]
    )
    return dict(
        graders=result,
        overall_pass=False,
        failures=[] if review else [reason],
        review_required=[reason] if review else [],
        hard_constraint_violations=0,
    )


def ratio(numerator, denominator):
    return dict(
        numerator=numerator,
        denominator=denominator,
        value=numerator / denominator if denominator else None,
    )


def aggregate(records):
    eligible = [c for c in records if not c["review_required"]]
    passed = sum(c["overall_pass"] for c in records)
    reviewed = sum(bool(c["review_required"]) for c in records)
    metrics = {}
    for label, grader in [
        ("Calculation Accuracy", "CalculationGrader"),
        ("Workflow Path Accuracy", "WorkflowPathGrader"),
        ("Primary Driver Accuracy", "PrimaryDriverGrader"),
        ("Correct Stop Rate", "StopGrader"),
    ]:
        applicable = [
            c["graders"][grader] for c in eligible if c["graders"][grader]["applicable"]
        ]
        metrics[label] = ratio(
            sum(g["passed"] is True for g in applicable), len(applicable)
        )
    for label, name in [
        ("First-Level Driver Accuracy", "first_level_primary_driver"),
        ("Nested Driver Accuracy", "nested_primary_driver"),
    ]:
        checks = [
            x
            for c in eligible
            for x in c["graders"]["PrimaryDriverGrader"]["checks"]
            if x["name"] == name
        ]
        metrics[label] = ratio(sum(x["passed"] for x in checks), len(checks))
    routing = [
        x
        for c in eligible
        for x in c["graders"]["ConstraintGrader"].get("routing_checks", [])
    ]
    metrics["Routing Validity"] = ratio(sum(x["passed"] for x in routing), len(routing))
    evidence = [c["graders"]["EvidenceGrader"] for c in eligible]
    total = sum(g.get("total_claims", 0) for g in evidence)
    metrics["Evidence Coverage"] = ratio(
        sum(g.get("supported_claims", 0) for g in evidence), total
    )
    metrics["Unsupported Claim Rate"] = ratio(
        sum(g.get("unsupported_claims", 0) for g in evidence), total
    )
    required = [c for g in evidence for c in g.get("required_claim_checks", [])]
    metrics["Required Claim Coverage"] = ratio(
        sum(c["passed"] for c in required), len(required)
    )
    metrics["Overall Case Pass Rate"] = ratio(passed, len(records))
    return dict(
        total_cases=len(records),
        executed_cases=sum(c["execution_status"] == "completed" for c in records),
        passed_cases=passed,
        failed_cases=len(records) - passed - reviewed,
        review_required_cases=reviewed,
        framework_error_cases=sum(
            c["execution_status"] == "framework_error"
            or c.get("grading_status") == "error"
            for c in records
        ),
        hard_constraint_violations=sum(
            c["hard_constraint_violations"] for c in records
        ),
        metrics=metrics,
    )


def markdown(summary, records):
    lines = [
        "# Offline Agent Eval",
        "",
        f"Run: `{summary['run_id']}`",
        "",
        f"Loaded {summary['total_cases']}; executed {summary['executed_cases']}; passed {summary['passed_cases']}; failed {summary['failed_cases']}; review required {summary['review_required_cases']}.",
        "",
        "| Metric | Value | Numerator / denominator |",
        "|---|---:|---:|",
    ]
    for name, m in summary["metrics"].items():
        value = f"{m['value']:.2%}" if m["value"] is not None else "N/A"
        lines.append(f"| {name} | {value} | {m['numerator']} / {m['denominator']} |")
    lines.extend(
        [
            "",
            f"Hard constraint violations: {summary['hard_constraint_violations']}",
            "",
            "Overall pass rate uses all loaded Cases. Review-required cases are excluded from component accuracy denominators, and never count as passes. Component accuracy is per applicable case; routing is per candidate selection; evidence metrics are per output core claim. N/A is not 100%.",
            "",
            "## Case results",
            "",
            "| Case | Status | Details |",
            "|---|---|---|",
        ]
    )
    for c in records:
        status = (
            "REVIEW_REQUIRED"
            if c["review_required"]
            else "PASS"
            if c["overall_pass"]
            else "FAIL"
        )
        message = (
            "; ".join(c["review_required"] or c["failures"])
            or "All applicable checks passed"
        )
        lines.append(
            f"| [{c['case_id']}](cases/{c['case_id']}.json) | {status} | {message.replace('|', '/')} |"
        )
    lines.extend(
        [
            "",
            "Agent and frozen specifications were not modified. Expected is loaded only after execution; Golden Set revisions are documented separately. No live API was used.",
            "",
            "Leakage controls: all execution precedes Expected loading; Actual is saved first; worker copies exclude Case/Expected/graders and use opaque filenames. Audit hooks block outside reads and networking. This is a trusted-code evaluation boundary, not an OS security sandbox.",
        ]
    )
    return "\n".join(lines) + "\n"


def run_suite(*, root=ROOT, manifest=None, fixture_dir=None, results_dir=None):
    root = Path(root).resolve()
    entries = load_manifest(manifest or root / "evals/manifest.json", root)
    fixture_dir = Path(fixture_dir or root / "evals/fixtures")
    run_id = str(uuid4())
    output = Path(results_dir or root / "evals/results") / run_id
    output.mkdir(parents=True, exist_ok=False)
    records = []
    # Phase 1: do not load Expected, even for earlier completed Cases.
    for entry in entries:
        identifier = entry["case_id"]
        case = read_json(root / entry["case_file"])
        request = workflow_input(case)
        record = dict(
            case_id=identifier,
            input=request,
            execution_status="pending",
            grading_status="pending",
            lifecycle=["case_loaded"],
            fixture=None,
        )
        try:
            database, mapping, fixture = prepare_fixture(case, fixture_dir)
            record["fixture"] = dict(
                path=str(database),
                mapping=str(mapping),
                sha256=hashlib.sha256(database.read_bytes()).hexdigest(),
                **fixture,
            )
            record["lifecycle"].extend(["fixture_generated", "agent_started"])
            actual = execute_agent(database, mapping, request, root)
            serialized = json.dumps(actual, ensure_ascii=False)
            if identifier in serialized or '"case_id"' in serialized:
                raise RuntimeError("Case identity leaked into Agent output")
            record["actual"] = actual
            record["execution_status"] = "completed"
            record["lifecycle"].append("actual_saved")
        except FixtureReviewRequired as exc:
            record.update(
                execution_status="review_required", **unscored(str(exc), review=True)
            )
            record["lifecycle"].append("fixture_infeasible")
        except Exception as exc:
            record.update(
                execution_status="framework_error",
                **unscored(f"{type(exc).__name__}: {exc}"),
            )
            record["lifecycle"].append("execution_error_saved")
        write_json(output / "actual" / f"{identifier}.json", record)
        records.append(record)
    # Phase 2: contracts and Expected belong to graders, not Agent context.
    from .graders import OverallCaseGrader

    contract = contracts(root)
    from .support.expected_gate import ExpectedGate

    gate = ExpectedGate()
    gate.close_execution([output / "actual" / f"{c['case_id']}.json" for c in records])
    for entry, record in zip(entries, records):
        if record["execution_status"] == "completed":
            try:
                expected = gate.load(
                    root / entry["expected_file"],
                    output / "actual" / f"{record['case_id']}.json",
                )
                if expected["case_id"] != record["case_id"]:
                    raise ValueError("Expected identity mismatch")
                record["lifecycle"].append("expected_loaded")
                reviews = review_expectation(expected, record["input"], contract)
                record.update(
                    OverallCaseGrader().evaluate(
                        record["actual"], expected, contract, reviews
                    )
                )
                record["grading_status"] = "completed"
                record["lifecycle"].append("graded")
            except Exception as exc:
                record.update(
                    grading_status="error",
                    **unscored(f"Grader error: {type(exc).__name__}: {exc}"),
                )
        else:
            record["grading_status"] = (
                "review_required"
                if record["execution_status"] == "review_required"
                else "not_available"
            )
        write_json(output / "cases" / f"{record['case_id']}.json", record)
    summary = dict(
        run_id=run_id,
        mode="offline",
        live_api_used=False,
        expected_leakage="PASS"
        if gate.execution_closed
        and any(c["execution_status"] == "completed" for c in records)
        and not any(c["execution_status"] == "framework_error" for c in records)
        and all(
            c.get("actual", {}).get("isolation", {}).get("denied_operations") == 0
            for c in records
            if c["execution_status"] == "completed"
        )
        else "FAIL",
        leakage_audit=gate.events,
        **aggregate(records),
    )
    summary["status"] = (
        "PARTIAL"
        if summary["review_required_cases"] or summary["framework_error_cases"]
        else "SUCCESS"
    )
    summary["cases"] = [
        {
            k: c[k]
            for k in (
                "case_id",
                "execution_status",
                "overall_pass",
                "failures",
                "review_required",
            )
        }
        for c in records
    ]
    write_json(output / "summary.json", summary)
    (output / "summary.md").write_text(markdown(summary, records), encoding="utf-8")
    return summary, output


def main():
    parser = argparse.ArgumentParser(
        description="Offline Agent evaluation; no external providers"
    )
    parser.add_argument("--mode", choices=["offline"], default="offline")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--fixture-dir", type=Path)
    parser.add_argument("--results-dir", type=Path)
    args = parser.parse_args()
    summary, output = run_suite(
        manifest=args.manifest,
        fixture_dir=args.fixture_dir,
        results_dir=args.results_dir,
    )
    print(
        json.dumps(
            dict(summary=summary, results=str(output)), ensure_ascii=False, indent=2
        )
    )
    return (
        2
        if summary["framework_error_cases"]
        else 1
        if summary["failed_cases"] or summary["review_required_cases"]
        else 0
    )


if __name__ == "__main__":
    raise SystemExit(main())
