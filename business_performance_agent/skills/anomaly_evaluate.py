from ..models.schemas import ModuleResult


def execute(knowledge, query, *, metric_compare_result, anomaly_policy):
    knowledge.get_metric(metric_compare_result["metric_id"])
    relative = metric_compare_result["relative_change"]
    if relative is None:
        return ModuleResult(
            "blocked",
            reason="data_unavailable",
            limitations=[
                "Undefined relative change cannot be classified by the configured threshold policy."
            ],
        )
    if anomaly_policy["method"] != "relative_change_threshold":
        return ModuleResult("blocked", reason="execution_failure")
    magnitude = abs(relative)
    severity = (
        "critical"
        if magnitude >= anomaly_policy["critical_threshold"]
        else "warning"
        if magnitude >= anomaly_policy["warning_threshold"]
        else "normal"
    )
    return ModuleResult(
        result=dict(
            is_anomaly=severity != "normal",
            severity=severity,
            direction="increase"
            if relative > 0
            else "decrease"
            if relative < 0
            else "unchanged",
        )
    )
