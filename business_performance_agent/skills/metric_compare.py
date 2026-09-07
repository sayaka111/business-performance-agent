from ..models.schemas import ModuleResult
from ..tools.calculations import absolute_change, relative_change

def execute(knowledge, query, *, metric_id, current_period, baseline_period, filters=None):
    knowledge.get_metric(metric_id)
    current = query.metric(metric_id, current_period, filters or {})
    baseline = query.metric(metric_id, baseline_period, filters or {})
    result = dict(metric_id=metric_id, current_value=current['value'], baseline_value=baseline['value'],
                  absolute_change=absolute_change(current['value'],baseline['value']),
                  relative_change=relative_change(current['value'],baseline['value']),
                  provenance=[baseline['provenance'],current['provenance']])
    undefined = result['relative_change'] is None
    return ModuleResult(status='warning' if undefined else 'success', result=result,
                        warnings=['relative_change_undefined'] if undefined else [])
