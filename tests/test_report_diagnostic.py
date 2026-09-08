import json
import unittest
import io
import tempfile
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch
from pathlib import Path

from business_performance_agent.app.report_diagnostic import DiagnosticClient, metadata, main
from business_performance_agent.llm.gemini_client import response_schema
from business_performance_agent.llm.report_generator import ReportGenerator
from business_performance_agent.models.schemas import BoundaryError


class ReportDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.fixture = json.loads((Path(__file__).parent/'fixtures/gemini_report_failure.json').read_text(encoding='utf-8'))

    def test_fixture_is_minimal_synthetic_report(self):
        self.assertEqual(self.fixture['fixture_source'],'synthetic_sqlite_fixture')
        self.assertEqual(set(self.fixture['payload']),{'claims'})
        for claim in self.fixture['payload']['claims']:
            self.assertEqual(set(claim),{'claim_id','variants'})

    def test_schema_experiment_does_not_mutate_local_contract(self):
        expected=response_schema('report',self.fixture['payload'],self.fixture['schema'])
        config=DiagnosticClient('no_variant_enum').generation_config(expected)
        local=expected['properties']['selections']['items']['properties']['variant']
        remote=config['response_json_schema']['properties']['selections']['items']['properties']['variant']
        self.assertEqual(local['enum'],[0])
        self.assertNotIn('enum',remote)

    def test_minimal_server_config_still_rejects_invalid_report(self):
        for invalid in [1,True,'0']:
            reply={'selections':[{'claim_id':c['claim_id'],'variant':invalid} for c in self.fixture['payload']['claims']]}
            client=DiagnosticClient('minimal',transport=lambda *_:json.dumps(reply))
            with self.assertRaises(BoundaryError):
                client.structured_generate(purpose='report',payload=self.fixture['payload'],schema=self.fixture['schema'])
            self.assertEqual(len(client.events),1)

    def test_validated_report_render_without_workflow(self):
        fixture=self.fixture
        reply={'selections':[{'claim_id':c['claim_id'],'variant':0} for c in reversed(fixture['payload']['claims'])]}
        client=DiagnosticClient('baseline',transport=lambda *_:json.dumps(reply))
        findings=[{'claim_id':c['claim_id'],'claim':c['variants'][0]} for c in fixture['payload']['claims']]
        result={'key_findings':findings,'workflow_status':'completed','stop_reason':'target_coverage_reached',
                'warnings':['retained warning'],'limitations':['retained limitation']}
        report=ReportGenerator(client).generate(result)
        for item in findings: self.assertIn(item['claim'],report)
        self.assertIn('retained warning',report)
        self.assertIn('retained limitation',report)
        self.assertEqual(client.events[-1]['status'],'success')

    def test_metadata_changes_for_schema_experiment(self):
        a=metadata(DiagnosticClient('baseline',model=self.fixture['model']),self.fixture)
        b=metadata(DiagnosticClient('no_variant_enum',model=self.fixture['model']),self.fixture)
        self.assertEqual(a['model'],b['model'])
        self.assertEqual(a['prompt_character_count'],b['prompt_character_count'])
        self.assertNotEqual(a['request_sha256'],b['request_sha256'])

    def test_third_identical_503_is_refused_before_request(self):
        info=metadata(DiagnosticClient('baseline',model=self.fixture['model']),self.fixture)
        with tempfile.TemporaryDirectory() as directory:
            log=Path(directory)/'diagnostics.json'
            log.write_text(json.dumps([dict(info,events=[{'http_status':503}])]*2),encoding='utf-8')
            fixture=Path(__file__).parent/'fixtures/gemini_report_failure.json'
            with patch('sys.argv',['report_diagnostic','--fixture',str(fixture),'--log',str(log)]), \
                 patch.object(DiagnosticClient,'_request',side_effect=AssertionError('Network must not be called')), \
                 redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                main()
            self.assertEqual(error.exception.code,2)


if __name__ == '__main__': unittest.main()
