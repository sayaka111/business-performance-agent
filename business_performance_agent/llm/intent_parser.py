import json
from dataclasses import asdict
from ..models.schemas import WorkflowInput
from .structured_client import response_schema, validate


INTENT_RULES = """Preserve analysis scope separately from filters.
按渠道看 / 哪个渠道拖累最大 -> context.preferred_dimension=channel, filters={}.
按品类看 -> context.preferred_dimension=category, filters={}.
哪个地区的问题 / 哪个地区拖累最大 -> context.preferred_dimension=region, filters={}.
Use only allowed dimensions. If no dimension is requested, omit the preference or use null.
Only an explicit restriction to a concrete segment may create a filter.
Never create all, 全部, 所有, 全渠道, 全品类, 全地区 or * filter values.
Use verified_filter_values only; labels map explicitly to semantic values.
Never guess physical values or convert Paid Search to paid_search yourself.
If a requested restriction cannot be verified, preserve its label in filters
so local validation can stop for clarification; never silently broaden scope.
"""


class IntentParser:
    def __init__(self, knowledge, definition, client=None, *, filter_values=None):
        self.knowledge, self.definition, self.client = knowledge, definition, client
        # Caller-supplied, verified semantic label -> value mapping. Never LLM-owned.
        self.filter_values = {
            d["id"]: {v: v for v in d.get("values", [])}
            for d in knowledge.all("dimensions")
        }
        for dimension, aliases in (filter_values or {}).items():
            definition = knowledge.get_dimension(dimension)
            if not isinstance(aliases, dict):
                raise ValueError("Verified filter mappings must be objects")
            for label, value in aliases.items():
                if not isinstance(label, str) or not isinstance(value, str):
                    raise ValueError(
                        "Verified filter labels and values must be strings"
                    )
                self._check_filter(label)
                self._check_filter(value)
                if definition.get("values") and value not in definition["values"]:
                    raise ValueError("Filter mapping outside Knowledge values")
                self.filter_values[dimension][label] = value

    @staticmethod
    def _check_filter(value):
        if not isinstance(value, str) or value.strip().casefold() in {
            "",
            "all",
            "*",
            "全部",
            "所有",
            "全渠道",
            "全品类",
            "全地区",
        }:
            raise ValueError("A filter requires a concrete verified segment, not all")

    def parse(self, question):
        try:
            raw = json.loads(question)
        except json.JSONDecodeError:
            if self.client is None:
                raise ValueError(
                    "Natural language requires an LLMClient; structured JSON is supported offline."
                )
            payload = {
                "question": question,
                "allowed_metrics": self.definition["state_schema"]["state"][
                    "target_metric"
                ]["allowed"],
                "allowed_dimensions": [
                    d["id"] for d in self.knowledge.all("dimensions")
                ],
                "intent_rules": INTENT_RULES,
                "verified_filter_values": self.filter_values,
            }
            schema = {
                "type": "object",
                "required": [
                    "metric_id",
                    "current_period",
                    "baseline_period",
                    "filters",
                ],
            }
            raw = self.client.structured_generate(
                purpose="intent",
                payload=payload,
                schema=schema,
            )
            validate(raw, response_schema("intent", payload, schema))
            raw = dict(raw, filters=dict(raw["filters"]))
            for dimension, value in raw["filters"].items():
                self._check_filter(value)
                verified = self.filter_values.get(dimension, {})
                if value in verified:
                    raw["filters"][dimension] = verified[value]
                elif value not in verified.values():
                    raise ValueError(
                        "Requested filter cannot be verified; provide an explicit semantic value mapping before analysis"
                    )
        for value in raw.get("filters", {}).values():
            self._check_filter(value)
        return asdict(WorkflowInput.parse(raw, self.knowledge, self.definition))
