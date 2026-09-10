"""Four bounded real-data scenarios. Live calls require explicit --live."""

import argparse
import json
import os
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from business_performance_agent.config.settings import Settings
from business_performance_agent.tools.knowledge_loader import KnowledgeLoader
from business_performance_agent.workflows.definition import load_workflow
from business_performance_agent.data_contract.sqlite_adapter import SQLiteDatasetAdapter
from business_performance_agent.tools.sqlite_query_tool import SQLiteQueryTool
from business_performance_agent.runtime.engine import Runtime
from business_performance_agent.llm.client import MockLLMClient
from business_performance_agent.llm.providers import create_client
from business_performance_agent.llm.intent_parser import IntentParser
from business_performance_agent.llm.report_generator import ReportGenerator


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    if args.live and not os.environ.get("DEEPSEEK_API_KEY"):
        raise SystemExit("DEEPSEEK_API_KEY_MISSING")
    output = ROOT / "examples/real_data/completejourney/runs" / str(uuid4())
    output.mkdir(parents=True)
    settings = Settings(logs=output / "traces")
    knowledge = KnowledgeLoader(settings.business / "knowledge")
    workflow = load_workflow(settings.workflow)
    adapter = SQLiteDatasetAdapter(
        knowledge,
        ROOT / "data/processed/completejourney/completejourney.sqlite",
        mapping=ROOT / "data/mappings/completejourney.json",
    )
    print("Adapter ready", flush=True)
    base = dict(
        metric_id="gross_gmv",
        current_period=dict(start="2017-12-01", end="2017-12-31"),
        baseline_period=dict(start="2017-01-01", end="2017-01-31"),
        filters={},
        context={},
    )
    date_text = "当前周期2017-12-01至2017-12-31，基期2017-01-01至2017-01-31。"
    scenarios = [
        ("overall", "分析总体GMV经营变化。", None),
        ("drivers", "GMV变化主要由订单还是客单价驱动？", None),
        ("category", "按品类分析GMV，哪个品类贡献最大？", "category"),
        ("unsupported_channel", "按渠道分析GMV。", "channel"),
    ]
    records = []
    for name, question, dim in scenarios:
        client = (
            create_client("deepseek", max_attempts=2) if args.live else MockLLMClient()
        )
        item = dict(
            scenario=name,
            user_query=question + date_text,
            execution_mode=dict(
                llm="deepseek" if args.live else "mock",
                data_origin="public_historical",
                dataset_id="completejourney_v1",
                production_database=False,
            ),
            capability_contract="data/contracts/completejourney.json",
        )
        try:
            raw = (
                IntentParser(knowledge, workflow, client).parse(question + date_text)
                if args.live
                else dict(base, context={"preferred_dimension": dim} if dim else {})
            )
            item["parsed_input"] = raw
            runtime = Runtime(
                knowledge, SQLiteQueryTool(adapter), workflow, settings, client
            )
            result = runtime.run(raw)
            item.update(result)
            renderer = ReportGenerator(client)
            item["report"] = renderer.generate(result["result"], trace=runtime.trace)
            item["report_metadata"] = renderer.metadata
            item["provider_events"] = getattr(client, "events", [])
            runtime.trace["execution_mode"] = item["execution_mode"]
            runtime.trace["rendered_report"] = item["report"]
            runtime.save_trace()
            facts = [e["payload"] for e in result["result"]["evidence"]]
            item["checks"] = dict(
                no_unsupported_core_claim=all(
                    c["evidence_level"] in ("direct", "derived")
                    for c in result["result"]["key_findings"]
                ),
                root_decomposition=any(
                    f.get("kind") == "contribution"
                    and f["fact"].get("relationship_id") == "gross_gmv_orders_aov"
                    for f in facts
                ),
                category_path=any(
                    p.get("dimension_id") == "category"
                    for p in result["result"]["diagnostic_path"]
                ),
                unsupported_stops=result["result"]["stop_reason"]
                == "data_quality_boundary"
                and any("channel" in x for x in result["result"]["limitations"]),
            )
        except Exception as exc:
            item.update(
                error_type=type(exc).__name__,
                provider_events=getattr(client, "events", []),
            )
        finally:
            if hasattr(client, "close"):
                client.close()
        (output / (name + ".json")).write_text(
            json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        if "report" in item:
            (output / (name + ".md")).write_text(item["report"], encoding="utf-8")
        records.append(item)
        print(name + ": " + str(item.get("checks", item.get("error_type"))), flush=True)
    passed = all(
        "result" in r
        and r["checks"]["no_unsupported_core_claim"]
        and (
            r["checks"]["unsupported_stops"]
            if r["scenario"] == "unsupported_channel"
            else r["checks"]["category_path"]
            if r["scenario"] == "category"
            else r["checks"]["root_decomposition"]
        )
        for r in records
    )
    (output / "summary.json").write_text(
        json.dumps(
            dict(
                run_id=output.name,
                mode="deepseek" if args.live else "mock",
                passed=passed,
                scenarios=[
                    dict(
                        scenario=r["scenario"],
                        checks=r.get("checks"),
                        error=r.get("error_type"),
                    )
                    for r in records
                ],
            ),
            indent=2,
        ),
        encoding="utf-8",
    )
    print("OUTPUT: " + str(output), flush=True)
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
