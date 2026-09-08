import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from business_performance_agent.config.settings import Settings
from business_performance_agent.tools.knowledge_loader import KnowledgeLoader
from business_performance_agent.tools.metric_definition import execute
from business_performance_agent.models.schemas import BoundaryError
from business_performance_agent.app.gemini_tool_demo import run, safe_error_metadata, generate_with_retry

try:
    from google.genai import types
except ImportError:
    types = None

class MetricDefinitionToolTests(unittest.TestCase):
    def setUp(self):
        self.knowledge = KnowledgeLoader(Settings().business / "knowledge")

    def test_exact_registry_result_and_defensive_copy(self):
        result = execute(self.knowledge, {"metric_id": "gross_gmv"})
        self.assertEqual(result["metric"], self.knowledge.get_metric("gross_gmv"))
        result["metric"]["id"] = "modified"
        self.assertEqual(self.knowledge.get_metric("gross_gmv")["id"], "gross_gmv")

    def test_error_metadata_excludes_provider_payload(self):
        exc = RuntimeError("secret response")
        exc.code = 503
        exc.status = "UNAVAILABLE"
        exc.response = {"api_key": "do-not-log"}
        info = safe_error_metadata(exc, [{"event": "llm_request", "step": 1},
                                         {"event": "tool_result"}])
        self.assertEqual(info, {"http_status": 503, "api_status": "UNAVAILABLE",
                                "request_step": 1, "tools_executed": 1})
        exc.code = "secret"
        exc.status = "private message"
        info = safe_error_metadata(exc, [])
        self.assertIsNone(info["http_status"])
        self.assertIsNone(info["api_status"])

    def test_retry_is_bounded_and_preserves_request(self):
        error = RuntimeError("private response")
        error.code = 503
        generate = Mock(side_effect=[error, error, "ok"])
        client = SimpleNamespace(models=SimpleNamespace(generate_content=generate))
        contents = [object()]
        trace = {"events": []}
        with patch("business_performance_agent.app.gemini_tool_demo.time.sleep") as sleep:
            self.assertEqual(generate_with_retry(client, trace, 1, contents=contents), "ok")
        self.assertEqual(generate.call_count, 3)
        self.assertTrue(all(c.kwargs["contents"] is contents for c in generate.call_args_list))
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [2, 4])
        generate.side_effect = error
        generate.reset_mock()
        with patch("business_performance_agent.app.gemini_tool_demo.time.sleep"), self.assertRaises(RuntimeError):
            generate_with_retry(client, {"events": []}, 1, contents=contents)
        self.assertEqual(generate.call_count, 3)
        error.code = 400
        generate.reset_mock()
        with self.assertRaises(RuntimeError):
            generate_with_retry(client, {"events": []}, 1, contents=contents)
        self.assertEqual(generate.call_count, 1)

    def test_arguments_rejected(self):
        for args in ({}, {"metric_id": 3}, {"metric_id": "gross_gmv", "sql": "SELECT 1"}):
            with self.subTest(args=args), self.assertRaises(ValueError):
                execute(self.knowledge, args)
        with self.assertRaises(BoundaryError):
            execute(self.knowledge, {"metric_id": "invented"})

    def test_roundtrip_without_id_keyword_helper(self):
        # Model a SDK whose convenience factory does not accept call IDs.
        class Part(SimpleNamespace):
            @staticmethod
            def from_text(*, text):
                return Part(text=text, function_call=None)

            @staticmethod
            def from_function_response(*, name, response):
                raise AssertionError("Use FunctionResponse to preserve the call ID")

        sdk = SimpleNamespace(Part=Part)
        for name in ("Content", "Tool", "FunctionDeclaration", "GenerateContentConfig",
                     "AutomaticFunctionCallingConfig", "ToolConfig", "FunctionCallingConfig", "FunctionResponse"):
            setattr(sdk, name, SimpleNamespace)
        call = SimpleNamespace(name="get_metric_definition", args={"metric_id": "gross_gmv"}, id="call-1")
        content = SimpleNamespace(parts=[Part(function_call=call)])
        final = SimpleNamespace(parts=[Part.from_text(text="Definition received")])
        client = SimpleNamespace(models=SimpleNamespace(generate_content=Mock(side_effect=[
            SimpleNamespace(candidates=[SimpleNamespace(content=content)]),
            SimpleNamespace(candidates=[SimpleNamespace(content=final)], text="Definition received"),
        ])))
        trace = {"events": []}
        run("What is GMV?", "gemini-3.8-flash", client, sdk, self.knowledge, trace)
        sent = client.models.generate_content.call_args.kwargs["contents"]
        response = sent[2].parts[0].function_response
        self.assertEqual(response.id, "call-1")
        self.assertEqual(response.response["metric"], self.knowledge.get_metric("gross_gmv"))
        self.assertTrue(trace["tool_called"])

    @unittest.skipIf(types is None, "Install optional gemini dependency")
    def test_manual_roundtrip_preserves_call_id_and_content(self):
        content = types.Content(role="model", parts=[types.Part(function_call=types.FunctionCall(
            name="get_metric_definition", args={"metric_id": "gross_gmv"}, id="call-1"))])
        final = types.Content(role="model", parts=[types.Part.from_text(text="Definition received")])
        client = SimpleNamespace(models=SimpleNamespace(generate_content=Mock(side_effect=[
            types.GenerateContentResponse(candidates=[types.Candidate(content=content)]),
            types.GenerateContentResponse(candidates=[types.Candidate(content=final)]),
        ])))
        trace = {"events": []}
        self.assertEqual(run("What is gross GMV?", "gemini-3.8-flash", client, types, self.knowledge, trace), "Definition received")
        self.assertTrue(trace["tool_called"])
        sent = client.models.generate_content.call_args.kwargs["contents"]
        self.assertIs(sent[1], content)
        self.assertEqual(sent[2].parts[0].function_response.id, "call-1")
        self.assertEqual(trace["events"][1]["arguments"], {"metric_id": "gross_gmv"})

    @unittest.skipIf(types is None, "Install optional gemini dependency")
    def test_unknown_tool_is_never_executed(self):
        content = types.Content(role="model", parts=[types.Part(function_call=types.FunctionCall(name="delete_data", args={}))])
        client = SimpleNamespace(models=SimpleNamespace(generate_content=Mock(return_value=
            types.GenerateContentResponse(candidates=[types.Candidate(content=content)]))))
        with self.assertRaisesRegex(ValueError, "unregistered"):
            run("test", "gemini-3.8-flash", client, types, self.knowledge, {"events": []})

    @unittest.skipIf(types is None, "Install optional gemini dependency")
    def test_no_tool_is_not_reported_as_tool_success(self):
        content = types.Content(role="model", parts=[types.Part.from_text(text="Only definitions are supported")])
        client = SimpleNamespace(models=SimpleNamespace(generate_content=Mock(return_value=
            types.GenerateContentResponse(candidates=[types.Candidate(content=content)]))))
        trace = {"events": []}
        run("hello", "gemini-3.8-flash", client, types, self.knowledge, trace)
        self.assertFalse(trace["tool_called"])
