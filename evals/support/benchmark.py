"""Archive explicitly selected runs; existing benchmark directories are immutable.

No Agent execution or Expected access. Source run files are never changed.
"""

import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def archive(root, run_id, benchmark_id, *, notes, integrity, comparison=None):
    root = Path(root)
    if not re.fullmatch(r"round_\d{2}_[a-z_]+", benchmark_id):
        raise ValueError("Invalid benchmark ID")
    source = root / "evals/results" / run_id
    summary = json.loads((source / "summary.json").read_text(encoding="utf-8"))
    # Keep audit evidence without publishing workstation-specific absolute paths.
    for event in summary.get("leakage_audit", []):
        if "checkpoint" in event:
            event["checkpoint"] = (
                "actual/" + event["checkpoint"].replace("\\", "/").rsplit("/", 1)[-1]
            )
    commit = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    metadata = dict(
        benchmark_id=benchmark_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        timestamp_kind="archive_time; original run timestamp unavailable",
        source_run_id=run_id,
        source_summary_sha256=sha256(source / "summary.json"),
        agent_version="0.1.0",
        git_commit=commit.stdout.strip() if commit.returncode == 0 else None,
        git_commit_scope="archive checkout; not an assertion of historical run revision",
        eval_manifest_sha256_at_archive=sha256(root / "evals/manifest.json"),
        historical_manifest_hash=None,
        mode=summary["mode"],
        case_count=summary["total_cases"],
        cases_executed=summary["executed_cases"],
        passed=summary["passed_cases"],
        failed=summary["failed_cases"],
        review_required=summary["review_required_cases"],
        metrics=summary["metrics"],
        failed_cases=[
            c["case_id"]
            for c in summary["cases"]
            if not c["overall_pass"] and not c["review_required"]
        ],
        expected_leakage=summary["expected_leakage"],
        spec_integrity=integrity,
        notes=notes,
    )
    failures = ["# Failed and review-required cases", ""]
    for case in summary["cases"]:
        if case["overall_pass"]:
            continue
        failures += [
            f"## {case['case_id']}",
            "",
            "Status: " + ("REVIEW_REQUIRED" if case["review_required"] else "FAIL"),
            "",
        ]
        failures += [
            "- " + reason for reason in case["review_required"] or case["failures"]
        ]
        failures.append("")
    if all(c["overall_pass"] for c in summary["cases"]):
        failures.append("NONE")
    markdown = (source / "summary.md").read_text(encoding="utf-8")
    markdown = markdown.replace(
        "Agent and frozen specifications were not modified. Expected is loaded only after execution; Golden Set revisions are documented separately. No live API was used.",
        "Expected is loaded only after execution. Changes relative to previous benchmarks are documented in archive notes and metadata. No live API was used.",
    )
    # Selected snapshots contain aggregate records, not copied full traces.
    markdown = re.sub(r"\[([^\]]+)\]\(cases/[^)]+\)", r"`\1`", markdown)
    markdown += "\n## Archive notes\n\n" + notes + "\n"
    files = {
        "summary.json": json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        "summary.md": markdown,
        "failures.md": "\n".join(failures) + "\n",
    }
    if comparison is not None:
        files["comparison.md"] = comparison
    metadata["artifact_sha256"] = {
        name: hashlib.sha256(content.encode()).hexdigest()
        for name, content in files.items()
    }
    files["metadata.json"] = json.dumps(metadata, ensure_ascii=False, indent=2) + "\n"
    destination = root / "evals/benchmarks" / benchmark_id
    destination.mkdir(parents=True, exist_ok=False)
    for name, content in files.items():
        with (destination / name).open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
    return destination
