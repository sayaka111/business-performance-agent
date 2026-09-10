"""Explicit pending-only continuation; preserve historical grades without regrading."""

import argparse
import os
from pathlib import Path
from uuid import uuid4

from . import live_runner
from .runner import (
    ROOT,
    read_json,
    write_json,
    load_manifest,
    aggregate,
    ratio,
    markdown,
)
from .support.benchmark import archive, sha256
from business_performance_agent.config.settings import DeepSeekSettings


def completed(record):
    return (
        record.get("execution_status") == "completed"
        and record.get("grading_status") == "completed"
        and isinstance(record.get("actual", {}).get("result"), dict)
        and not record.get("provider_interrupted")
        and not record.get("review_required")
        and type(record.get("overall_pass")) is bool
    )


def select_pending(entries, records):
    by_id = {r["case_id"]: r for r in records}
    if len(by_id) != len(records) or set(by_id) != {e["case_id"] for e in entries}:
        raise ValueError("Historical case inventory does not match Holdout manifest")
    return [e for e in entries if not completed(by_id[e["case_id"]])]


def snapshot():
    folders = (
        "business_performance_agent",
        "specs",
        "evals/cases",
        "evals/expected",
        "evals/graders",
        "evals/benchmarks",
        "evals/results",
    )
    paths = [
        p
        for folder in folders
        for p in (ROOT / folder).rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
    ]
    paths += [
        ROOT / "evals/holdout_manifest.json",
        ROOT / "evals/manifest.json",
        ROOT / "evals/support/holdout_grading.py",
    ]
    return {str(p.relative_to(ROOT)): sha256(p) for p in paths}


def provenance(record, provider, source_run, model=None):
    metrics = live_runner.provider_metrics([record])
    models = {
        e["model"] for e in record.get("actual", {}).get("events", []) if e.get("model")
    }
    return dict(
        case_id=record["case_id"],
        provider=provider,
        model=next(iter(models)) if len(models) == 1 else model,
        source_run_id=source_run,
        execution_status=record["execution_status"],
        grading_status=record.get("grading_status"),
        provider_attempts=metrics["provider_attempts"],
        provider_failures=metrics["provider_failures"],
        retry_count=metrics["retry_count"],
        fallback_used=bool(metrics["fallback_count"]),
    )


def run(previous, offline):
    if not os.environ.get("DEEPSEEK_API_KEY"):
        raise RuntimeError("DEEPSEEK_API_KEY_MISSING")
    previous, offline = Path(previous), Path(offline)
    entries = load_manifest(ROOT / "evals/holdout_manifest.json")
    old = [read_json(previous / "cases" / (e["case_id"] + ".json")) for e in entries]
    prior_summary = read_json(previous / "summary.json")
    pending = select_pending(entries, old)
    if not pending:
        raise RuntimeError("No pending cases; no requests sent")
    integrity = snapshot()
    model = DeepSeekSettings().model
    resume = dict(
        total=len(entries),
        previously_completed=sum(map(completed, old)),
        provider_interrupted=sum(bool(r.get("provider_interrupted")) for r in old),
        never_executed=sum(r["execution_status"] == "not_run" for r in old),
        pending_assigned=len(pending),
    )
    print("Resume: " + str(resume), flush=True)
    # The existing isolated runner receives only selected Cases and existing fixtures.
    # All new Actuals are persisted before the unchanged grading implementation runs.
    output = live_runner.execute(offline, "deepseek", model, entries=pending)
    print("DeepSeek run: " + str(output), flush=True)
    write_json(
        output / "continuation_lineage.json",
        dict(parent_run=previous.name, resume=resume),
    )
    new_summary = live_runner.grade_run(output, entries=pending)
    new = {
        e["case_id"]: read_json(output / "cases" / (e["case_id"] + ".json"))
        for e in pending
    }
    mixed = ROOT / "evals/results" / str(uuid4())
    mixed.mkdir(parents=True, exist_ok=False)
    records, sources = [], []
    for original in old:
        preserved = completed(original)
        record = original if preserved else new[original["case_id"]]
        source = provenance(
            record,
            "gemini" if preserved else "deepseek",
            previous.name if preserved else output.name,
            None if preserved else model,
        )
        sources.append(source)
        records.append(record)
        # Exact historical graded records are retained; provenance is stored separately.
        write_json(mixed / "cases" / (record["case_id"] + ".json"), record)
    eligible = [r for r in records if completed(r)]
    metrics = aggregate(eligible)["metrics"]
    metrics["Overall Case Pass Rate"] = ratio(
        sum(r["overall_pass"] for r in eligible), len(eligible)
    )
    unchanged = all(
        (ROOT / p).exists() and sha256(ROOT / p) == digest
        for p, digest in integrity.items()
    )
    if not unchanged:
        raise RuntimeError(
            "Protected artifact integrity failed; results retained for audit"
        )
    summary = dict(
        run_id=mixed.name,
        title="Phase 2 Live Eval — Gemini → DeepSeek Continuation",
        mode="live_mixed_gemini_deepseek",
        suite="holdout",
        status="SUCCESS" if len(eligible) == len(entries) else "PARTIAL",
        parent_run_id=previous.name,
        deepseek_run_id=output.name,
        source_offline_run_id=offline.name,
        resume_state=resume,
        total_cases=len(entries),
        executed_cases=sum(r["execution_status"] == "completed" for r in records),
        business_evaluated_cases=len(eligible),
        passed_cases=sum(r["overall_pass"] for r in eligible),
        failed_cases=sum(not r["overall_pass"] for r in eligible),
        pending_cases=len(entries) - len(eligible),
        review_required_cases=sum(bool(r["review_required"]) for r in records),
        metrics=metrics,
        hard_constraint_violations=sum(
            r["hard_constraint_violations"] for r in eligible
        ),
        provider_metrics={
            "gemini": prior_summary["provider_metrics"],
            "deepseek": new_summary["provider_metrics"],
        },
        expected_leakage="PASS"
        if prior_summary["expected_leakage"]
        == new_summary["expected_leakage"]
        == "PASS"
        else "FAIL",
        leakage_audit=new_summary["leakage_audit"],
        historical_leakage_audit_run=previous.name,
        protected_artifacts_unchanged=unchanged,
        stop_reason=new_summary["stop_reason"],
        provider_sources=sources,
        cases=[
            {
                k: r[k]
                for k in (
                    "case_id",
                    "execution_status",
                    "overall_pass",
                    "failures",
                    "review_required",
                )
            }
            for r in records
        ],
    )
    write_json(mixed / "summary.json", summary)
    write_json(mixed / "integrity.json", integrity)
    text = markdown(summary, records).replace(
        "No live API was used.",
        "Live Gemini and DeepSeek results are combined with explicit provenance.",
    )
    text = "# " + summary["title"] + "\n\n" + text
    text += "\nHistorical Gemini PASS and FAIL are preserved without re-execution or regrading. Provider reliability includes prior interrupted Gemini requests. DeepSeek smoke is excluded from Eval request counts. This is not a pure DeepSeek benchmark.\n"
    (mixed / "summary.md").write_text(text, encoding="utf-8")
    archived = archive(
        ROOT,
        mixed.name,
        "round_06_mixed_provider_live_completion",
        notes=f"Continuation of {previous.name}; new DeepSeek run {output.name}. Existing Gemini grades retained. No business logic, Cases, Expected, fixtures or graders changed. Single-attempt DeepSeek smoke passed before continuation and is excluded from provider metrics.",
        integrity={
            "unchanged": unchanged,
            "holdout_manifest_sha256": sha256(ROOT / "evals/holdout_manifest.json"),
        },
    )
    print("Mixed run: " + str(mixed), flush=True)
    print("Archive: " + str(archived), flush=True)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--previous-run", type=Path, required=True)
    parser.add_argument("--offline-run", type=Path, required=True)
    parser.add_argument("--execute-live", action="store_true", required=True)
    args = parser.parse_args()
    run(args.previous_run, args.offline_run)
