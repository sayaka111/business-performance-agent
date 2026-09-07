from ..models.schemas import ModuleResult
from ..tools.calculations import absolute_change, relative_change

def execute(knowledge, query, *, metric_id, dimension_id, current_period, baseline_period, filters=None):
    knowledge.get_metric(metric_id)
    dimension = knowledge.get_dimension(dimension_id)
    supported = dimension.get('contribution_support',{}).get(metric_id) is True
    if not supported and not dimension.get('descriptive_support',{}).get(metric_id):
        return ModuleResult('blocked', reason='no_valid_dimension')
    current = query.segments(metric_id,dimension_id,current_period,filters or {})
    baseline = query.segments(metric_id,dimension_id,baseline_period,filters or {})
    rows = []
    for segment in sorted(set(current['values']) | set(baseline['values'])):
        c,b = current['values'].get(segment,0),baseline['values'].get(segment,0)
        rows.append(dict(id=segment,current=c,baseline=b,absolute_change=absolute_change(c,b),relative_change=relative_change(c,b)))
    return ModuleResult(result=dict(metric_id=metric_id,dimension_id=dimension_id, contribution_supported=supported,
                                   segments=rows,provenance=[baseline['provenance'],current['provenance']]),
                        limitations=[] if supported else ['Non-additive metric/dimension: descriptive comparison only; strict contribution prohibited.'])
