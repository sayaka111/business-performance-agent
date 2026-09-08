import json
import unittest
from business_performance_agent.llm.gemini_client import GeminiLLMClient
from business_performance_agent.models.schemas import BoundaryError


class GeminiProviderTests(unittest.TestCase):
    def run_router(self, replies):
        self.calls = []
        iterator = iter(replies)
        def transport(payload, schema):
            self.calls.append(payload)
            reply = next(iterator)
            if isinstance(reply, Exception): raise reply
            return reply
        self.client = GeminiLLMClient(transport=transport,sleep=lambda _:None)
        return self.client.structured_generate(purpose='routing',payload={'allowed_candidates':['a','b']},
            schema={'type':'object','required':['choice','rationale']})

    def test_valid_retry(self):
        value = self.run_router(['not json',json.dumps({'choice':'a','rationale':'available'})])
        self.assertEqual(value['choice'],'a')
        self.assertEqual(len(self.calls),2)

    def test_invalid_candidates_extra_fields_empty_missing(self):
        for reply in ['', '{}', '[]', '{"choice":"outside","rationale":"x"}', '{"choice":"a","rationale":"x","extra":1}',
                      '{"choice":"outside","choice":"a","rationale":"x"}']:
            with self.subTest(reply=reply), self.assertRaises(BoundaryError): self.run_router([reply,reply])
            self.assertEqual(len(self.calls),2)

    def test_provider_error_redacted(self):
        with self.assertRaises(BoundaryError) as error:
            self.run_router([RuntimeError('secret=not-for-log')])
        self.assertNotIn('not-for-log',str(error.exception)+json.dumps(self.client.events))

    def test_unknown_purpose_has_no_request(self):
        client = GeminiLLMClient(transport=lambda *_:self.fail('Network request forbidden'))
        with self.assertRaises(ValueError): client.structured_generate(purpose='sql',payload={},schema={})

    def test_http_retry_is_bounded(self):
        class ProviderFailure(Exception):
            code=503
        with self.assertRaises(BoundaryError): self.run_router([ProviderFailure(),ProviderFailure()])
        self.assertEqual(len(self.calls),2)
        ProviderFailure.code=400
        with self.assertRaises(BoundaryError): self.run_router([ProviderFailure()])
        self.assertEqual(len(self.calls),1)

    def test_report_cannot_add_duplicate_or_free_form_claim(self):
        for response in [{'selections':[{'claim_id':'c1','variant':0},{'claim_id':'c1','variant':0}]},
                         {'selections':[{'claim_id':'invented','variant':0}]},
                         {'selections':[{'claim_id':'c1','variant':True}]},
                         {'selections':[], 'report':'unsupported cause'}]:
            client=GeminiLLMClient(transport=lambda *_:json.dumps(response),sleep=lambda _:None)
            with self.assertRaises(BoundaryError):
                client.structured_generate(purpose='report',payload={'claims':[{'claim_id':'c1','variants':['verified']} ]},
                    schema={'type':'object','required':['selections']})


if __name__ == '__main__': unittest.main()
