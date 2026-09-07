from abc import ABC, abstractmethod
import re

class LLMClient(ABC):
    @abstractmethod
    def structured_generate(self, *, purpose: str, payload: dict, schema: dict) -> dict:
        """Provider boundary. Only intent, routing and report purposes are allowed."""

class MockLLMClient(LLMClient):
    """Offline fixture, not a real language model or production semantic router."""
    def structured_generate(self, *, purpose, payload, schema):
        if purpose=='routing':
            candidates=payload['allowed_candidates']
            preferred=payload['context'].get('preferred_dimension')
            return {'choice':preferred if preferred in candidates else candidates[0], 'rationale':'offline_mock_candidate_selection'}
        if purpose=='report':
            return {'selections':[{'claim_id':x['claim_id'],'variant':0} for x in payload['claims']]}
        if purpose=='intent':
            dates=re.findall(r'\d{4}-\d{2}-\d{2}',payload['question'])
            if len(dates)!=4 or not re.search(r'gmv',payload['question'],re.I):
                return {'error':'Provide GMV and four ISO dates: current start/end, baseline start/end.'}
            return {'metric_id':payload['allowed_metrics'][0],
                'current_period':{'start':dates[0],'end':dates[1]},'baseline_period':{'start':dates[2],'end':dates[3]},'filters':{}}
        raise ValueError('LLM purpose is not allowed')
