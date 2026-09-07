from ..models.schemas import ModuleResult

def execute(knowledge, query, *, claim, evidence):
    """Structured claims bind exact facts, scope and evidence; free text fails closed."""
    if not isinstance(claim,dict) or claim.get('kind') not in ('comparison','contribution'):
        return ModuleResult('blocked', result={'claim_status':'unsupported','evidence_level':'unsupported'}, reason='evidence_boundary_reached')
    by_id = {e['evidence_id']:e for e in evidence}
    refs = claim.get('evidence_refs',[])
    valid = bool(refs) and all(ref in by_id and by_id[ref]['evidence_level'] in ('direct','derived') for ref in refs)
    if valid:
        source = by_id[refs[0]]
        valid = source['payload'].get('fact') == claim.get('fact') and source['payload'].get('scope') == claim.get('scope')
        valid = valid and source['payload'].get('kind') == claim['kind']
    if not valid:
        return ModuleResult('blocked', result={'claim_status':'unsupported','evidence_level':'unsupported'}, reason='evidence_boundary_reached')
    knowledge.get_metric(claim['scope']['metric_id'])
    return ModuleResult(result={'claim_status':'supported','evidence_level':source['evidence_level'],'evidence_refs':refs})
