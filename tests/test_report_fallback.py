import copy
import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

from business_performance_agent.llm.gemini_client import GeminiLLMClient
from business_performance_agent.llm.report_generator import ReportGenerator


class ProviderFailure(Exception):
    def __init__(self, code):
        self.code = code
        self.message = "temporary provider error with private details"


class ReportFallbackTests(unittest.TestCase):
    def setUp(self):
        fixture = json.loads(
            (Path(__file__).parent / "fixtures/report_claims.json").read_text(
                encoding="utf-8"
            )
        )
        self.result = {
            "workflow_status": "completed",
            "stop_reason": "target_coverage_reached",
            "key_findings": [
                {"claim_id": c["claim_id"], "claim": c["variants"][0]}
                for c in fixture["payload"]["claims"]
            ],
            "warnings": ["Observed data warning"],
            "limitations": ["Existing evidence boundary"],
        }
        self.reply = json.dumps(
            {
                "selections": [
                    {"claim_id": c["claim_id"], "variant": 0}
                    for c in reversed(self.result["key_findings"])
                ]
            }
        )

    def test_transient_failure_uses_markdown_fallback_and_traces_report_only(self):
        for code in (429, 503, 504):
            with self.subTest(code=code):
                transport = Mock(side_effect=ProviderFailure(code))
                sleep = Mock()
                client = GeminiLLMClient(transport=transport, sleep=sleep)
                client.events.append(
                    {
                        "purpose": "routing",
                        "attempt": 9,
                        "status": "failed",
                        "http_status": 500,
                    }
                )
                generator = ReportGenerator(client)
                before = copy.deepcopy(self.result)
                trace = {}
                report = generator.generate(self.result, trace=trace)
                self.assertEqual(transport.call_count, 2)
                sleep.assert_called_once_with(2)
                self.assertEqual(
                    trace,
                    {
                        "report_renderer": "deterministic_fallback",
                        "provider_error_code": code,
                        "retry_count": 1,
                    },
                )
                self.assertEqual(before, self.result)
                self.assertTrue(report.startswith("# GMV 诊断报告\n\n"))
                for finding in self.result["key_findings"]:
                    self.assertIn("- " + finding["claim"], report)
                self.assertIn(self.result["warnings"][0], report)
                self.assertIn(self.result["limitations"][0], report)
                self.assertNotIn(
                    "private details",
                    report + json.dumps(trace) + json.dumps(client.events),
                )
                self.assertTrue(
                    all(e["transient_provider_failure"] for e in client.events[1:])
                )

    def test_recovered_gemini_keeps_validated_gemini_order(self):
        client = GeminiLLMClient(
            transport=Mock(side_effect=[ProviderFailure(503), self.reply]), sleep=Mock()
        )
        renderer = ReportGenerator(client)
        trace = {}
        report = renderer.generate(self.result, trace=trace)
        self.assertEqual(
            trace,
            {"report_renderer": "gemini", "provider_error_code": 503, "retry_count": 1},
        )
        claims = self.result["key_findings"]
        self.assertLess(
            report.index(claims[-1]["claim"]), report.index(claims[0]["claim"])
        )

    def test_normal_success_and_metadata_do_not_leak_previous_failure(self):
        transport = Mock(
            side_effect=[ProviderFailure(504), ProviderFailure(504), self.reply]
        )
        renderer = ReportGenerator(GeminiLLMClient(transport=transport, sleep=Mock()))
        renderer.generate(self.result)
        trace = {}
        renderer.generate(self.result, trace=trace)
        self.assertEqual(
            trace,
            {
                "report_renderer": "gemini",
                "provider_error_code": None,
                "retry_count": 0,
            },
        )

    def test_nontransient_error_is_not_retried(self):
        transport = Mock(side_effect=ProviderFailure(400))
        sleep = Mock()
        renderer = ReportGenerator(GeminiLLMClient(transport=transport, sleep=sleep))
        renderer.generate(self.result)
        self.assertEqual(transport.call_count, 1)
        sleep.assert_not_called()
        self.assertEqual(renderer.metadata["retry_count"], 0)

    def test_empty_claims_do_not_call_provider(self):
        transport = Mock(side_effect=AssertionError("No request expected"))
        renderer = ReportGenerator(GeminiLLMClient(transport=transport))
        self.result["key_findings"] = []
        renderer.generate(self.result)
        transport.assert_not_called()
        self.assertEqual(
            renderer.metadata,
            {
                "report_renderer": "deterministic_fallback",
                "provider_error_code": None,
                "retry_count": 0,
            },
        )

    def test_cli_persists_fallback_metadata_without_changing_structured_result(self):
        from business_performance_agent.app.cli import main
        from business_performance_agent.config.settings import Settings
        from business_performance_agent.llm.client import MockLLMClient

        def transport(request, schema):
            if request["purpose"] == "report":
                raise ProviderFailure(503)
            return json.dumps(
                MockLLMClient().structured_generate(
                    purpose=request["purpose"],
                    payload=request["payload"],
                    schema=schema,
                )
            )

        client = GeminiLLMClient(transport=transport, sleep=Mock())
        with tempfile.TemporaryDirectory() as directory:
            settings = Settings(logs=Path(directory))
            output = io.StringIO()
            with (
                patch(
                    "sys.argv",
                    [
                        "bpa",
                        "--gemini",
                        "--input",
                        str(settings.root / "examples/gmv_input.json"),
                        "--json",
                    ],
                ),
                patch(
                    "business_performance_agent.app.cli.Settings", return_value=settings
                ),
                patch(
                    "business_performance_agent.llm.gemini_client.GeminiLLMClient",
                    return_value=client,
                ),
                redirect_stdout(output),
            ):
                self.assertEqual(main(), 0)
            result = json.loads(output.getvalue())
            trace = json.loads(Path(result["trace_path"]).read_text(encoding="utf-8"))
            self.assertEqual(trace["report_renderer"], "deterministic_fallback")
            self.assertEqual(trace["provider_error_code"], 503)
            self.assertEqual(trace["retry_count"], 1)
            self.assertEqual(trace["state"]["retry_count"], 0)
            self.assertEqual(trace["final_structured_result"], result["result"])
            self.assertEqual(
                result["execution_mode"]["report_rendering"], "deterministic_fallback"
            )
            self.assertTrue(result["report"].startswith("# GMV 诊断报告"))

    @unittest.skipUnless(
        importlib.util.find_spec("google"), "Optional Gemini SDK not installed"
    )
    def test_sdk_and_application_retries_do_not_multiply(self):
        try:
            from google import genai
            import httpx
        except ImportError:
            self.skipTest("Optional Gemini SDK not installed")
        requests = []

        def handler(request):
            requests.append(request)
            return httpx.Response(
                503,
                json={
                    "error": {
                        "code": 503,
                        "status": "UNAVAILABLE",
                        "message": "Temporary failure",
                    }
                },
            )

        original = genai.Client

        def sdk_factory(**kwargs):
            self.assertEqual(kwargs["http_options"].retry_options.attempts, 1)
            kwargs["http_options"].client_args = {
                "transport": httpx.MockTransport(handler),
                "trust_env": False,
            }
            return original(**kwargs)

        with (
            patch.dict("os.environ", {"GEMINI_API_KEY": "synthetic-test-key"}),
            patch.object(genai, "Client", side_effect=sdk_factory),
        ):
            client = GeminiLLMClient(sleep=Mock())
            try:
                renderer = ReportGenerator(client)
                renderer.generate(self.result)
            finally:
                client.close()
        self.assertEqual(
            len(requests), 2, "SDK must not multiply the two application attempts"
        )
        self.assertEqual(
            renderer.metadata,
            {
                "report_renderer": "deterministic_fallback",
                "provider_error_code": 503,
                "retry_count": 1,
            },
        )
