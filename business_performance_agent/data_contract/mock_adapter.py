import json
import re
from pathlib import Path
from ..models.schemas import BoundaryError,Period
from ..tools.calculations import evaluate_formula
from .adapter import DatasetAdapter

class MockDatasetAdapter(DatasetAdapter):
    def __init__(self,knowledge,rows=None,mapping=None):
        self.knowledge=knowledge
        self.mapping=mapping or json.loads(Path(__file__).with_name('schema_mapping.example.json').read_text(encoding='utf-8'))
        self.capabilities=self.mapping['capabilities']
        self.complete_periods={('2026-08-24','2026-08-30'),('2026-08-31','2026-09-06')}
        self.semantic_consistent=True
        self.rows=rows if rows is not None else self._fixture()

    def _fixture(self):
        rows=[]
        # Synthetic records, not metric values or replacement formulas.
        for label,day,count,amount in [('b','2026-08-25',100,100.0),('c','2026-09-01',75,98.0)]:
            for i in range(count):
                values=dict(order_id=f'{label}-o{i}',order_item_id=f'{label}-i{i}',customer_id=f'{label}-u{i//2}',
                    paid_at=day,payment_success=True,merchandise_amount=amount,quantity=2,
                    first_valid_paid_at=day if i<count//2 else '2025-01-01',refund_status='confirmed',refunded_merchandise_amount=0,
                    channel='paid_search' if i%3==0 else 'organic' if i%3==1 else None,
                    campaign=None,region='north' if i%2==0 else 'south',category='home',product='sku_1')
                rows.append({self.mapping['semantic_mapping'][key]:value for key,value in values.items()})
        # Stable first purchase per customer, including multiple orders in one period.
        first={}
        for row in rows:
            customer=row[self.mapping['semantic_mapping']['customer_id']]
            date=row[self.mapping['semantic_mapping']['first_valid_paid_at']]
            first[customer]=min(first.get(customer,date),date)
        for row in rows:
            row[self.mapping['semantic_mapping']['first_valid_paid_at']]=first[row[self.mapping['semantic_mapping']['customer_id']]]
        return rows

    def field(self,row,semantic):
        physical=self.mapping['semantic_mapping'].get(semantic)
        if physical is None: raise BoundaryError('data_unavailable',f'semantic_mapping_missing: {semantic}')
        if physical not in row: raise BoundaryError('data_unavailable',f'missing mapped field: {semantic}')
        return row[physical]

    def required_fields(self,metric_id):
        metric=self.knowledge.get_metric(metric_id)
        fields=set(metric.get('required_fields',[]))
        for dependency in metric.get('required_metrics',[]): fields.update(self.required_fields(dependency))
        return fields

    def metric_available(self,metric_id):
        metric=self.knowledge.get_metric(metric_id)
        if metric.get('availability')=='optional' and not all(self.capabilities.values()): return False
        return self.required_fields(metric_id) <= self.mapping['semantic_mapping'].keys()

    def dimension_available(self,dimension_id):
        self.knowledge.get_dimension(dimension_id)
        if dimension_id=='customer_type':
            return {'customer_id','first_valid_paid_at'} <= self.mapping['semantic_mapping'].keys()
        return dimension_id in self.mapping['semantic_mapping']

    def dimension(self,row,dimension_id,period):
        dimension=self.knowledge.get_dimension(dimension_id)
        if dimension_id=='customer_type':
            first=self.field(row,'first_valid_paid_at')
            if not first: raise BoundaryError('data_unavailable','first_valid_paid_at unavailable; customer classification blocked')
            if first>period.end: raise BoundaryError('semantic_conflict','first purchase after observed paid order')
            return 'new' if period.contains(first) else 'returning'
        value=self.field(row,dimension_id)
        return str(value) if value is not None else dimension.get('rules',{}).get('unknown_value','unknown')

    def _rows(self,metric,period,filters):
        if (period.start,period.end) not in self.complete_periods:
            raise BoundaryError('data_unavailable','Mock has no complete data for requested period.')
        result=[]
        time=metric.get('time_attribution',self.knowledge.metadata('metrics')['time_attribution_default'])
        condition=self.knowledge.get_business_rule('valid_order')['minimum_condition']
        valid_field,required_value=condition.split(' = ')
        if required_value!='true': raise BoundaryError('semantic_conflict','Unsupported valid-order contract')
        for row in self.rows:
            if self.field(row,valid_field) is not True: continue
            if not period.contains(self.field(row,time)): continue
            if all(self.dimension(row,d,period)==v for d,v in filters.items()): result.append(row)
        return result

    def metric(self,metric_id,period,filters):
        period=Period(**period) if isinstance(period,dict) else period
        if not self.semantic_consistent: raise BoundaryError('semantic_conflict')
        metric=self.knowledge.get_metric(metric_id)
        if not self.metric_available(metric_id): raise BoundaryError('data_unavailable',f'Metric unavailable: {metric_id}')
        if metric.get('required_metrics'):
            return evaluate_formula(metric['formula'],lambda dependency:self.metric(dependency,period,filters))
        rows=self._rows(metric,period,filters)
        formula=metric['formula']
        aggregate=re.fullmatch(r'(SUM|COUNT)\((?:DISTINCT )?(\w+)(?: WHERE (.+))?\)',formula)
        if not aggregate: raise BoundaryError('data_unavailable','Unsupported frozen aggregate syntax: '+formula)
        operation,field,condition=aggregate.groups()
        if condition:
            if condition=='first_valid_paid_at BETWEEN period_start AND period_end':
                rows=[r for r in rows if period.contains(self.field(r,'first_valid_paid_at'))]
            elif condition=='first_valid_paid_at < period_start AND has_valid_order_in_period = true':
                rows=[r for r in rows if self.field(r,'first_valid_paid_at')<period.start]
            elif condition in ("customer_type_for_period = 'new'","customer_type_for_period = 'returning'"):
                required=condition.split("'")[1]
                rows=[r for r in rows if self.dimension(r,'customer_type',period)==required]
            else: raise BoundaryError('data_unavailable','Unsupported source predicate: '+condition)
        if field=='confirmed_refunded_merchandise_amount':
            rows=[r for r in rows if self.field(r,'refund_status')=='confirmed']
        values=[self.field(row,field) for row in rows]
        if any(v is None for v in values): raise BoundaryError('data_unavailable','Null required value: '+field)
        return sum(values) if operation=='SUM' else len(set(values))

    def segments(self,metric_id,dimension_id,period,filters):
        period=Period(**period) if isinstance(period,dict) else period
        metric=self.knowledge.get_metric(metric_id)
        segments={self.dimension(row,dimension_id,period) for row in self._rows(metric,period,filters)}
        return {segment:self.metric(metric_id,period,dict(filters,**{dimension_id:segment})) for segment in segments}

    def quality(self,scope):
        issues=[]
        checks={}
        def issue(kind,severity,detail): issues.append(dict(type=kind,severity=severity,detail=detail))
        checks['period_completeness']={p:(scope[p]['start'],scope[p]['end']) in self.complete_periods for p in ('current_period','baseline_period')}
        for p,complete in checks['period_completeness'].items():
            if not complete: issue('incomplete_'+p,'blocked','Mock period is missing or incomplete: '+p)
        fields=set()
        for metric in scope['metrics']: fields.update(self.required_fields(metric))
        fields.update(('order_item_id','order_id','paid_at','payment_success'))
        for dim in scope.get('dimensions',[]):
            fields.update(('customer_id','first_valid_paid_at') if dim=='customer_type' else (dim,))
        missing=sorted(fields-self.mapping['semantic_mapping'].keys())
        checks['metric_coverage']={'missing_fields':missing,'null_share':{}}
        if missing: issue('missing_fields','blocked','Required semantic mappings missing: '+','.join(missing))
        for field in sorted(fields-self.knowledge_dimension_ids()):
            if field in missing: continue
            nulls=sum(self.mapping['semantic_mapping'][field] not in row or row.get(self.mapping['semantic_mapping'][field]) is None for row in self.rows)
            checks['metric_coverage']['null_share'][field]=nulls/max(1,len(self.rows))
            if nulls: issue('missing_required_values','blocked','Missing required values: '+field)
        item_field=self.mapping['semantic_mapping'].get('order_item_id')
        keys=[r.get(item_field) for r in self.rows]
        checks['duplicate_integrity']={'duplicate_item_ids':len(keys)-len(set(keys))}
        if len(keys)!=len(set(keys)): issue('duplicate_business_id','blocked','Duplicate order item IDs detected.')
        # Repeated order IDs are valid across items; conflicting order attributes are not.
        orders,customers={},{}
        for row in self.rows:
            mapping=self.mapping['semantic_mapping']
            oid=row.get(mapping.get('order_id'))
            attributes=tuple(row.get(mapping.get(k)) for k in ('paid_at','payment_success','customer_id','channel','campaign','region'))
            if oid in orders and orders[oid]!=attributes:
                issue('semantic_conflict','blocked','An order has inconsistent order-level attributes across items.')
            orders[oid]=attributes
            if 'customer_id' in fields and 'first_valid_paid_at' in mapping:
                cid=row.get(mapping.get('customer_id'))
                first=row.get(mapping['first_valid_paid_at'])
                paid=row.get(mapping.get('paid_at'))
                if first and paid and (first>paid or (cid in customers and customers[cid]!=first)):
                    issue('semantic_conflict','blocked','Customer first purchase history is inconsistent.')
                customers[cid]=first
        checks['join_coverage']={}
        checks['unknown_share']={}
        for dim in scope.get('dimensions',[]):
            if dim=='customer_type': continue
            physical=self.mapping['semantic_mapping'].get(dim)
            unknown=sum(row.get(physical) in (None,'unknown','unattributed') for row in self.rows)/max(1,len(self.rows))
            checks['join_coverage'][dim]=1-unknown
            checks['unknown_share'][dim]=unknown
            if unknown: issue('unknown_'+dim,'warning',f'{dim} unknown/unattributed share={unknown:.6g}; values retained. No frozen high-share cutoff exists.')
        checks['comparison_consistency']=self.semantic_consistent
        if not self.semantic_consistent: issue('semantic_conflict','blocked','Dataset semantics disagree with frozen Knowledge.')
        checks['optional_capability_availability']=dict(self.capabilities)
        return {'issues':issues,'checks':checks}

    def knowledge_dimension_ids(self): return {d['id'] for d in self.knowledge.all('dimensions')}
    def scan_size(self): return len(self.rows)
    def schema(self):
        return {self.mapping['table']:sorted(set(self.mapping['semantic_mapping'].values()))}
