import io
import json
import os
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch, Mock
from tempfile import TemporaryDirectory
from pathlib import Path
from urllib.error import HTTPError, URLError

from business_performance_agent.config.settings import DeepSeekSettings
from business_performance_agent.llm.deepseek_client import DeepSeekLLMClient, NoRedirect
from business_performance_agent.llm.providers import create_client
from business_performance_agent.llm.report_generator import ReportGenerator
from business_performance_agent.models.schemas import BoundaryError
from evals.live_runner import provider_metrics


class DeepSeekProviderTests(unittest.TestCase):
    def ask(self, client):
        return client.structured_generate(
            purpose="routing",
            payload={"allowed_candidates": ["a", "b"]},
            schema={"type": "object", "required": ["choice", "rationale"]},
        )

    def client(self, responses):
        opener = Mock()

        def request(*args, **kwargs):
            item = next(responses)
            if isinstance(item, Exception):
                raise item
            return io.BytesIO(json.dumps(item).encode())

        opener.open.side_effect = request
        client = DeepSeekLLMClient(
            settings=DeepSeekSettings(api_key="test-only-secret"),
            opener=opener,
            sleep=lambda _: None,
        )
        return client, opener

    @staticmethod
    def envelope(content):
        return {"choices": [{"finish_reason": "stop", "message": {"content": content}}]}

    def test_config_from_environment_and_secret_repr(self):
        with patch.dict(
            os.environ,
            {
                "DEEPSEEK_API_KEY": "private-canary",
                "DEEPSEEK_BASE_URL": "https://example.com/v1",
                "DEEPSEEK_MODEL": "custom-model",
                "DEEPSEEK_TIMEOUT": "12.5",
            },
        ):
            config = DeepSeekSettings()
            self.assertEqual(config.timeout, 12.5)
            self.assertEqual(config.model, "custom-model")
            self.assertNotIn("private-canary", repr(config))
        for value in (0, -1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                DeepSeekSettings(timeout=value)
        with self.assertRaises(ValueError):
            DeepSeekSettings(base_url="https://user:secret@example.com")

    def test_missing_key_never_sends_request(self):
        opener = Mock()
        client = DeepSeekLLMClient(settings=DeepSeekSettings(api_key=""), opener=opener)
        with self.assertRaises(BoundaryError):
            self.ask(client)
        opener.open.assert_not_called()
        self.assertEqual(len(client.events), 1)

    def test_factory_and_unknown_provider(self):
        self.assertEqual(create_client("gemini").provider_name, "gemini")
        self.assertEqual(create_client("deepseek").provider_name, "deepseek")
        with self.assertRaises(ValueError):
            create_client("invented")

    def test_request_and_response_parsing(self):
        client, opener = self.client(
            iter([self.envelope('{"choice":"a","rationale":"valid"}')])
        )
        self.assertEqual(self.ask(client)["choice"], "a")
        req = opener.open.call_args.args[0]
        body = json.loads(req.data)
        self.assertEqual(body["response_format"], {"type": "json_object"})
        self.assertFalse(body["stream"])
        self.assertNotIn("tools", body)
        self.assertIn("JSON", body["messages"][0]["content"])
        self.assertNotIn("test-only-secret", json.dumps(client.events) + str(body))
        self.assertEqual(client.events[0]["provider"], "deepseek")
        self.assertEqual(
            opener.open.call_args.kwargs["timeout"], client.settings.timeout
        )

    def test_invalid_structures_retry_at_most_twice(self):
        for content in (
            "",
            "{}",
            "[]",
            '{"choice":"outside","rationale":"x"}',
            '{"choice":"a","rationale":"x","extra":1}',
            '{"choice":"b","choice":"a","rationale":"x"}',
        ):
            with self.subTest(content=content):
                client, opener = self.client(iter([self.envelope(content)] * 2))
                with self.assertRaises(BoundaryError):
                    self.ask(client)
                self.assertEqual(opener.open.call_count, 2)

    def test_nonterminal_response_is_rejected(self):
        reply = self.envelope('{"choice":"a","rationale":"valid"}')
        reply["choices"][0]["finish_reason"] = "length"
        client, _ = self.client(iter([reply, reply]))
        with self.assertRaises(BoundaryError):
            self.ask(client)

    def test_http_and_timeout_normalization_and_redaction(self):
        for code in (429, 500, 501, 503, 504, 401):
            errors = [
                HTTPError(
                    "https://example.com",
                    code,
                    "test-only-secret",
                    {},
                    io.BytesIO(b"test-only-secret"),
                )
                for _ in range(2)
            ]
            client, opener = self.client(iter(errors))
            with self.assertRaises(BoundaryError) as caught:
                self.ask(client)
            self.assertEqual(opener.open.call_count, 1 if code == 401 else 2)
            self.assertNotIn(
                "test-only-secret", str(caught.exception) + json.dumps(client.events)
            )
            self.assertEqual(client.events[-1]["http_status"], code)
            self.assertEqual(
                provider_metrics([{"actual": {"events": client.events}}])[
                    "provider_failures"
                ],
                opener.open.call_count,
            )
        for error in (TimeoutError("test-only-secret"), URLError("test-only-secret")):
            client, opener = self.client(iter([error, error]))
            with self.assertRaises(BoundaryError):
                self.ask(client)
            self.assertEqual(
                provider_metrics([{"actual": {"events": client.events}}])[
                    "provider_failures"
                ],
                2,
            )
            self.assertTrue(client.events[-1]["transient_provider_failure"])

    def test_redirect_does_not_forward_credentials(self):
        self.assertIsNone(
            NoRedirect().redirect_request(
                None, None, 302, "", {}, "https://other.example"
            )
        )

    def test_report_success_and_fallback_share_renderer(self):
        result = {
            "workflow_status": "completed",
            "stop_reason": "target_coverage_reached",
            "key_findings": [{"claim_id": "c1", "claim": "verified"}],
            "warnings": [],
            "limitations": [],
        }
        client = DeepSeekLLMClient(
            transport=lambda *_: '{"selections":[{"claim_id":"c1","variant":0}]}'
        )
        renderer = ReportGenerator(client)
        self.assertIn("verified", renderer.generate(result))
        self.assertEqual(renderer.metadata["report_renderer"], "deepseek")
        client, _ = self.client(
            iter(
                [
                    HTTPError("https://example.com", 503, "redacted", {}, None)
                    for _ in range(2)
                ]
            )
        )
        renderer = ReportGenerator(client)
        self.assertIn("verified", renderer.generate(result))
        self.assertEqual(renderer.metadata["report_renderer"], "deterministic_fallback")
        self.assertEqual(renderer.metadata["provider_error_code"], 503)

    def test_smoke_uses_selected_provider_single_attempt(self):
        from business_performance_agent.app.provider_smoke import main

        reply = json.dumps(
            dict(
                metric_id="gross_gmv",
                current_period=dict(start="2026-08-01", end="2026-08-31"),
                baseline_period=dict(start="2026-07-01", end="2026-07-31"),
                filters={},
            )
        )
        client = DeepSeekLLMClient(transport=lambda *_: reply)
        with (
            patch("sys.argv", ["smoke", "--provider", "deepseek"]),
            patch(
                "business_performance_agent.app.provider_smoke.create_client",
                return_value=client,
            ) as factory,
            redirect_stdout(io.StringIO()) as output,
        ):
            self.assertEqual(main(), 0)
        factory.assert_called_once_with("deepseek", None, max_attempts=1)
        self.assertIn("API_OK", output.getvalue())

    def test_cli_selects_deepseek_and_records_renderer(self):
        from business_performance_agent.app.cli import main
        from business_performance_agent.config.settings import Settings

        def transport(request, schema):
            payload = request["payload"]
            if request["purpose"] == "routing":
                return json.dumps(
                    dict(
                        choice=payload["allowed_candidates"][0],
                        rationale="offline transport",
                    )
                )
            return json.dumps(
                dict(
                    selections=[
                        dict(claim_id=c["claim_id"], variant=0)
                        for c in payload["claims"]
                    ]
                )
            )

        client = DeepSeekLLMClient(transport=transport)
        with (
            TemporaryDirectory() as directory,
            patch("sys.argv", ["bpa", "--provider", "deepseek", "--json"]),
            patch(
                "business_performance_agent.llm.providers.create_client",
                return_value=client,
            ),
            patch(
                "business_performance_agent.app.cli.Settings",
                return_value=Settings(logs=Path(directory)),
            ),
            redirect_stdout(io.StringIO()) as output,
        ):
            self.assertEqual(main(), 0)
            result = json.loads(output.getvalue())
            self.assertEqual(result["execution_mode"]["llm"], "deepseek")
            self.assertEqual(result["execution_mode"]["report_rendering"], "deepseek")

    def test_live_worker_receives_only_selected_provider_key(self):
        from evals.live_runner import worker
        from evals.runner import write_json

        def subprocess_run(*args, **kwargs):
            env = kwargs["env"]
            self.assertNotIn("GEMINI_API_KEY", env)
            self.assertIn("DEEPSEEK_API_KEY", env)
            work = kwargs["cwd"]
            request = json.loads((work / "input.json").read_text())
            self.assertEqual(request["provider"], "deepseek")
            self.assertEqual(request["model"], "test-model")
            write_json(work / "actual.json", {"checked": True})
            return Mock(returncode=0)

        with TemporaryDirectory() as directory:
            database = Path(directory) / "data.db"
            mapping = Path(directory) / "mapping.json"
            database.write_bytes(b"unused fake database")
            mapping.write_text("{}")
            with (
                patch.dict(
                    os.environ,
                    {
                        "GEMINI_API_KEY": "fake-gemini",
                        "DEEPSEEK_API_KEY": "fake-deepseek",
                    },
                ),
                patch("evals.live_runner.subprocess.run", side_effect=subprocess_run),
            ):
                self.assertEqual(
                    worker(
                        database,
                        mapping,
                        {"question": "test"},
                        "deepseek",
                        "test-model",
                    ),
                    {"checked": True},
                )


@unittest.skipUnless(
    os.environ.get("BPA_RUN_DEEPSEEK_LIVE_TESTS") == "1"
    and __name__ == "tests.test_deepseek_provider"
    and "discover" not in __import__("sys").argv
    and bool(os.environ.get("DEEPSEEK_API_KEY")),
    "Explicit opt-in DeepSeek live test only",
)
class DeepSeekLiveTests(unittest.TestCase):
    def test_live_intent_smoke(self):
        from business_performance_agent.app.provider_smoke import main

        with patch("sys.argv", ["smoke", "--provider", "deepseek"]):
            self.assertEqual(main(), 0)
