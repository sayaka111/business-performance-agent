import argparse
import json
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

def main():
    parser=argparse.ArgumentParser(description='Business Performance Agent MVP (mock data only)')
    inputs=parser.add_mutually_exclusive_group()
    inputs.add_argument('--input',type=Path,help='Structured workflow JSON file (UTF-8, optional BOM)')
    inputs.add_argument('--question',help='JSON text or natural language with a configured client')
    parser.add_argument('--mock-llm',action='store_true',help='Offline LLM interface fixture; no network/model call')
    parser.add_argument('--json',action='store_true',help='Print structured output')
    args=parser.parse_args()
    settings=Settings()
    knowledge=KnowledgeLoader(settings.business/'knowledge')
    definition=load_workflow(settings.workflow)
    client=MockLLMClient() if args.mock_llm else None
    if args.question:
        try: raw=IntentParser(knowledge,definition,client).parse(args.question)
        except (ValueError,KeyError,TypeError) as exc: parser.error(str(exc))
    else:
        try:
            raw=json.loads((args.input or settings.root/'examples'/'gmv_input.json').read_text(encoding='utf-8-sig'))
        except (OSError,UnicodeError,ValueError) as exc:
            parser.error(f'Cannot read workflow input: {exc}')
    query=MockQueryTool(MockDatasetAdapter(knowledge))
    output=Runtime(knowledge,query,definition,settings,client).run(raw)
    # Application metadata only: preserve the authoritative Runtime result verbatim.
    output['execution_mode']={
        'dataset':'mock',
        'dataset_id':query.adapter.mapping['dataset_id'],
        'llm':'mock' if client is not None else 'unconfigured',
        'real_business_data':False,
    }
    if not args.json:
        print(f"[MOCK DATA / 非真实经营数据] Dataset=mock; LLM={output['execution_mode']['llm']}")
    print(json.dumps(output,ensure_ascii=False,indent=2) if args.json else ReportGenerator(client).generate(output['result']))
    if not args.json: print(f"Run ID: {output['run_id']}\nTrace: {output['trace_path']}")
    return 1 if output['result']['workflow_status'] in ('blocked','failed') else 0

if __name__=='__main__': raise SystemExit(main())
