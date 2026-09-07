import copy
import json
from unittest.mock import patch

from business_performance_agent.runtime.state import WorkflowState
from business_performance_agent.runtime.router import Router
from business_performance_agent.llm.client import MockLLMClient
from business_performance_agent.llm.constrained_router import ConstrainedRouter
from business_performance_agent.models.schemas import TransientError

from tests.helpers import Harness

class RuntimeTests(Harness):
    def test_default_end_to_end_with_mock_router(self):
        result=self.run_agent(MockLLMClient())
        self.assertEqual(result['workflow_status'],'completed')
        self.assertEqual(result['target']['absolute_change'],-2650)
        self.assertEqual(result['primary_driver']['metric_id'],'orders')
        self.assertIn('dimension_drilldown',self.engine.trace['nodes_executed'])
        self.assertEqual(result['stop_reason'],'target_coverage_reached')
        self.assertEqual({x['skill'] for x in self.engine.trace['skills_called']},set(__import__('business_performance_agent.runtime.executor',fromlist=['SKILLS']).SKILLS))

    def test_trace_is_complete_json(self):
        self.run_agent(MockLLMClient())
        trace=json.loads(self.engine.trace_path.read_text(encoding='utf-8'))
        for field in ('run_id','workflow_id','workflow_version','input','nodes_executed','skills_called','router_decisions','warnings','limitations','evidence','stop_reason','final_structured_result'):
            self.assertIn(field,trace)
        self.assertEqual(trace['state']['current_node'],'complete')

    def test_no_llm_stops_at_candidate_boundary(self):
        result=self.run_agent()
        self.assertEqual(result['stop_reason'],'evidence_boundary_reached')

    def test_no_anomaly(self):
        for row in self.adapter.rows:
            if row['mock_paid_date']=='2026-09-01': row['mock_goods_amount']=10000/75
        result=self.run_agent()
        self.assertEqual(result['workflow_status'],'completed_no_anomaly')
        self.assertNotIn('decompose_gross_gmv',self.engine.trace['nodes_executed'])

    def test_aov_branch_forced(self):
        for row in self.adapter.rows:
            if row['mock_paid_date']=='2026-09-01': row['mock_goods_amount']=35
        result=self.run_agent()
        self.assertEqual(result['primary_driver']['metric_id'],'aov')
        self.assertIn('decompose_aov',self.engine.trace['nodes_executed'])

    def test_customer_structure_context(self):
        self.raw['context']={'customer_structure':True}
        result=self.run_agent()
        self.assertIn('orders_new_returning',[x['relationship_id'] for x in result['diagnostic_path']])

    def test_session_unavailable_is_partial(self):
        self.raw['context']={'traffic_view':True}
        result=self.run_agent()
        self.assertEqual(result['workflow_status'],'partial')
        self.assertEqual(result['stop_reason'],'data_unavailable')
        self.assertTrue(result['failed_branches'])

    def test_invalid_input_is_traced(self):
        result=self.run_agent(raw={'metric_id':'invented'})
        self.assertEqual(result['stop_reason'],'invalid_input')
        self.assertEqual(result['workflow_status'],'blocked')
        self.assertTrue(self.engine.trace_path.exists())

    def test_semantic_conflict_stops(self):
        self.adapter.semantic_consistent=False
        result=self.run_agent()
        self.assertEqual(result['stop_reason'],'semantic_conflict')
        self.assertFalse(result['key_findings'])

    def test_duplicate_quality_blocks(self):
        self.adapter.rows.append(copy.deepcopy(self.adapter.rows[0]))
        result=self.run_agent()
        self.assertEqual(result['stop_reason'],'data_quality_boundary')

    def test_incomplete_period_blocks(self):
        self.raw['current_period']['end']='2026-09-05'
        self.assertEqual(self.run_agent()['stop_reason'],'data_quality_boundary')

    def test_missing_mapping_does_not_guess(self):
        del self.adapter.mapping['semantic_mapping']['customer_id']
        result=self.run_agent()
        self.assertEqual(result['workflow_status'],'partial')
        self.assertEqual(result['stop_reason'],'data_unavailable')

    def test_transient_retry(self):
        original=self.adapter.metric
        count=[0]
        def flaky(*args):
            count[0]+=1
            if count[0]==1: raise TransientError('temporary data read failure')
            return original(*args)
        with patch.object(self.adapter,'metric',side_effect=flaky): result=self.run_agent()
        self.assertEqual(result['workflow_status'],'completed')
        self.assertEqual(self.engine.state.retry_count,1)

    def test_retry_exhaustion(self):
        with patch.object(self.adapter,'metric',side_effect=TransientError('unavailable')):
            result=self.run_agent()
        self.assertEqual(result['workflow_status'],'failed')
        calls=[x for x in self.engine.trace['skills_called'] if x['skill']=='metric_compare']
        self.assertEqual(len(calls),2)

    def test_max_depth_stop(self):
        self.definition['policy']['diagnosis_policy']['max_depth']=1 # test-only in-memory policy fixture
        self.assertEqual(self.run_agent()['stop_reason'],'max_depth_reached')

    def test_min_contribution_stop(self):
        router=Router(self.definition,ConstrainedRouter())
        state=WorkflowState(selected_driver={'aligned_share':0.19})
        self.assertEqual(router.stop(state),'below_min_contribution')
