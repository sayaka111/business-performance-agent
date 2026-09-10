"""Deterministic v1 graders. Only called after Actual has been persisted.

Missing required observations fail, never get filled from Expected. No Agent
calculation functions are imported to calculate grading reference values.
"""

import math
import re

MISSING = "<not observed>"


def close(actual, expected):
    if expected is None:
        return actual is None
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        return (
            isinstance(actual, (int, float))
            and not isinstance(actual, bool)
            and math.isfinite(actual)
            and math.isclose(actual, expected, rel_tol=1e-7, abs_tol=1e-7)
        )
    return actual == expected


def check(name, actual, expected, *, message=None, numeric=False):
    passed = close(actual, expected) if numeric else actual == expected
    return dict(
        name=name,
        passed=passed,
        actual=actual,
        expected=expected,
        message=message or f"{name}: expected {expected!r}, observed {actual!r}",
    )


def grade(checks, **metadata):
    return dict(
        applicable=bool(checks),
        passed=all(c["passed"] for c in checks) if checks else None,
        checks=checks,
        failures=[c["message"] for c in checks if not c["passed"]],
        **metadata,
    )


def facts(actual, kind):
    return [
        e["payload"]
        for e in actual.get("result", {}).get("evidence", [])
        if e.get("payload", {}).get("kind") == kind
    ]


def root_metric(actual, metric):
    result = actual.get("result", {})
    target = result.get("target", {})
    if target.get("metric_id") == metric and target.get("baseline_value") is not None:
        return target
    for p in facts(actual, "comparison"):
        if p["scope"]["metric_id"] == metric and not p["scope"].get("filters"):
            return p["fact"]
    for p in facts(actual, "decomposition"):
        if p["scope"].get("filters"):
            continue
        for d in p["fact"]["drivers"]:
            if d["metric_id"] == metric:
                b, c = d["baseline"], d["current"]
                return dict(
                    baseline_value=b,
                    current_value=c,
                    absolute_change=c - b if b is not None and c is not None else None,
                    relative_change=(c - b) / b
                    if b not in (None, 0) and c is not None
                    else None,
                )
    return {}


def contributions(actual, metric=None, dimension=None):
    return [
        p["fact"]
        for p in facts(actual, "contribution")
        if (metric is None or p["fact"]["target_metric"] == metric)
        and p["fact"].get("dimension_id") == dimension
        and not p["scope"].get("filters")
    ]


def normalized(text):
    return re.sub(r"[^\w\u4e00-\u9fff]", "", str(text).lower()).replace(
        "paidsearch", "paid_search"
    )


def positive_mention(text, phrase):
    """Bounded lexical rule: explicit denials are not causal assertions."""
    for sentence in re.split(r"[。；;\n]", text):
        norm = normalized(sentence)
        needle = normalized(phrase)
        position = norm.find(needle)
        if position < 0:
            continue
        prefix = norm[max(0, position - 25) : position]
        if not re.search(
            r"无法|没有证据|不足以|不支持|不得|不能|不证明|未证实|noevidence|cannot",
            prefix,
            re.I,
        ):
            return True
    return False


class CalculationGrader:
    def evaluate(self, actual, expected, contracts):
        e = expected.get("expected", {})
        metric = e.get(
            "contribution_metric",
            e.get(
                "target_metric",
                actual["result"].get("target", {}).get("metric_id", "gross_gmv"),
            ),
        )
        checks = []
        aliases = {
            "gmv": "gross_gmv",
            "units": "units_per_order",
            "price": "average_realized_unit_price",
        }
        dim = e.get("selected_dimension")
        for key, wanted in e.get("expected_values", {}).items():
            observed = MISSING
            if key.endswith("_effect"):
                name = aliases.get(key[:-7], key[:-7])
                for fact in contributions(actual, metric, dim):
                    for item in fact["effects"]:
                        if item["id"] == name:
                            observed = item["effect"]
            else:
                prefix, _, name = key.partition("_")
                column = {
                    "baseline": "baseline_value",
                    "current": "current_value",
                    "delta": "absolute_change",
                }.get(prefix)
                if column:
                    observed = root_metric(actual, aliases.get(name, name)).get(
                        column, MISSING
                    )
            checks.append(check(key, observed, wanted, numeric=True))
        for key in ("absolute_change", "relative_change"):
            if key in e:
                checks.append(
                    check(
                        key,
                        actual["result"].get("target", {}).get(key, MISSING),
                        e[key],
                        numeric=True,
                    )
                )
        if "relative_change_status" in e:
            target = actual["result"].get("target", {})
            status = (
                "undefined"
                if target.get("baseline_value") == 0
                and target.get("relative_change", MISSING) is None
                else "defined_or_unobserved"
            )
            checks.append(
                check("relative_change_status", status, e["relative_change_status"])
            )
        # Independently verify all emitted comparisons and contribution closure.
        for p in facts(actual, "comparison"):
            f = p["fact"]
            b, c = f["baseline_value"], f["current_value"]
            if b is None or c is None:
                continue
            checks.append(
                check(
                    "comparison_absolute_change",
                    f["absolute_change"],
                    c - b,
                    numeric=True,
                )
            )
            checks.append(
                check(
                    "comparison_relative_change",
                    f["relative_change"],
                    None if b == 0 else (c - b) / b,
                    numeric=True,
                )
            )
        emitted = facts(actual, "contribution")
        if e.get("closure_required"):
            checks.append(
                check(
                    "required_contribution_observed",
                    bool(contributions(actual, metric, dim)),
                    True,
                    message=f"No contribution observed for {metric} / {dim or 'relationship'}; required closure cannot be assessed",
                )
            )
        for p in emitted:
            f = p["fact"]
            checks.append(
                check(
                    "effect_sum_closure",
                    sum(x["effect"] for x in f["effects"]),
                    f["target_change"],
                    numeric=True,
                )
            )
        # Skill calls expose actual baseline/current inputs; use them, not data re-query.
        for call in actual["trace"].get("skills_called", []):
            if call["skill"] != "contribution_analysis" or call["output"][
                "status"
            ] not in ("success", "warning"):
                continue
            inp = call["input"]
            out = call["output"]["result"]
            parts = inp["components"]
            rel = contracts["relationships"].get(inp.get("relationship_id"), {})
            kind = rel.get("type", "partition" if inp.get("dimension_id") else "")
            b, c = inp["target_baseline"], inp["target_current"]
            if kind == "exact_multiplicative" and len(parts) == 2:
                x, y = parts
                expected_effects = [
                    (x["current"] - x["baseline"]) * (y["baseline"] + y["current"]) / 2,
                    (y["current"] - y["baseline"]) * (x["baseline"] + x["current"]) / 2,
                ]
                bases = x["baseline"] * y["baseline"]
                curs = x["current"] * y["current"]
            elif kind in ("exact_additive", "partition"):
                coeff = [v["coefficient"] for v in rel.get("components", [])] or [
                    1
                ] * len(parts)
                expected_effects = [
                    k * (v["current"] - v["baseline"]) for k, v in zip(coeff, parts)
                ]
                bases = sum(k * v["baseline"] for k, v in zip(coeff, parts))
                curs = sum(k * v["current"] for k, v in zip(coeff, parts))
            else:
                continue
            checks.extend(
                [
                    check(kind + "_baseline_closure", bases, b, numeric=True),
                    check(kind + "_current_closure", curs, c, numeric=True),
                ]
            )
            effects = {x["id"]: x["effect"] for x in out["effects"]}
            for part, value in zip(parts, expected_effects):
                identifier = part.get("metric_id", part.get("id"))
                checks.append(
                    check(
                        kind + "_effect_" + identifier,
                        effects.get(identifier, MISSING),
                        value,
                        numeric=True,
                    )
                )
        return grade(checks)


class WorkflowPathGrader:
    def evaluate(self, actual, expected, contracts):
        e = expected.get("expected", {})
        r = actual["result"]
        path = r.get("diagnostic_path", [])
        observed = {p["relationship_id"] for p in path if p.get("relationship_id")}
        checks = [
            check("relationship_" + rel, rel in observed, True)
            for rel in e.get("required_relationships", [])
        ]
        checks.extend(
            check("forbidden_relationship_" + rel, rel in observed, False)
            for rel in expected.get("forbidden", {}).get("relationships", [])
        )
        if "target_metric" in e:
            checks.append(
                check(
                    "target_metric",
                    r.get("target", {}).get("metric_id"),
                    e["target_metric"],
                )
            )
        if "selected_dimension" in e:
            wanted_metric = (
                e.get("primary_driver")
                if "top_dimension_driver" in e
                else e.get("target_metric")
            )
            checks.append(
                check(
                    "dimension_scope",
                    any(
                        p.get("dimension_id") == e["selected_dimension"]
                        and p.get("metric_id") == wanted_metric
                        for p in path
                    ),
                    True,
                    message=f"Required {wanted_metric} × {e['selected_dimension']} analytical path was not executed",
                )
            )
        if "workflow_status" in e or "expected_status" in e:
            checks.append(
                check(
                    "workflow_status",
                    r.get("workflow_status"),
                    e.get("workflow_status", e.get("expected_status")),
                )
            )
        if "anomaly" in e:
            anomalies = facts(actual, "anomaly")
            checks.append(
                check(
                    "anomaly",
                    anomalies[0]["fact"]["is_anomaly"] if anomalies else MISSING,
                    e["anomaly"],
                )
            )
        return grade(checks)


class PrimaryDriverGrader:
    def evaluate(self, actual, expected, contracts):
        e = expected.get("expected", {})
        checks = []
        if "primary_driver" in e or "first_level_primary_driver" in e:
            checks.append(
                check(
                    "first_level_primary_driver",
                    actual["result"].get("primary_driver", {}).get("metric_id"),
                    e.get("first_level_primary_driver", e.get("primary_driver")),
                )
            )
        if "nested_primary_driver" in e:
            metric = e["nested_metric"]
            selections = [
                snap.get("selected_driver", {}).get("id")
                for snap in actual["trace"].get("state_snapshots", [])
                if snap.get("current_metric") == metric
                and isinstance(snap.get("selected_driver"), dict)
                and snap.get("selected_relationship")
                in e.get("required_relationships", [])
            ]
            checks.append(
                check(
                    "nested_primary_driver",
                    selections[-1] if selections else MISSING,
                    e["nested_primary_driver"],
                )
            )
        top = e.get("top_negative_driver", e.get("top_dimension_driver"))
        if top:
            metric = (
                e.get("primary_driver")
                if "top_dimension_driver" in e
                else e.get("target_metric")
            )
            seen = contributions(actual, metric, e.get("selected_dimension"))
            driver = (
                min(seen[0]["effects"], key=lambda x: x["effect"])["id"]
                if seen and seen[0]["effects"]
                else MISSING
            )
            checks.append(check("top_dimension_driver", driver, top))
        return grade(checks)


class ConstraintGrader:
    def evaluate(self, actual, expected, contracts):
        checks = []
        routing = []
        for decision in actual["trace"].get("router_decisions", []):
            if "allowed_candidates" not in decision:
                continue
            legal = (
                decision.get("choice") == "no_valid_choice"
                or decision.get("choice") in decision["allowed_candidates"]
            )
            routing.append(
                check(
                    "candidate_set_choice",
                    legal,
                    True,
                    message="Router selected outside allowed_candidates",
                )
            )
        checks.extend(routing)
        prohibited = expected.get("expected", {}).get("forbidden_contribution")
        if prohibited:
            checks.append(
                check(
                    "forbidden_contribution_absent",
                    bool(
                        contributions(
                            actual, prohibited["metric_id"], prohibited["dimension_id"]
                        )
                    ),
                    False,
                )
            )
        path_relationships = {
            p.get("relationship_id")
            for p in actual["result"].get("diagnostic_path", [])
        }
        for rel in expected.get("forbidden", {}).get("relationships", []):
            checks.append(
                check(
                    "forbidden_relationship",
                    rel in path_relationships,
                    False,
                    message="Forbidden analytical relationship executed: " + rel,
                )
            )
        for claim in actual["result"].get("key_findings", []):
            text = claim.get("claim", "")
            illegal_text = bool(
                re.search(r"orders|订单", text, re.I)
                and re.search(
                    r"维度\s*category|(?:category|品类).{0,25}对.{0,12}(?:orders|订单)|orders\s*[×x]\s*category",
                    text,
                    re.I,
                )
                and re.search(r"贡献|contribution", text, re.I)
                and not re.search(
                    r"不允许|不得|不能|非严格|不支持|descriptive|描述性", text, re.I
                )
            )
            if illegal_text:
                checks.append(
                    check(
                        "orders_category_claim_boundary",
                        True,
                        False,
                        message="Strict Orders × Category contribution claim was emitted",
                    )
                )
        for p in facts(actual, "contribution"):
            f = p["fact"]
            metric = f["target_metric"]
            dim = f.get("dimension_id")
            rel = f.get("relationship_id")
            if dim:
                legal = (
                    contracts["dimensions"]
                    .get(dim, {})
                    .get("contribution_support", {})
                    .get(metric)
                    is True
                )
                checks.append(
                    check(
                        "strict_contribution_legality",
                        legal,
                        True,
                        message=f"strict contribution produced for {metric} × {dim} despite a frozen restriction",
                    )
                )
            if rel:
                definition = contracts["relationships"].get(rel, {})
                legal = definition.get("target_metric") == metric and definition.get(
                    "type"
                ) in ("exact_multiplicative", "exact_additive", "partition")
                checks.append(
                    check(
                        "relationship_legality",
                        legal,
                        True,
                        message=f"Illegal contribution relationship: {metric} / {rel}",
                    )
                )
        for p in facts(actual, "comparison"):
            f = p["fact"]
            if f.get("baseline_value") == 0:
                checks.append(
                    check(
                        "zero_denominator_boundary",
                        f.get("relative_change", MISSING),
                        None,
                        message="Zero baseline produced a defined relative change",
                    )
                )
        sql = " ".join(
            str(q.get("sql", "")) for q in actual["trace"].get("query_operations", [])
        )
        checks.append(
            check(
                "no_payment_time_guessing",
                bool(re.search(r"\b(created_at|delivered_at)\b", sql, re.I)),
                False,
                message="Agent read non-payment timestamps as analytical input",
            )
        )
        checks.append(
            check(
                "execution_mode",
                actual.get("execution_mode", {}).get("llm"),
                contracts.get("expected_llm_mode", "mock"),
            )
        )
        checks.append(
            check(
                "isolation_denials",
                actual.get("isolation", {}).get("denied_operations", MISSING),
                0,
            )
        )
        return grade(
            checks,
            hard_violations=sum(not c["passed"] for c in checks),
            routing_checks=routing,
        )


def supported_contribution_claim(actual, metric, dimension, driver):
    r = actual["result"]
    evidence = {e["evidence_id"]: e for e in r.get("evidence", [])}
    for claim in r.get("key_findings", []):
        for ref in claim.get("evidence_refs", []):
            e = evidence.get(ref, {})
            p = e.get("payload", {})
            f = p.get("fact", {})
            if (
                p.get("kind") == "contribution"
                and f.get("target_metric") == metric
                and f.get("dimension_id") == dimension
            ):
                aligned = [x for x in f["effects"] if x["role"] == "aligned_driver"]
                if (
                    aligned
                    and aligned[0]["id"] == driver
                    and e.get("evidence_level") in ("direct", "derived")
                ):
                    return True
    return False


class EvidenceGrader:
    def evaluate(self, actual, expected, contracts):
        r = actual["result"]
        checks = []
        claims = r.get("key_findings", [])
        evidence = {e["evidence_id"]: e for e in r.get("evidence", [])}
        supported = 0
        for claim in claims:
            refs = claim.get("evidence_refs", [])
            valid = (
                claim.get("evidence_level") in ("direct", "derived")
                and bool(refs)
                and all(
                    evidence.get(ref, {}).get("evidence_level") in ("direct", "derived")
                    for ref in refs
                )
            )
            supported += bool(valid)
            checks.append(
                check(
                    "supported_" + claim.get("claim_id", "?"),
                    valid,
                    True,
                    message="Core claim lacks direct/derived evidence references",
                )
            )
        text = "\n".join(
            [c.get("claim", "") for c in claims]
            + r.get("warnings", [])
            + r.get("limitations", [])
            + [actual.get("report", "")]
        )
        norm = normalized(text)
        for forbidden in expected.get("forbidden", {}).get("claims", []):
            found = positive_mention(text, forbidden)
            primary = re.search(r"将(\w+)作为主要驱动", forbidden)
            if primary:
                found = (
                    found or r.get("primary_driver", {}).get("metric_id") == primary[1]
                )
            if "GMV第一层数学驱动" in forbidden:
                found = (
                    found
                    or r.get("primary_driver", {}).get("metric_id")
                    in contracts["dimensions"]
                )
            checks.append(
                check(
                    "forbidden_claim",
                    found,
                    False,
                    message="Forbidden claim: " + forbidden,
                )
            )
        review = []
        for required in expected.get("expected", {}).get("required_claims", []):
            if "GMV下降主要由Orders" in required:
                found = supported_contribution_claim(
                    actual, "gross_gmv", None, "orders"
                )
            elif "Orders下降主要集中在Paid Search" in required:
                found = supported_contribution_claim(
                    actual, "orders", "channel", "paid_search"
                )
            elif "进一步外部原因" in required:
                found = bool(
                    re.search(r"(不足|无法|不能|不证明).{0,45}(外部|因果)", text)
                )
            elif "paid_at口径" in required:
                found = (
                    r.get("workflow_status") == "blocked"
                    and "paid_at" in text
                    and bool(re.search(r"missing|缺失|无法|unavailable", text, re.I))
                )
            else:
                found = normalized(required) in norm
                if not found:
                    review.append(
                        "No reviewed deterministic matcher for required claim: "
                        + required
                    )
            checks.append(
                check(
                    "required_claim",
                    found,
                    True,
                    message="Required claim not communicated: " + required,
                )
            )
        return grade(
            checks,
            total_claims=len(claims),
            supported_claims=supported,
            unsupported_claims=len(claims) - supported,
            forbidden_claim_violations=sum(
                c["name"] == "forbidden_claim" and not c["passed"] for c in checks
            ),
            required_claim_checks=[c for c in checks if c["name"] == "required_claim"],
            review_required=review,
        )


class StopGrader:
    def evaluate(self, actual, expected, contracts):
        e = expected.get("expected", {})
        r = actual["result"]
        reason = r.get("stop_reason")
        status = r.get("workflow_status")
        checks = [
            check("stop_reason_in_contract", reason in contracts["stop_reasons"], True),
            check(
                "terminal_status",
                status
                in (
                    "completed",
                    "completed_no_anomaly",
                    "blocked",
                    "partial",
                    "failed",
                ),
                True,
            ),
        ]
        if "allowed_stop_reasons" in e:
            checks.append(
                check(
                    "allowed_stop_reason",
                    reason in e["allowed_stop_reasons"],
                    True,
                    message=f"Stop {reason!r} outside Expected allowed_stop_reasons",
                )
            )
        desired = e.get("workflow_status", e.get("expected_status"))
        if desired:
            checks.append(check("expected_status", status, desired))
        if "data_quality_status" in e:
            outputs = [
                c["output"]["status"]
                for c in actual["trace"].get("skills_called", [])
                if c["skill"] == "data_quality_guard"
            ]
            checks.append(
                check("data_quality_status", e["data_quality_status"] in outputs, True)
            )
        state = actual["trace"].get("state", {})
        policy = contracts["policy"]
        if reason == "target_coverage_reached":
            checks.append(
                check(
                    "target_coverage",
                    state.get("aligned_coverage", -1)
                    >= policy["target_aligned_coverage"],
                    True,
                )
            )
        elif reason == "max_depth_reached":
            checks.append(
                check("max_depth", state.get("depth", -1) >= policy["max_depth"], True)
            )
        elif reason == "below_min_contribution":
            checks.append(
                check(
                    "min_contribution",
                    state.get("selected_driver", {}).get("aligned_share", 1)
                    < policy["branch_min_contribution"],
                    True,
                )
            )
        elif reason == "not_anomaly":
            anomalies = facts(actual, "anomaly")
            checks.append(
                check(
                    "not_anomaly",
                    bool(anomalies) and anomalies[0]["fact"].get("is_anomaly") is False,
                    True,
                )
            )
        return grade(checks)


class OverallCaseGrader:
    GRADERS = (
        CalculationGrader,
        WorkflowPathGrader,
        PrimaryDriverGrader,
        ConstraintGrader,
        EvidenceGrader,
        StopGrader,
    )

    def evaluate(self, actual, expected, contracts, review_required=()):
        graders = {
            cls.__name__: cls().evaluate(actual, expected, contracts)
            for cls in self.GRADERS
        }
        reviews = list(review_required) + graders["EvidenceGrader"]["review_required"]
        violations = (
            graders["ConstraintGrader"]["hard_violations"]
            + graders["EvidenceGrader"]["unsupported_claims"]
            + graders["EvidenceGrader"]["forbidden_claim_violations"]
        )
        failures = [
            f"{name}: {failure}"
            for name, g in graders.items()
            for failure in g["failures"]
        ]
        passed = not failures and not reviews and not violations
        graders["OverallCaseGrader"] = grade(
            [check("all_required_checks_passed", passed, True)],
            hard_violations=violations,
        )
        return dict(
            graders=graders,
            overall_pass=passed,
            failures=failures,
            review_required=reviews,
            hard_constraint_violations=violations,
        )
