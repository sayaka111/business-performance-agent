"""Explicit Phase 2B run, bounded requests; no Expected loaded until all execution ends."""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from uuid import uuid4
from business_performance_agent.llm.providers import PROVIDER_KEYS

from .runner import (
    ROOT,
    read_json,
    write_json,
    load_manifest,
    ratio,
    contracts,
    aggregate,
    unscored,
    markdown,
)


def provider_failure(event):
    return event.get("status") == "failed" and (
        event.get("failure_kind") in ("timeout", "network", "http")
        or isinstance(event.get("http_status"), int)
        or event.get("error_type")
        in (
            "ConnectError",
            "ReadTimeout",
            "ConnectTimeout",
            "TimeoutError",
            "RemoteProtocolError",
        )
    )


def provider_metrics(records):
    events = [e for c in records for e in c.get("actual", {}).get("events", [])]
    failures = sum(provider_failure(e) for e in events)
    valid = sum(e["status"] == "success" for e in events)
    invalid = sum(
        e.get("error_type") in ("ValueError", "TypeError", "JSONDecodeError")
        for e in events
    )
    attempts = failures + valid + invalid
    reports = [
        c["actual"]
        for c in records
        if any(e["purpose"] == "report" for e in c.get("actual", {}).get("events", []))
    ]
    fallback = sum(
        a["report_metadata"].get("report_renderer") == "deterministic_fallback"
        for a in reports
    )
    return dict(
        provider_attempts=attempts,
        provider_successes=valid + invalid,
        provider_failures=failures,
        provider_success_rate=ratio(valid + invalid, attempts),
        count_429=sum(e.get("http_status") == 429 for e in events),
        count_5xx=sum(
            500 <= e.get("http_status", 0) < 600
            for e in events
            if type(e.get("http_status")) is int
        ),
        retry_count=sum(e.get("attempt", 1) > 1 for e in events),
        fallback_count=fallback,
        fallback_rate=ratio(fallback, len(reports)),
        structured_output_compliance=ratio(valid, valid + invalid),
    )


def worker(database, mapping, request, provider="gemini", model=None):
    with tempfile.TemporaryDirectory(prefix="bpa-live-") as name:
        work = Path(name)
        for folder in ("business_performance_agent", "specs"):
            shutil.copytree(
                ROOT / folder,
                work / folder,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
        for source, target in [
            ("live_worker.py", "worker.py"),
            ("isolation.py", "isolation.py"),
        ]:
            shutil.copy2(ROOT / "evals/support" / source, work / target)
        shutil.copy2(database, work / "data.db")
        shutil.copy2(mapping, work / "mapping.json")
        write_json(work / "input.json", dict(request, provider=provider, model=model))
        env = {
            k: v
            for k, v in os.environ.items()
            if k == PROVIDER_KEYS[provider]
            or not any(
                x in k.upper() for x in ("API_KEY", "TOKEN", "SECRET", "PASSWORD")
            )
        }
        env.update(PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1")
        proc = subprocess.run(
            [sys.executable, "-I", "-B", str(work / "worker.py")],
            cwd=work,
            env=env,
            capture_output=True,
            timeout=420,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if proc.returncode:
            raise RuntimeError(
                "Isolated live worker failed; subprocess output withheld"
            )
        return read_json(work / "actual.json")


def execute(offline_run, provider="gemini", model=None, *, entries=None):
    key_name = PROVIDER_KEYS[provider]
    if not os.environ.get(key_name):
        raise ValueError(f"{key_name} not configured; no requests sent")
    if not (
        ROOT / "evals/benchmarks/round_04_holdout_offline_baseline/metadata.json"
    ).exists():
        raise RuntimeError(
            "Archive first Holdout Offline baseline before live execution"
        )
    output = ROOT / "evals/results" / str(uuid4())
    output.mkdir(parents=True, exist_ok=False)
    entries = (
        entries
        if entries is not None
        else load_manifest(ROOT / "evals/holdout_manifest.json")
    )
    records = []
    consecutive = 0
    stop = None
    for entry in entries:
        case = read_json(ROOT / entry["case_file"])
        record = dict(
            case_id=entry["case_id"], execution_status="not_run", lifecycle=[]
        )
        if stop:
            record["stop_reason"] = stop
        else:
            source = read_json(
                Path(offline_run) / "actual" / (entry["case_id"] + ".json")
            )
            periods = case["periods"]
            request = dict(
                question=case["user_query"],
                period_context=f"Current period: {periods['current']}. Baseline period: {periods['baseline']}.",
            )
            try:
                actual = worker(
                    source["fixture"]["path"],
                    source["fixture"]["mapping"],
                    request,
                    provider,
                    model,
                )
                record.update(
                    actual=actual,
                    execution_status="completed",
                    lifecycle=["agent_started", "actual_saved"],
                )
                events = actual["events"]
                consecutive = (
                    consecutive + 1 if events and provider_failure(events[-1]) else 0
                )
                if actual["isolation"]["denied_operations"]:
                    stop = "isolation_boundary"
                elif consecutive >= 3:
                    stop = "three_consecutive_provider_failures"
            except Exception as exc:
                record.update(
                    execution_status="framework_error", error_type=type(exc).__name__
                )
                stop = "worker_execution_error"
            if (
                sum(len(c.get("actual", {}).get("events", [])) for c in records)
                + len(record.get("actual", {}).get("events", []))
                >= 72
            ):
                stop = "request_budget_reached"
        write_json(output / "actual" / (entry["case_id"] + ".json"), record)
        records.append(record)
        print(f"{entry['case_id']}: {record['execution_status']}", flush=True)
    write_json(
        output / "execution_manifest.json",
        dict(
            run_id=output.name,
            mode="live_" + provider,
            provider=provider,
            source_offline_run=Path(offline_run).name,
            stop_reason=stop,
            provider_metrics=provider_metrics(records),
            policy="Transport retries0 (Gemini SDK attempts1; DeepSeek stdlib HTTP); application attempts2; stop after3 consecutive provider-failed cases; admission budget72 attempts, max80 including final case; at most20 cases",
        ),
    )
    return output


def grade_run(output, *, entries=None):
    from .support.expected_gate import ExpectedGate
    from .support.holdout_grading import evaluate

    output = Path(output)
    if (output / "summary.json").exists():
        raise FileExistsError("Live summary already exists")
    execution = read_json(output / "execution_manifest.json")
    entries = (
        entries
        if entries is not None
        else load_manifest(ROOT / "evals/holdout_manifest.json")
    )
    records = [read_json(output / "actual" / (e["case_id"] + ".json")) for e in entries]
    if any(r["execution_status"] == "pending" for r in records):
        raise RuntimeError("Live execution is still pending")
    gate = ExpectedGate()
    gate.close_execution(
        [
            output / "actual" / (r["case_id"] + ".json")
            for r in records
            if r["execution_status"] == "completed"
        ]
    )
    eligible = []
    intents = []
    provider = execution.get("provider", "gemini")
    contract = contracts(ROOT) | {"expected_llm_mode": provider}
    for entry, record in zip(entries, records):
        a = record.get("actual", {})
        events = a.get("events", [])
        final = {
            purpose: [e for e in events if e["purpose"] == purpose][-1]
            for purpose in {e["purpose"] for e in events}
        }
        interrupted = any(
            provider_failure(e)
            for purpose, e in final.items()
            if purpose in ("intent", "routing")
        )
        if record["execution_status"] != "completed" or interrupted:
            reason = (
                "Provider failure interrupted intent/routing; business checks N/A"
                if interrupted
                else record.get("stop_reason", record.get("error_type", "not executed"))
            )
            record.update(
                unscored(reason, review=True), provider_interrupted=interrupted
            )
        else:
            expected = gate.load(
                ROOT / entry["expected_file"],
                output / "actual" / (entry["case_id"] + ".json"),
            )
            case = read_json(ROOT / entry["case_file"])
            raw = a.get("parsed_input") or {}
            target = expected["expected"].get("target_metric")
            periods = case["periods"]
            correct = raw.get("metric_id") == target and raw.get("filters") == {}
            for key, field in [
                ("baseline", "baseline_period"),
                ("current", "current_period"),
            ]:
                start, end = periods[key].split("/")
                correct = correct and raw.get(field) == dict(start=start, end=end)
            for word, dimension in [
                ("渠道", "channel"),
                ("品类", "category"),
                ("地区", "region"),
            ]:
                if word in case["user_query"]:
                    correct = (
                        correct
                        and raw.get("context", {}).get("preferred_dimension")
                        == dimension
                    )
            intents.append(bool(correct))
            record["intent_correct"] = bool(correct)
            if a.get("result") is not None:
                record.update(evaluate(a, expected, contract))
                eligible.append(record)
            else:
                record.update(
                    unscored(
                        "Structured/semantic intent rejected; no Workflow result, calculation N/A"
                    )
                )
            if not correct:
                record["failures"].append(
                    "Intent mismatch: target, periods, filters or explicitly requested dimension"
                )
                record["overall_pass"] = False
        record["grading_status"] = "completed"
        write_json(output / "cases" / (entry["case_id"] + ".json"), record)
    metrics = aggregate(eligible)["metrics"]
    evaluated = [r for r in records if not r["review_required"]]
    metrics["Overall Case Pass Rate"] = ratio(
        sum(r["overall_pass"] for r in evaluated), len(evaluated)
    )
    metrics["Intent Accuracy"] = ratio(sum(intents), len(intents))
    summary = dict(
        run_id=output.name,
        mode="live_" + provider,
        provider=provider,
        suite="holdout",
        status="PARTIAL" if execution["stop_reason"] else "SUCCESS",
        total_cases=len(records),
        executed_cases=sum(r["execution_status"] == "completed" for r in records),
        passed_cases=sum(r["overall_pass"] for r in records),
        failed_cases=sum(
            not r["overall_pass"] and not r["review_required"] for r in records
        ),
        review_required_cases=sum(bool(r["review_required"]) for r in records),
        provider_interrupted_cases=sum(
            r.get("provider_interrupted", False) for r in records
        ),
        not_run_cases=sum(r["execution_status"] == "not_run" for r in records),
        business_evaluated_cases=len(evaluated),
        metrics=metrics,
        provider_metrics=execution["provider_metrics"],
        stop_reason=execution["stop_reason"],
        hard_constraint_violations=sum(
            r["hard_constraint_violations"] for r in records
        ),
        expected_leakage="PASS"
        if all(
            r.get("actual", {}).get("isolation", {}).get("denied_operations", 0) == 0
            for r in records
        )
        else "FAIL",
        leakage_audit=gate.events,
    )
    summary["cases"] = [
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
    ]
    write_json(output / "summary.json", summary)
    notes = "\n## Live interpretation\n\nProvider-interrupted and not-run cases are unscored/review-required, not calculation failures. Overall Case Pass Rate denominator is business-evaluable cases, not all loaded cases. Report fallback does not invalidate completed deterministic calculations. Intent accuracy requires target/periods/filters and explicit dimension preservation; it is separate from JSON schema compliance. Successful provider report behavior cannot be established when all reports fall back.\n"
    report = markdown(summary, records).replace(
        "No live API was used.",
        f"Live {provider} was used; Provider outcomes are reported separately.",
    )
    (output / "summary.md").write_text(
        report
        + notes
        + "\nProvider metrics: "
        + str(summary["provider_metrics"])
        + "\n",
        encoding="utf-8",
    )
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--execute-live", action="store_true")
    modes.add_argument("--grade", type=Path)
    parser.add_argument("--offline-run", type=Path)
    parser.add_argument("--provider", choices=list(PROVIDER_KEYS), default="gemini")
    parser.add_argument("--model")
    parser.add_argument(
        "--grade-after",
        action="store_true",
        help="Grade persisted results after the bounded Live run",
    )
    args = parser.parse_args()
    if args.execute_live and args.offline_run is None:
        parser.error("--offline-run is required for live execution")
    if args.grade:
        print(grade_run(args.grade))
    else:
        output = execute(args.offline_run, args.provider, args.model)
        if args.grade_after:
            grade_run(output)
        print(output)
