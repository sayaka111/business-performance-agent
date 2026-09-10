from ..models.schemas import ModuleResult


def execute(
    knowledge,
    query,
    *,
    metric_id,
    current_period,
    baseline_period,
    filters=None,
    relationship_id=None,
):
    relationships = knowledge.get_metric_relationships(metric_id)
    if relationship_id is None:
        return ModuleResult(
            result={
                "available_relationships": [
                    r["id"] for r in relationships if query.relationship_available(r)
                ]
            }
        )
    relationship = knowledge.get_relationship(relationship_id)
    if relationship not in relationships:
        return ModuleResult("blocked", reason="semantic_conflict")
    if not query.relationship_available(relationship):
        return ModuleResult("blocked", reason="data_unavailable")
    components = relationship.get(
        "components",
        [{"metric": m, "coefficient": 1} for m in relationship.get("drivers", [])],
    )
    drivers, provenance = [], []
    for component in components:
        baseline = query.metric(component["metric"], baseline_period, filters or {})
        current = query.metric(component["metric"], current_period, filters or {})
        drivers.append(
            dict(
                metric_id=component["metric"],
                coefficient=component["coefficient"],
                baseline=baseline["value"],
                current=current["value"],
            )
        )
        provenance.extend([baseline["provenance"], current["provenance"]])
    return ModuleResult(
        result=dict(
            target_metric=metric_id,
            relationship=relationship,
            drivers=drivers,
            provenance=provenance,
        )
    )
