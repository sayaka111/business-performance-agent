"""Copied into a fresh opaque directory: no Case, Expected, recipes or graders."""

import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
sys.path.insert(0, str(root))
from isolation import install_guard

guard = install_guard(root)
from business_performance_agent.config.settings import Settings
from business_performance_agent.data_contract.sqlite_adapter import SQLiteDatasetAdapter
from business_performance_agent.tools.knowledge_loader import KnowledgeLoader
from business_performance_agent.tools.sqlite_query_tool import SQLiteQueryTool
from business_performance_agent.workflows.definition import load_workflow
from business_performance_agent.runtime.engine import Runtime
from business_performance_agent.llm.client import MockLLMClient
from business_performance_agent.llm.report_generator import ReportGenerator


def main():
    settings = Settings(root=root, logs=root / "logs")
    knowledge = KnowledgeLoader(settings.business / "knowledge")
    query = SQLiteQueryTool(
        SQLiteDatasetAdapter(knowledge, root / "data.db", mapping=root / "mapping.json")
    )
    client = MockLLMClient()
    runtime = Runtime(
        knowledge, query, load_workflow(settings.workflow), settings, client
    )
    output = runtime.run(json.loads((root / "input.json").read_text(encoding="utf-8")))
    report = ReportGenerator(client).generate(output["result"], trace=runtime.trace)
    runtime.save_trace()
    actual = {
        "result": output["result"],
        "trace": runtime.trace,
        "report": report,
        "execution_mode": {
            "llm": "mock",
            "data_backend": "sqlite",
            "data_origin": "synthetic",
        },
        "isolation": guard,
    }
    (root / "actual.json").write_text(
        json.dumps(actual, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
