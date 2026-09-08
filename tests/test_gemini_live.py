"""Opt-in-by-key live test. SQLite rows here are synthetic test fixtures, not Olist."""
import os
import json
import unittest
from uuid import uuid4
from business_performance_agent.llm.gemini_client import GeminiLLMClient
from business_performance_agent.llm.intent_parser import IntentParser
from business_performance_agent.llm.report_generator import ReportGenerator
from business_performance_agent.runtime.engine import Runtime
from business_performance_agent.tools.sqlite_query_tool import SQLiteQueryTool
from business_performance_agent.workflows.definition import load_workflow
from tests import test_sqlite_adapter


@unittest.skipUnless(os.environ.get('GEMINI_API_KEY'), 'GEMINI_API_KEY not configured')
class GeminiLiveTests(unittest.TestCase):
    def test_live_provider_with_synthetic_sqlite_workflow(self):
        fixture = test_sqlite_adapter.SQLiteTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        client = GeminiLLMClient()
        self.addCleanup(client.close)
        artifact = {'dataset':'synthetic_sqlite_fixture', 'production_database':False,
                    'llm_events':client.events, 'status':'not_completed'}
        def save():
            path = fixture.settings.root / 'logs' / ('gemini-live-' + str(uuid4()) + '.json')
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(json.dumps(artifact,ensure_ascii=False,indent=2),encoding='utf-8')
            print('Live test trace: ' + str(path))
        self.addCleanup(save)
        definition = load_workflow(fixture.settings.workflow)
        raw = IntentParser(fixture.knowledge, definition, client).parse(
            'Diagnose gross_gmv. Current 2018-06-01 to 2018-06-30. Baseline 2018-05-01 to 2018-05-31. No filters.')
        runtime = Runtime(fixture.knowledge, SQLiteQueryTool(fixture.adapter), definition, fixture.settings, client)
        output = runtime.run(raw)
        artifact['workflow_trace'] = runtime.trace
        self.assertEqual(output['result']['workflow_status'], 'completed',
                         {'limitations':output['result']['limitations'], 'events':client.events})
        renderer = ReportGenerator(client)
        report = renderer.generate(output['result'],trace=runtime.trace)
        self.assertTrue(report)
        succeeded = {e['purpose'] for e in client.events if e['status']=='success'}
        self.assertTrue({'intent','routing'} <= succeeded, client.events)
        self.assertEqual(renderer.metadata['report_renderer'],'gemini' if 'report' in succeeded else 'deterministic_fallback')
        artifact['status']='success'
