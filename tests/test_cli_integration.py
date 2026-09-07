"""Real CLI smoke tests; reuse the Runtime and frozen result validator."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from business_performance_agent.config.settings import ROOT
from business_performance_agent.llm.result_builder import validate_result


class CLIIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'agent project'
        self.root.mkdir()
        # Isolate generated logs without adding new production settings or wrappers.
        for name in ('business_performance_agent', 'specs', 'examples'):
            shutil.copytree(ROOT / name, self.root / name, ignore=shutil.ignore_patterns('__pycache__'))
        for name in ('run.ps1',):
            shutil.copy2(ROOT / name, self.root / name)
        self.request = json.loads((self.root / 'examples/gmv_input.json').read_text(encoding='utf-8'))
        schema_path = (self.root / 'specs/workflows/gmv_diagnosis/output_schema.json')
        self.output_schema = json.loads(schema_path.read_text(encoding='utf-8'))
        self.before = self.source_hashes()

    def source_hashes(self):
        paths = []
        for name in ('business_performance_agent', 'specs'):
            paths.extend(p for p in (self.root / name).rglob('*')
                         if p.is_file() and '__pycache__' not in p.parts)
        return {str(p.relative_to(self.root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}

    def invoke(self, *arguments, command=None):
        env = dict(os.environ, PYTHONUTF8='1')
        process = subprocess.run(command or [sys.executable, '-m', 'business_performance_agent', *arguments],
                                 cwd=self.root, env=env, capture_output=True, text=True,
                                 encoding='utf-8', timeout=30,
                                 creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        self.assertEqual(self.before, self.source_hashes(), 'CLI changed business specifications or implementation')
        return process

    def assert_output(self, process, code=0, llm='mock'):
        self.assertEqual(process.returncode, code, process.stderr)
        self.assertEqual(process.stderr, '')
        output = json.loads(process.stdout)  # Fails if JSON stdout is contaminated by prose.
        self.assertEqual(output['execution_mode'], {
            'dataset': 'mock', 'dataset_id': 'mock_retail_v1',
            'llm': llm, 'real_business_data': False,
        })
        validate_result(output['result'], self.output_schema)
        trace = json.loads(Path(output['trace_path']).read_text(encoding='utf-8'))
        self.assertEqual(trace['run_id'], output['run_id'])
        self.assertEqual(trace['final_structured_result'], output['result'])
        self.assertIn('validate_input', trace['nodes_executed'])
        self.assertEqual(trace['nodes_executed'][-1], 'complete')
        return output, trace

    def test_structured_mock_request_runs_original_workflow(self):
        request_path = self.root / 'request.json'
        request_path.write_text(json.dumps(self.request), encoding='utf-8')
        output, trace = self.assert_output(self.invoke('--input', str(request_path), '--mock-llm', '--json'))
        self.assertEqual(trace['input'], self.request)
        self.assertEqual(output['result']['workflow_status'], 'completed')
        self.assertEqual(output['result']['target']['relative_change'], -0.265)
        self.assertEqual(output['result']['primary_driver']['metric_id'], 'orders')
        self.assertEqual(output['result']['stop_reason'], 'target_coverage_reached')
        self.assertIn('dimension_drilldown', trace['nodes_executed'])
        self.assertEqual(len({step['skill'] for step in trace['skills_called']}), 7)

    def test_unconfigured_llm_preserves_actual_stop_reason(self):
        output, trace = self.assert_output(self.invoke('--input', 'examples/gmv_input.json', '--json'), llm='unconfigured')
        self.assertEqual(output['result']['stop_reason'], 'evidence_boundary_reached')
        self.assertTrue(any(d.get('rationale') == 'llm_provider_not_configured' for d in trace['router_decisions']))

    def test_unsupported_input_returns_original_blocked_json(self):
        for change in ({'intent': 'metric_diagnosis'}, {'current_period': {'start': '2026-09-01', 'end': '2026-09-05'}}):
            with self.subTest(change=change):
                raw = dict(self.request, **change)
                path = self.root / 'unsupported.json'
                path.write_text(json.dumps(raw), encoding='utf-8')
                output, trace = self.assert_output(self.invoke('--input', str(path), '--mock-llm', '--json'), code=1)
                self.assertEqual(trace['input'], raw)  # No silent field removal or date substitution.
                self.assertEqual(output['result']['workflow_status'], 'blocked')
                self.assertEqual(output['result']['stop_reason'], 'invalid_input' if 'intent' in change else 'data_quality_boundary')

    def test_input_errors_do_not_fall_back_to_demo(self):
        bad = self.root / 'bad.json'
        bad.write_text('{broken', encoding='utf-8')
        cases = [('--input', str(bad), '--json'), ('--input', 'missing.json', '--json'),
                 ('--input', 'examples/gmv_input.json', '--question', '{}', '--json'),
                 ('--question', 'Diagnose this week GMV', '--json')]
        for arguments in cases:
            with self.subTest(arguments=arguments):
                process = self.invoke(*arguments)
                self.assertEqual(process.returncode, 2)
                self.assertEqual(process.stdout, '')
                self.assertIn('error:', process.stderr)
                self.assertFalse((self.root / 'logs').exists())

    def test_text_output_discloses_mock_data(self):
        process = self.invoke('--input', 'examples/gmv_input.json', '--mock-llm')
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertTrue(process.stdout.startswith('[MOCK DATA / 非真实经营数据]'))
        self.assertIn('LLM=mock', process.stdout)

    def test_utf8_bom_request_preserves_user_filters(self):
        self.request['filters'] = {'channel': 'paid_search'}
        path = self.root / '中文 请求.json'
        path.write_text(json.dumps(self.request, ensure_ascii=False), encoding='utf-8-sig')
        output, trace = self.assert_output(self.invoke('--input', str(path), '--mock-llm', '--json'))
        self.assertEqual(trace['input']['filters'], self.request['filters'])
        self.assertEqual(output['result']['target']['baseline_value'], 3400)

    @unittest.skipUnless(os.name == 'nt', 'PowerShell entry point is Windows-specific')
    def test_existing_powershell_entry_point(self):
        shell = shutil.which('pwsh') or shutil.which('powershell')
        if shell is None:
            self.skipTest('PowerShell not available')
        command = [shell, '-NoProfile', '-File', str(self.root / 'run.ps1'),
                   '-InputFile', 'examples/gmv_input.json', '-MockLLM', '-Json']
        output, _ = self.assert_output(self.invoke(command=command))
        self.assertEqual(output['result']['workflow_status'], 'completed')


if __name__ == '__main__':
    unittest.main()
