from ..models.schemas import ModuleResult


def execute(knowledge, query, *, analysis_scope):
    for metric in analysis_scope["metrics"]:
        knowledge.get_metric(metric)
    for dimension in analysis_scope.get("dimensions", []):
        knowledge.get_dimension(dimension)
    quality = query.quality(analysis_scope)
    issues = quality["issues"]
    blocked = [x for x in issues if x["severity"] == "blocked"]
    reason = (
        (
            "semantic_conflict"
            if any(x["type"] == "semantic_conflict" for x in blocked)
            else "data_quality_boundary"
        )
        if blocked
        else None
    )
    return ModuleResult(
        "blocked" if blocked else "warning" if issues else "success",
        result=dict(
            analysis_allowed=not blocked, issues=issues, checks=quality["checks"]
        ),
        reason=reason,
        warnings=[x["type"] for x in issues if x["severity"] == "warning"],
        limitations=[x["detail"] for x in issues],
    )
