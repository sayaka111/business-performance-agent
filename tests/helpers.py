import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from business_performance_agent.config.settings import Settings
from business_performance_agent.tools.knowledge_loader import KnowledgeLoader
from business_performance_agent.tools.query_tool import MockQueryTool
from business_performance_agent.data_contract.mock_adapter import MockDatasetAdapter
from business_performance_agent.workflows.definition import load_workflow
from business_performance_agent.runtime.engine import Runtime
from business_performance_agent.llm.result_builder import validate_result


class Harness(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.settings = Settings(logs=Path(self.temp.name))
        self.knowledge = KnowledgeLoader(self.settings.business / "knowledge")
        self.definition = load_workflow(self.settings.workflow)
        self.adapter = MockDatasetAdapter(self.knowledge)
        self.query = MockQueryTool(self.adapter)
        self.raw = json.loads(
            (self.settings.root / "examples/gmv_input.json").read_text()
        )

    def run_agent(self, client=None, raw=None):
        self.engine = Runtime(
            self.knowledge, self.query, self.definition, self.settings, client
        )
        output = self.engine.run(raw if raw is not None else self.raw)
        validate_result(output["result"], self.definition["output_schema"])
        return output["result"]

    def comparison_args(self, metric="orders"):
        return dict(
            metric_id=metric,
            current_period=self.raw["current_period"],
            baseline_period=self.raw["baseline_period"],
            filters={},
        )
