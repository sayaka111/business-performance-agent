"""Isolated live worker: only question, dates, synthetic data and frozen Agent."""

import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
sys.path.insert(0, str(root))
from isolation import install_guard

guard = install_guard(root, allow_network=True)
from business_performance_agent.config.settings import Settings
from business_performance_agent.tools.knowledge_loader import KnowledgeLoader
from business_performance_agent.workflows.definition import load_workflow
from business_performance_agent.data_contract.sqlite_adapter import SQLiteDatasetAdapter
from business_performance_agent.tools.sqlite_query_tool import SQLiteQueryTool
from business_performance_agent.runtime.engine import Runtime
from business_performance_agent.llm.providers import create_client
from business_performance_agent.llm.intent_parser import IntentParser
from business_performance_agent.llm.report_generator import ReportGenerator


class RequestBudgetReached(RuntimeError):
    pass


def bounded_client(provider, model=None):
    client = create_client(provider, model, max_attempts=2)
    request = client._request
    calls = [0]

    def limited(payload, schema):
        if calls[0] >= 8:
            raise RequestBudgetReached("Per-case evaluation request budget reached")
        calls[0] += 1
        return request(payload, schema)

    client._request = limited
    return client


def main():
    request = json.loads((root / "input.json").read_text(encoding="utf-8"))
    settings = Settings(root=root, logs=root / "logs")
    knowledge = KnowledgeLoader(settings.business / "knowledge")
    definition = load_workflow(settings.workflow)
    provider = request.get("provider", "gemini")
    client = bounded_client(provider, request.get("model"))
    artifact = dict(
        events=client.events,
        parsed_input=None,
        result=None,
        trace={},
        report=None,
        report_metadata={},
        isolation=guard,
        execution_mode=dict(
            llm=provider, data_backend="sqlite", data_origin="synthetic"
        ),
    )
    try:
        question = request["question"] + "\n" + request["period_context"]
        raw = IntentParser(knowledge, definition, client).parse(question)
        artifact["parsed_input"] = raw
        query = SQLiteQueryTool(
            SQLiteDatasetAdapter(
                knowledge, root / "data.db", mapping=root / "mapping.json"
            )
        )
        runtime = Runtime(knowledge, query, definition, settings, client)
        output = runtime.run(raw)
        artifact.update(result=output["result"], trace=runtime.trace)
        renderer = ReportGenerator(client)
        artifact["report"] = renderer.generate(output["result"], trace=runtime.trace)
        artifact["report_metadata"] = renderer.metadata
    except Exception as exc:
        # Never print/provider-store exception messages, which may contain secrets.
        artifact["error_type"] = type(exc).__name__
    finally:
        client.close()
        (root / "actual.json").write_text(
            json.dumps(artifact, ensure_ascii=False, indent=2, allow_nan=False),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
