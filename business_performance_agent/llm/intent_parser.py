import json
from dataclasses import asdict
from ..models.schemas import WorkflowInput

class IntentParser:
    def __init__(self, knowledge, definition, client=None):
        self.knowledge,self.definition,self.client=knowledge,definition,client

    def parse(self, question):
        try: raw=json.loads(question)
        except json.JSONDecodeError:
            if self.client is None: raise ValueError('Natural language requires an LLMClient; structured JSON is supported offline.')
            raw=self.client.structured_generate(purpose='intent',payload={'question':question,
                'allowed_metrics':self.definition['state_schema']['state']['target_metric']['allowed'],
                'allowed_dimensions':[d['id'] for d in self.knowledge.all('dimensions')]},
                schema={'type':'object','required':['metric_id','current_period','baseline_period','filters']})
        return asdict(WorkflowInput.parse(raw,self.knowledge,self.definition))
