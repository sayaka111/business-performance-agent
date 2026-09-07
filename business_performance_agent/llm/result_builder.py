"""Build a structured result before any language presentation."""

def candidate_claims(evidence):
    claims=[]
    for e in evidence:
        payload=e['payload']
        if e['evidence_level'] not in ('direct','derived') or payload.get('kind') not in ('comparison','contribution'): continue
        claims.append(dict(claim_id='C'+e['evidence_id'][1:],kind=payload['kind'],fact=payload['fact'],scope=payload['scope'],evidence_refs=[e['evidence_id']]))
    return claims

def claim_text(claim):
    fact,scope=claim['fact'],claim['scope']
    qualifier=f"（筛选：{scope['filters']}）" if scope.get('filters') else ''
    if claim['kind']=='comparison':
        relative='undefined' if fact['relative_change'] is None else f"{fact['relative_change']:.2%}"
        return f"{scope['metric_id']}{qualifier} 从 {fact['baseline_value']} 变为 {fact['current_value']}，变化 {fact['absolute_change']}（{relative}）。"
    aligned=[x for x in fact['effects'] if x['role']=='aligned_driver']
    if not aligned: return f"{scope['metric_id']}{qualifier} 无同向贡献项。"
    top=aligned[0]
    axis=f"，维度 {fact['dimension_id']}" if fact.get('dimension_id') else ''
    return f"在 {scope['metric_id']}{qualifier}{axis} 的本层分解中，{top['id']} 是最大同向内部贡献项：effect={top['effect']:.6g}，占本层同向贡献 {top['aligned_share']:.2%}。"

def build_result(definition,state,target,primary,secondary,claims):
    def driver(value):
        return dict(metric_id=value['id'],effect=value['effect'],aligned_share=value['aligned_share']) if value else dict(metric_id=None,effect=None,aligned_share=None)
    result=dict(workflow_id=definition['workflow_id'],workflow_version=definition['workflow_version'],workflow_status=state.workflow_status,
        target={key:target.get(key,state.target_metric if key=='metric_id' else None) for key in ('metric_id','current_value','baseline_value','absolute_change','relative_change')},
        primary_driver=driver(primary),secondary_drivers=[driver(x) for x in secondary],
        diagnostic_path=[{key:step.get(key) for key in ('metric_id','relationship_id','dimension_id','segment_id')} for step in state.analysis_path],
        key_findings=[dict(claim_id=c['claim_id'],claim=claim_text(c),evidence_level=c['evidence_level'],evidence_refs=c['evidence_refs']) for c in claims],
        evidence=[e for e in state.evidence if e['evidence_level'] in ('direct','derived')],
        warnings=list(dict.fromkeys(state.warnings)),limitations=list(dict.fromkeys(state.limitations)),
        failed_branches=state.failed_branches,stop_reason=state.stop_reason)
    validate_result(result,definition['output_schema'])
    return result

def validate_result(result,schema):
    if set(schema['required_fields'])-result.keys(): raise ValueError('missing output fields')
    allowed=schema['output']['workflow_status'].split(' | ')
    if result['workflow_status'] not in allowed: raise ValueError('invalid final status')
    evidence={x['evidence_id']:x for x in result['evidence']}
    for finding in result['key_findings']:
        if finding['evidence_level'] not in ('direct','derived') or not finding['evidence_refs']:
            raise ValueError('unsupported output claim')
        if any(ref not in evidence for ref in finding['evidence_refs']): raise ValueError('dangling evidence reference')
    def validate(value,template,path):
        if isinstance(template,dict):
            if not isinstance(value,dict): raise ValueError(path)
            for key,child in template.items():
                if key not in value: raise ValueError(path+'.'+key)
                validate(value[key],child,path+'.'+key)
        elif isinstance(template,list):
            if not isinstance(value,list): raise ValueError(path)
            for item in value:
                if template: validate(item,template[0],path+'[]')
        elif isinstance(template,str):
            options=[x.strip() for x in template.split('|')]
            types={'number':lambda x:type(x) in (int,float),'null':lambda x:x is None,'string':lambda x:isinstance(x,str),'object':lambda x:isinstance(x,dict)}
            if not any(types[t](value) if t in types else value==t for t in options): raise ValueError(path)
    validate(result,schema['output'],'result')
