import copy
from unittest.mock import patch

from business_performance_agent.config.settings import ReadOnlyPolicy
from business_performance_agent.tools.query_tool import MockQueryTool, validate_read_only_sql
from business_performance_agent.data_contract.mock_adapter import MockDatasetAdapter
from business_performance_agent.runtime.router import Router
from business_performance_agent.llm.client import MockLLMClient
from business_performance_agent.llm.constrained_router import ConstrainedRouter
from business_performance_agent.llm.intent_parser import IntentParser
from business_performance_agent.llm.report_generator import ReportGenerator
from business_performance_agent.llm.result_builder import validate_result
from business_performance_agent.models.schemas import BoundaryError, TransientError

from tests.helpers import Harness

class InterfaceTests(Harness):
    def test_unique_candidate_never_calls_llm(self):
        client=MockLLMClient()
        with patch.object(client,'structured_generate',side_effect=AssertionError('must not call')):
            router=Router(self.definition,ConstrainedRouter(client))
            self.assertEqual(router.select(['aov_units_price'],{},'node',{'router_decisions':[]}),'aov_units_price')

    def test_router_rejects_invented_choice(self):
        client=MockLLMClient()
        with patch.object(client,'structured_generate',return_value={'choice':'invented'}):
            with self.assertRaises(BoundaryError): ConstrainedRouter(client).choose(['channel','category'],{},'select_next_dimension')

    def test_intent_validation(self):
        parser=IntentParser(self.knowledge,self.definition,MockLLMClient())
        parsed=parser.parse('GMV 2026-08-31 2026-09-06 对比 2026-08-24 2026-08-30')
        self.assertEqual(parsed['metric_id'],'gross_gmv')
        with self.assertRaises((ValueError,KeyError)): parser.parse('invent a business metric')

    def test_rendering_cannot_add_causal_story(self):
        result=self.run_agent()
        client=MockLLMClient()
        with patch.object(client,'structured_generate',return_value={'text':'Competitor bidding caused decline'}):
            report=ReportGenerator(client).generate(result)
        self.assertNotIn('Competitor',report)
        for finding in result['key_findings']: self.assertIn(finding['claim'],report)

    def test_sql_readonly_policy(self):
        policy=ReadOnlyPolicy(column_allowlist=('mock_order_key',))
        for sql in ['SELECT mock_order_key FROM mock_order_items','WITH x AS (SELECT mock_order_key FROM mock_order_items) SELECT mock_order_key FROM x']:
            self.assertTrue(validate_read_only_sql(sql,policy))
        for sql in ['DELETE FROM mock_order_items','SELECT mock_order_key FROM mock_order_items; DROP TABLE x','WITH x AS (DELETE FROM t) SELECT a FROM x','SELECT secret FROM mock_order_items','SELECT mock_order_key FROM private','SELECT * FROM mock_order_items']:
            with self.assertRaises(BoundaryError): validate_read_only_sql(sql,policy)

    def test_query_row_limit_blocks_without_truncation(self):
        query=MockQueryTool(self.adapter,ReadOnlyPolicy(max_rows=1))
        with self.assertRaises(BoundaryError): query.metric('orders',self.raw['current_period'],{})

    def test_physical_mapping_replacement_preserves_result(self):
        expected=self.run_agent(MockLLMClient())['target']
        old=self.adapter.mapping['semantic_mapping']
        renamed={value:'replacement_'+str(i) for i,value in enumerate(sorted(set(old.values())))}
        rows=[{renamed[k]:v for k,v in row.items()} for row in self.adapter.rows]
        mapping=copy.deepcopy(self.adapter.mapping)
        mapping['semantic_mapping']={k:renamed[v] for k,v in old.items()}
        self.adapter=MockDatasetAdapter(self.knowledge,rows=rows,mapping=mapping)
        self.query=MockQueryTool(self.adapter)
        self.assertEqual(self.run_agent(MockLLMClient())['target'],expected)

    def test_timeout_rejects_late_response(self):
        with patch('business_performance_agent.tools.query_tool.time.monotonic',side_effect=[0,100]):
            with self.assertRaises(BoundaryError): self.query.metric('orders',self.raw['current_period'],{})

    def test_unsupported_core_evidence_removed(self):
        result=self.run_agent()
        result['key_findings'][0]['evidence_level']='unsupported'
        with self.assertRaises(ValueError): validate_result(result,self.definition['output_schema'])

    def test_customer_identity_conflict_blocks(self):
        self.adapter.rows[1]['mock_first_purchase']='2024-01-01'
        result=self.run_agent()
        self.assertEqual(result['workflow_status'],'blocked')
        self.assertEqual(result['stop_reason'],'semantic_conflict')

    def test_baseline_zero_is_not_fabricated_anomaly(self):
        for row in self.adapter.rows:
            if row['mock_paid_date']=='2026-08-25': row['mock_goods_amount']=0
        result=self.run_agent()
        self.assertIsNone(result['target']['relative_change'])
        self.assertEqual(result['stop_reason'],'data_unavailable')

    def test_failure_after_reliable_root_is_partial(self):
        original=self.adapter.metric
        def unavailable(metric,*args):
            if metric=='buyers': raise TransientError('buyer data temporarily unavailable')
            return original(metric,*args)
        with patch.object(self.adapter,'metric',side_effect=unavailable): result=self.run_agent()
        self.assertEqual(result['workflow_status'],'partial')
        self.assertTrue(result['key_findings'])
        self.assertTrue(result['failed_branches'])
