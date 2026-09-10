import argparse
import json
import sqlite3
from uuid import uuid4
from pathlib import Path
from ..config.settings import Settings
from ..tools.knowledge_loader import KnowledgeLoader
from ..tools.query_tool import MockQueryTool
from ..data_contract.mock_adapter import MockDatasetAdapter
from ..workflows.definition import load_workflow
from ..runtime.engine import Runtime
from ..llm.client import MockLLMClient
from ..llm.intent_parser import IntentParser
from ..llm.report_generator import ReportGenerator
from ..models.schemas import BoundaryError


def main():
    parser = argparse.ArgumentParser(description="Business Performance Agent MVP")
    inputs = parser.add_mutually_exclusive_group()
    inputs.add_argument(
        "--input", type=Path, help="Structured workflow JSON file (UTF-8, optional BOM)"
    )
    inputs.add_argument(
        "--question", help="JSON text or natural language with a configured client"
    )
    providers = parser.add_mutually_exclusive_group()
    providers.add_argument(
        "--mock-llm",
        action="store_true",
        help="Offline LLM interface fixture; no network/model call",
    )
    providers.add_argument(
        "--gemini", action="store_true", help="Gemini via GEMINI_API_KEY"
    )
    providers.add_argument(
        "--provider", choices=["gemini", "deepseek"], help="Select a real LLM provider"
    )
    parser.add_argument("--model", help="Provider model override")
    parser.add_argument(
        "--database", type=Path, help="Read-only SQLite database; requires --mapping"
    )
    parser.add_argument(
        "--mapping", type=Path, help="Explicit semantic SQLite mapping JSON"
    )
    parser.add_argument("--json", action="store_true", help="Print structured output")
    args = parser.parse_args()
    provider_name = args.provider or ("gemini" if args.gemini else None)
    settings = Settings()
    knowledge = KnowledgeLoader(settings.business / "knowledge")
    definition = load_workflow(settings.workflow)
    if args.model and not provider_name:
        parser.error("--model requires --gemini or --provider")
    if args.database and not (args.input or args.question):
        parser.error("SQLite requires explicit --input or --question periods")
    if bool(args.database) != bool(args.mapping):
        parser.error("--database and --mapping must be provided together")
    client = MockLLMClient() if args.mock_llm else None
    if provider_name:
        from ..llm.providers import create_client

        client = create_client(provider_name, args.model)
    if args.question:
        try:
            raw = IntentParser(knowledge, definition, client).parse(args.question)
        except (ValueError, KeyError, TypeError, BoundaryError) as exc:
            if provider_name:
                settings.logs.mkdir(parents=True, exist_ok=True)
                run_id = str(uuid4())
                path = settings.logs / (run_id + ".json")
                path.write_text(
                    json.dumps(
                        {
                            "run_id": run_id,
                            "phase": "intent",
                            "status": "blocked",
                            "input": {"question": args.question},
                            "llm_events": client.events,
                            "final_structured_result": None,
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
                client.close()
                parser.error(f"{exc}; intent trace: {path}")
            parser.error(str(exc))
    else:
        try:
            raw = json.loads(
                (args.input or settings.root / "examples" / "gmv_input.json").read_text(
                    encoding="utf-8-sig"
                )
            )
        except (OSError, UnicodeError, ValueError) as exc:
            parser.error(f"Cannot read workflow input: {exc}")
    if args.database:
        from ..data_contract.sqlite_adapter import SQLiteDatasetAdapter
        from ..tools.sqlite_query_tool import SQLiteQueryTool

        try:
            query = SQLiteQueryTool(
                SQLiteDatasetAdapter(knowledge, args.database, mapping=args.mapping)
            )
        except (
            OSError,
            ValueError,
            KeyError,
            TypeError,
            sqlite3.Error,
            BoundaryError,
        ) as exc:
            parser.error(str(exc))
    else:
        query = MockQueryTool(MockDatasetAdapter(knowledge))
    runtime = Runtime(knowledge, query, definition, settings, client)
    output = runtime.run(raw)
    # Application metadata only: preserve the authoritative Runtime result verbatim.
    output["execution_mode"] = {
        "dataset": "SQLite" if args.database else "mock",
        "dataset_id": query.adapter.mapping["dataset_id"],
        "llm": provider_name
        if provider_name
        else "mock"
        if client is not None
        else "unconfigured",
        "data_backend": "sqlite" if args.database else "memory",
        "data_origin": query.adapter.mapping.get("data_origin", "synthetic"),
        "production_database": False,
    }
    if args.database:
        output["execution_mode"]["production_database"] = False
    report = None
    if not args.json or provider_name:
        renderer = ReportGenerator(client)
        report = renderer.generate(output["result"], trace=runtime.trace)
    if provider_name:
        output["report"] = report
        output["execution_mode"]["llm_requests_succeeded"] = sum(
            e["status"] == "success" for e in client.events
        )
        output["execution_mode"]["report_rendering"] = renderer.metadata[
            "report_renderer"
        ]
        runtime.trace["llm_events"] = client.events
        client.close()
    runtime.trace["execution_mode"] = output["execution_mode"]
    if report is not None:
        runtime.trace["rendered_report"] = report
    runtime.save_trace()
    if not args.json:
        label = (
            "SQLite / " + output["execution_mode"]["data_origin"] + " / 非生产数据库"
            if args.database
            else "MOCK DATA / 非真实经营数据"
        )
        print(
            f"[{label}] Dataset={output['execution_mode']['dataset']}; LLM={output['execution_mode']['llm']}"
        )
    print(json.dumps(output, ensure_ascii=False, indent=2) if args.json else report)
    if not args.json:
        print(f"Run ID: {output['run_id']}\nTrace: {output['trace_path']}")
    return 1 if output["result"]["workflow_status"] in ("blocked", "failed") else 0


if __name__ == "__main__":
    raise SystemExit(main())
