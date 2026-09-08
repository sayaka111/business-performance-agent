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
    parser=argparse.ArgumentParser(description='Business Performance Agent MVP')
    inputs=parser.add_mutually_exclusive_group()
    inputs.add_argument('--input',type=Path,help='Structured workflow JSON file (UTF-8, optional BOM)')
    inputs.add_argument('--question',help='JSON text or natural language with a configured client')
    providers=parser.add_mutually_exclusive_group()
    providers.add_argument('--mock-llm',action='store_true',help='Offline LLM interface fixture; no network/model call')
    providers.add_argument('--gemini',action='store_true',help='Gemini via GEMINI_API_KEY')
    parser.add_argument('--model',help='Gemini model override; default from GEMINI_MODEL')
    parser.add_argument('--database',type=Path,help='Read-only Olist raw SQLite database')
    parser.add_argument('--json',action='store_true',help='Print structured output')
    args=parser.parse_args()
    settings=Settings()
    knowledge=KnowledgeLoader(settings.business/'knowledge')
    definition=load_workflow(settings.workflow)
    if args.model and not args.gemini: parser.error('--model requires --gemini')
    if args.database and not (args.input or args.question): parser.error('SQLite requires explicit --input or --question periods')
    client=MockLLMClient() if args.mock_llm else None
    if args.gemini:
        from ..llm.gemini_client import GeminiLLMClient
        client=GeminiLLMClient(args.model)
    if args.question:
        try: raw=IntentParser(knowledge,definition,client).parse(args.question)
        except (ValueError,KeyError,TypeError,BoundaryError) as exc:
            if args.gemini:
                settings.logs.mkdir(parents=True,exist_ok=True)
                run_id=str(uuid4())
                path=settings.logs/(run_id+'.json')
                path.write_text(json.dumps({'run_id':run_id,'phase':'intent','status':'blocked',
                    'input':{'question':args.question},'llm_events':client.events,
                    'final_structured_result':None},ensure_ascii=False,indent=2),encoding='utf-8')
                client.close()
                parser.error(f'{exc}; intent trace: {path}')
            parser.error(str(exc))
    else:
        try:
            raw=json.loads((args.input or settings.root/'examples'/'gmv_input.json').read_text(encoding='utf-8-sig'))
        except (OSError,UnicodeError,ValueError) as exc:
            parser.error(f'Cannot read workflow input: {exc}')
    if args.database:
        from ..data_contract.sqlite_adapter import SQLiteDatasetAdapter
        from ..tools.sqlite_query_tool import SQLiteQueryTool
        try: query=SQLiteQueryTool(SQLiteDatasetAdapter(knowledge,args.database))
        except (OSError,sqlite3.Error,BoundaryError) as exc: parser.error(str(exc))
    else:
        query=MockQueryTool(MockDatasetAdapter(knowledge))
    runtime=Runtime(knowledge,query,definition,settings,client)
    output=runtime.run(raw)
    # Application metadata only: preserve the authoritative Runtime result verbatim.
    output['execution_mode']={
        'dataset':'SQLite' if args.database else 'mock',
        'dataset_id':query.adapter.mapping['dataset_id'],
        'llm':'gemini' if args.gemini else 'mock' if client is not None else 'unconfigured',
        'real_business_data':bool(args.database),
    }
    if args.database: output['execution_mode']['production_database']=False
    report=None
    if not args.json or args.gemini:
        renderer=ReportGenerator(client)
        report=renderer.generate(output['result'],trace=runtime.trace)
    if args.gemini:
        output['report']=report
        output['execution_mode']['llm_requests_succeeded']=sum(e['status']=='success' for e in client.events)
        output['execution_mode']['report_rendering']=renderer.metadata['report_renderer']
        runtime.trace['llm_events']=client.events
        client.close()
    runtime.trace['execution_mode']=output['execution_mode']
    if report is not None: runtime.trace['rendered_report']=report
    runtime.save_trace()
    if not args.json:
        label='SQLite / 历史公开数据，非生产数据库' if args.database else 'MOCK DATA / 非真实经营数据'
        print(f"[{label}] Dataset={output['execution_mode']['dataset']}; LLM={output['execution_mode']['llm']}")
    print(json.dumps(output,ensure_ascii=False,indent=2) if args.json else report)
    if not args.json: print(f"Run ID: {output['run_id']}\nTrace: {output['trace_path']}")
    return 1 if output['result']['workflow_status'] in ('blocked','failed') else 0

if __name__=='__main__': raise SystemExit(main())
