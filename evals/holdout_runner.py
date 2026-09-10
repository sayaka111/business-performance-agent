"""Phase 2 execution: persist every Actual before any Expected is loaded."""

import argparse
import hashlib
from pathlib import Path
from uuid import uuid4

from .runner import (
    ROOT,
    load_manifest,
    read_json,
    write_json,
    execute_agent,
    unscored,
    contracts,
    aggregate,
    ratio,
    markdown,
)
from .support.case_fixture import workflow_input, FixtureReviewRequired
from .support.holdout_fixture import prepare


def execute():
    entries = load_manifest(ROOT / "evals/holdout_manifest.json")
    output = ROOT / "evals/results" / str(uuid4())
    output.mkdir(parents=True, exist_ok=False)
    records = []
    for entry in entries:
        case = read_json(ROOT / entry["case_file"])
        request = workflow_input(case)
        record = dict(
            case_id=case["case_id"],
            input=request,
            user_query=case["user_query"],
            execution_status="pending",
            lifecycle=["case_loaded"],
        )
        try:
            database, mapping, metadata = prepare(case, output / "fixtures")
            record["fixture"] = dict(
                path=str(database),
                mapping=str(mapping),
                sha256=hashlib.sha256(database.read_bytes()).hexdigest(),
                **metadata,
            )
            record["lifecycle"].extend(["fixture_generated", "agent_started"])
            record["actual"] = execute_agent(database, mapping, request)
            record["execution_status"] = "completed"
            record["lifecycle"].append("actual_saved")
        except FixtureReviewRequired as exc:
            record.update(
                execution_status="review_required", **unscored(str(exc), review=True)
            )
        except Exception as exc:
            record.update(
                execution_status="framework_error",
                **unscored(f"{type(exc).__name__}: {exc}"),
            )
        write_json(output / "actual" / (case["case_id"] + ".json"), record)
        records.append(record)
    write_json(
        output / "execution_manifest.json",
        dict(
            run_id=output.name,
            mode="offline",
            records=[r["case_id"] for r in records],
            phase="actual_persisted_before_expected",
            input_translation="unchanged Round 3 deterministic workflow_input; offline does not assess a real intent LLM",
        ),
    )
    return output


def grade_run(output):
    from .support.expected_gate import ExpectedGate
    from .support.holdout_grading import evaluate

    output = Path(output)
    if (output / "summary.json").exists():
        raise FileExistsError(
            "Holdout summary is immutable; do not replace first grading"
        )
    execution = read_json(output / "execution_manifest.json")
    entries = load_manifest(ROOT / "evals/holdout_manifest.json")
    checkpoints = [output / "actual" / (e["case_id"] + ".json") for e in entries]
    gate = ExpectedGate()
    gate.close_execution(checkpoints)
    records = []
    for entry, checkpoint in zip(entries, checkpoints):
        record = read_json(checkpoint)
        if record["execution_status"] == "completed":
            expected = gate.load(ROOT / entry["expected_file"], checkpoint)
            record.update(evaluate(record["actual"], expected, contracts(ROOT)))
            record["grading_status"] = "completed"
            record["lifecycle"].extend(["expected_loaded", "graded"])
            record["input_translation_mismatch"] = record["input"][
                "metric_id"
            ] != expected["expected"].get("target_metric")
        write_json(output / "cases" / (entry["case_id"] + ".json"), record)
        records.append(record)
    summary = dict(
        run_id=output.name,
        mode="offline",
        suite="holdout",
        live_api_used=False,
        expected_leakage="PASS"
        if all(
            c["execution_status"] == "completed"
            and c["actual"]["isolation"]["denied_operations"] == 0
            for c in records
        )
        else "FAIL",
        leakage_audit=gate.events,
        **aggregate(records),
    )
    dimensions = [x for c in records for x in c.get("dimension_checks", [])]
    summary["metrics"]["Dimension Selection Accuracy"] = ratio(
        sum(x["passed"] for x in dimensions), len(dimensions)
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
    summary["limitations"] = [
        execution["input_translation"],
        "First offline baseline includes deterministic input-translation mismatches; these are not claims about live model intent accuracy.",
        "Qualitative construction choices are disclosed per Actual fixture; source Case/Expected remain unchanged.",
    ]
    write_json(output / "summary.json", summary)
    (output / "summary.md").write_text(
        markdown(summary, records)
        + "\n## Holdout interpretation\n\n"
        + "\n\n".join(summary["limitations"])
        + "\n",
        encoding="utf-8",
    )
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grade", type=Path)
    args = parser.parse_args()
    print(grade_run(args.grade) if args.grade else execute())
