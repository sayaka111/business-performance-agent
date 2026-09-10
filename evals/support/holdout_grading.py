"""Grade persisted Holdout Actuals. Expected normalization never reaches Agent."""

import copy
import re

from ..graders import OverallCaseGrader, check, grade, facts, contributions


def evaluate(actual, expected, contract):
    normalized = copy.deepcopy(expected)
    e = normalized["expected"]
    if "nested_primary_driver" in e:
        e.setdefault("nested_metric", e.get("first_level_primary_driver"))
    if "top_dimension_driver" in e:
        e.setdefault("primary_driver", e.get("first_level_primary_driver"))
    unavailable = "report dimension unavailable" in e.get("required_behaviors", [])
    dimension = e.get("selected_dimension")
    if unavailable:
        # This field specifies the requested dimension, not a demand to execute it.
        e.pop("selected_dimension", None)
    result = OverallCaseGrader().evaluate(actual, normalized, contract)
    r = actual["result"]
    path = r.get("diagnostic_path", [])
    metric = (
        e.get("first_level_primary_driver")
        if "top_dimension_driver" in e
        else e.get("target_metric")
    )
    scoped = contributions(actual, metric, dimension)
    effects = scoped[0]["effects"] if scoped else []
    checks = []
    dimension_checks = []
    if dimension and not unavailable:
        dimension_checks.append(
            check(
                "dimension_selection",
                any(
                    p.get("metric_id") == metric and p.get("dimension_id") == dimension
                    for p in path
                ),
                True,
            )
        )
    if "expected_ranking" in e:
        ranked = [x["id"] for x in effects if x["role"] == "aligned_driver"]
        checks.append(check("expected_ranking", ranked, e["expected_ranking"]))
    for name in e.get("offsetting_segments", []):
        checks.append(
            check(
                "offsetting_segment_" + name,
                any(x["id"] == name and x["role"] == "offset" for x in effects),
                True,
            )
        )
    limitations = "\n".join(r.get("warnings", []) + r.get("limitations", []))
    for behavior in e.get("required_behaviors", []):
        found = False
        if match := re.fullmatch(
            r"identify (\w+) as offsetting (nested driver|factor)", behavior
        ):
            scope = (
                e.get("nested_metric")
                if match[2] == "nested driver"
                else e.get("target_metric")
            )
            found = any(
                x["id"] == match[1] and x["role"] == "offset"
                for f in contributions(actual, scope)
                for x in f["effects"]
            )
        elif behavior == "preserve unknown segment":
            found = any(x["id"] in ("unknown", "unattributed") for x in effects)
        elif behavior in (
            "emit warning_or_limitation",
            "avoid overconfident full attribution",
        ):
            found = bool(
                re.search(r"unknown|unattributed|未知|未归因", limitations, re.I)
            )
        elif behavior in ("segment relative_change undefined", "absolute_change=1500"):
            segments = [
                row
                for p in facts(actual, "segments")
                if p["fact"].get("dimension_id") == dimension
                for row in p["fact"]["segments"]
                if row["baseline"] == 0 and row["current"] > 0
            ]
            found = any(
                row["relative_change"] is None
                if behavior.startswith("segment")
                else row["absolute_change"] == 1500
                for row in segments
            )
        elif behavior == "state internal localization":
            found = bool(scoped) and any(
                c["evidence_refs"] for c in r.get("key_findings", [])
            )
        elif behavior == "state external cause not established":
            found = bool(
                re.search(r"(无法|不足|不能|不证明).{0,45}(外部|因果)", limitations)
            )
        elif match := re.fullmatch(r"execute (\w+) x (\w+) drilldown", behavior):
            found = any(
                p.get("metric_id") == match[1] and p.get("dimension_id") == match[2]
                for p in path
            )
        elif behavior == "preserve requested dimension scope":
            found = any(
                p.get("metric_id") == e["target_metric"]
                and p.get("dimension_id") == dimension
                for p in path
            )
        elif behavior == "block strict orders x category contribution":
            found = not contributions(actual, "orders", "category")
        elif behavior == "may provide descriptive comparison only":
            found = not contributions(actual, "orders", "category")
        elif behavior == "do not launch unnecessary deep drilldown":
            found = not path
        elif behavior == "do not guess channel mapping":
            found = not any(p.get("dimension_id") == dimension for p in path)
        elif behavior == "report dimension unavailable":
            found = bool(
                re.search(r"channel|渠道", limitations, re.I)
                and re.search(r"unavailable|缺失|不可用|无法", limitations, re.I)
            )
        elif behavior == "preserve valid overall diagnosis":
            found = r.get("target", {}).get("current_value") is not None and bool(
                contributions(actual, e["target_metric"])
            )
        else:
            result["review_required"].append(
                "Unreviewed Holdout behavior matcher: " + behavior
            )
        checks.append(check(behavior, found, True))
    if "allowed_statuses" in e:
        observed = r.get("workflow_status")
        allowed = observed in e["allowed_statuses"] or (
            "warning" in e["allowed_statuses"] and bool(r.get("warnings"))
        )
        checks.append(check("allowed_statuses", allowed, True))
    checks.extend(dimension_checks)
    result["graders"]["HoldoutBehaviorGrader"] = grade(checks)
    result["dimension_checks"] = dimension_checks
    result["failures"].extend(
        "HoldoutBehaviorGrader: " + c["message"] for c in checks if not c["passed"]
    )
    result["overall_pass"] = (
        not result["failures"]
        and not result["review_required"]
        and not result["hard_constraint_violations"]
    )
    result["graders"]["OverallCaseGrader"] = grade(
        [check("all_required_checks_passed", result["overall_pass"], True)]
    )
    return result
