"""Standalone report-only replay; never loads a workflow, database or API key file."""
import argparse
import hashlib
import json
from pathlib import Path
from ..llm.gemini_client import GeminiLLMClient, response_schema


class DiagnosticClient(GeminiLLMClient):
    def __init__(self, case, **kwargs):
        super().__init__(max_attempts=1, **kwargs)
        self.case = case

    def generation_config(self, schema):
        config = super().generation_config(schema)
        if self.case == 'no_variant_enum':
            config['response_json_schema']['properties']['selections']['items']['properties']['variant'].pop('enum', None)
        elif self.case == 'no_schema':
            schema = config.pop('response_json_schema')
            config['system_instruction'] += ' Required output schema: ' + json.dumps(schema)
        elif self.case == 'minimal':
            config = {'response_mime_type': 'application/json',
                      'system_instruction': 'Return only a JSON object with selections, an array containing every supplied claim_id exactly once and integer variant 0. Do not write report prose.'}
        return config


def metadata(client, fixture):
    schema = response_schema(fixture['purpose'], fixture['payload'], fixture['schema'])
    config = client.generation_config(schema)
    contents = json.dumps({'purpose': fixture['purpose'], 'payload': fixture['payload']}, ensure_ascii=False)
    text = contents + config.get('system_instruction','') + json.dumps(config.get('response_json_schema',{}),ensure_ascii=False)
    signature = json.dumps({'model':client.model, 'contents':contents, 'config':config},ensure_ascii=False,sort_keys=True)
    return {'model':client.model, 'request_type':fixture['purpose'], 'api_method':'models.generate_content',
            'streaming':False, 'prompt_character_count':len(contents),
            'approximate_input_tokens':sum(1 if ord(c)>127 else .25 for c in text),
            'token_count_method':'heuristic, not provider tokenization',
            'config':config, 'request_sha256':hashlib.sha256(signature.encode()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture',type=Path,default=Path('tests/fixtures/gemini_report_failure.json'))
    parser.add_argument('--case',choices=['baseline','no_variant_enum','no_schema','minimal'],default='baseline')
    parser.add_argument('--inspect-only',action='store_true')
    parser.add_argument('--log',type=Path,default=Path('logs/report-diagnostics.json'))
    args = parser.parse_args()
    fixture = json.loads(args.fixture.read_text(encoding='utf-8'))
    if fixture.get('fixture_source') != 'synthetic_sqlite_fixture' or fixture.get('purpose') != 'report':
        parser.error('Only the sanitized synthetic report fixture is accepted')
    client = DiagnosticClient(args.case,model=fixture['model'])
    info = metadata(client,fixture)
    print(json.dumps(info,ensure_ascii=False,indent=2),flush=True)
    if args.inspect_only:
        return 0
    previous = json.loads(args.log.read_text(encoding='utf-8')) if args.log.exists() else []
    failures = sum(x['request_sha256']==info['request_sha256'] and
                   any(e.get('http_status')==503 for e in x.get('events',[])) for x in previous)
    if failures >= 2:
        parser.error('This identical request already returned HTTP 503 twice; change diagnostic strategy')
    record = dict(info,case=args.case,status='FAIL')
    try:
        value = client.structured_generate(purpose='report',payload=fixture['payload'],schema=fixture['schema'])
        record.update(status='PASS',validated_selections=value['selections'])
    except Exception as exc:
        record['error_type']=type(exc).__name__
    finally:
        record['events']=client.events
        previous.append(record)
        args.log.parent.mkdir(parents=True,exist_ok=True)
        args.log.write_text(json.dumps(previous,ensure_ascii=False,indent=2),encoding='utf-8')
        client.close()
    print(json.dumps({k:record[k] for k in ('case','status','events')},ensure_ascii=False),flush=True)
    return 0 if record['status']=='PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
