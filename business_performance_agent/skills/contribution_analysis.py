from ..models.schemas import ModuleResult
from ..tools.calculations import symmetric_two_factor_decomposition, additive_contribution, closure_check, rank_effects

def execute(knowledge, query, *, target_metric, target_baseline, target_current, components, relationship_id=None, dimension_id=None):
    knowledge.get_metric(target_metric)
    if (relationship_id is None) == (dimension_id is None):
        return ModuleResult('blocked', reason='semantic_conflict')
    if dimension_id:
        dimension = knowledge.get_dimension(dimension_id)
        if dimension.get('contribution_support', {}).get(target_metric) is not True:
            return ModuleResult('blocked', reason='non_additive_metric_dimension_pair')
        kind = 'partition'
        ids = [x['id'] for x in components]
        coefficients = [1]*len(components)
    else:
        relationship = knowledge.get_relationship(relationship_id)
        if relationship['target_metric'] != target_metric or relationship['type'] == 'diagnostic':
            return ModuleResult('blocked', reason='semantic_conflict')
        kind = relationship['type']
        ids = relationship.get('drivers', [x['metric'] for x in relationship.get('components',[])])
        coefficients = [x['coefficient'] for x in relationship.get('components',[])]
        if [x['metric_id'] for x in components] != ids:
            return ModuleResult('blocked', reason='semantic_conflict')
    if len(ids) != len(set(ids)):
        return ModuleResult('blocked', reason='semantic_conflict')
    values = [target_baseline,target_current] + [x[k] for x in components for k in ('baseline','current')]
    if any(x is None for x in values):
        return ModuleResult('blocked', reason='data_unavailable', limitations=['Undefined component prevents exact contribution.'])
    if kind == 'exact_multiplicative':
        if len(components) != 2:
            return ModuleResult('blocked', reason='no_valid_relationship')
        a,b = components
        baselines, currents = a['baseline']*b['baseline'], a['current']*b['current']
        effects = symmetric_two_factor_decomposition(a['baseline'],a['current'],b['baseline'],b['current'])
    elif kind in ('exact_additive','partition'):
        baselines = sum(c*x['baseline'] for c,x in zip(coefficients,components))
        currents = sum(c*x['current'] for c,x in zip(coefficients,components))
        effects = [additive_contribution(x['baseline'],x['current'],c) for c,x in zip(coefficients,components)]
    else:
        return ModuleResult('blocked', reason='no_valid_relationship')
    checks = [closure_check(target_baseline,[baselines]), closure_check(target_current,[currents]), closure_check(target_current-target_baseline,effects)]
    if not all(x['closed'] for x in checks):
        return ModuleResult('blocked', result={'closure_checks': checks}, reason='semantic_conflict', limitations=['Exact relationship/partition does not close; no approximate attribution emitted.'])
    return ModuleResult(result=dict(target_metric=target_metric, target_change=target_current-target_baseline,
        relationship_id=relationship_id, dimension_id=dimension_id,
        effects=rank_effects(target_current-target_baseline,[{'id':key,'effect':value} for key,value in zip(ids,effects)]), **checks[-1]))
