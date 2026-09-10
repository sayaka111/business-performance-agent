"""Explicit opt-in live integration; never enabled by API key alone."""

import os
import sys
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


@unittest.skipUnless(
    __name__ == "tests.test_gemini_live"
    and "discover" not in sys.argv
    and any(arg == __name__ or arg.startswith(__name__ + ".") for arg in sys.argv[1:])
    and os.environ.get("BPA_RUN_LIVE_TESTS") == "1"
    and os.environ.get("GEMINI_API_KEY"),
    "Live requires explicit module, BPA_RUN_LIVE_TESTS=1 and GEMINI_API_KEY",
)
class GeminiLiveTests(unittest.TestCase):
    def test_live_provider_with_synthetic_sqlite_workflow(self):
        fixture = test_sqlite_adapter.SQLiteTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        client = GeminiLLMClient()
        self.addCleanup(client.close)
        artifact = {
            "dataset": "synthetic_sqlite_fixture",
            "production_database": False,
            "llm_events": client.events,
            "status": "not_completed",
        }

        def save():
            path = (
                fixture.settings.root
                / "logs"
                / ("gemini-live-" + str(uuid4()) + ".json")
            )
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print("Live test trace: " + str(path))

        self.addCleanup(save)
        definition = load_workflow(fixture.settings.workflow)
        raw = IntentParser(fixture.knowledge, definition, client).parse(
            "Diagnose gross_gmv. Current 2026-08-31 to 2026-09-06. Baseline 2026-08-24 to 2026-08-30. No filters."
        )
        runtime = Runtime(
            fixture.knowledge,
            SQLiteQueryTool(fixture.adapter),
            definition,
            fixture.settings,
            client,
        )
        output = runtime.run(raw)
        artifact["workflow_trace"] = runtime.trace
        self.assertEqual(
            output["result"]["workflow_status"],
            "completed",
            {"limitations": output["result"]["limitations"], "events": client.events},
        )
        renderer = ReportGenerator(client)
        report = renderer.generate(output["result"], trace=runtime.trace)
        self.assertTrue(report)
        succeeded = {e["purpose"] for e in client.events if e["status"] == "success"}
        self.assertTrue({"intent", "routing"} <= succeeded, client.events)
        self.assertEqual(
            renderer.metadata["report_renderer"],
            "gemini" if "report" in succeeded else "deterministic_fallback",
        )
        artifact["status"] = "success"
