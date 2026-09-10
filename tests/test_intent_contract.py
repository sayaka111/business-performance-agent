import json
from business_performance_agent.models.schemas import BoundaryError

from tests.helpers import Harness
from business_performance_agent.llm.intent_parser import IntentParser
from business_performance_agent.llm.gemini_client import GeminiLLMClient
from business_performance_agent.llm.deepseek_client import DeepSeekLLMClient
from business_performance_agent.llm.structured_client import response_schema, validate


class IntentContractTests(Harness):
    def parser(self, reply, provider=GeminiLLMClient, **kwargs):
        def transport(request, schema):
            self.request, self.schema = request, schema
            return json.dumps(reply)

        client = provider(transport=transport, max_attempts=1)
        self.addCleanup(client.close)
        return IntentParser(self.knowledge, self.definition, client, **kwargs)

    def test_grouping_context_reaches_runtime_for_both_providers(self):
        for provider in (GeminiLLMClient, DeepSeekLLMClient):
            for question, dimension in (
                ("按渠道看GMV下降", "channel"),
                ("按品类看GMV", "category"),
                ("哪个地区拖累最大", "region"),
            ):
                with self.subTest(provider=provider.__name__, dimension=dimension):
                    reply = dict(
                        self.raw, filters={}, context={"preferred_dimension": dimension}
                    )
                    parsed = self.parser(reply, provider).parse(question)
                    self.assertEqual(parsed["context"], reply["context"])
                    self.assertEqual(parsed["filters"], {})
                    self.assertIn(
                        "preferred_dimension", self.request["payload"]["intent_rules"]
                    )
                    self.run_agent(raw=parsed)
                    self.assertEqual(
                        self.engine.trace["input"]["context"], reply["context"]
                    )

    def test_verified_channel_label_is_normalized(self):
        reply = dict(self.raw, filters={"channel": "Paid Search"})
        parsed = self.parser(
            reply, filter_values={"channel": {"Paid Search": "paid_search"}}
        ).parse("只看 Paid Search 渠道的GMV")
        self.assertEqual(parsed["filters"], {"channel": "paid_search"})

    def test_unverified_label_and_guessed_canonical_value_stop(self):
        for value in ("Paid Search", "paid_search", "made_up"):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(ValueError, "cannot be verified"),
            ):
                self.parser(dict(self.raw, filters={"channel": value})).parse(
                    "只看 Paid Search"
                )

    def test_all_never_reaches_workflow(self):
        for dim in ("channel", "category", "region"):
            for value in ("all", " ALL ", "全部", "*"):
                reply = dict(self.raw, filters={dim: value})
                with self.subTest(dim=dim, value=value):
                    with self.assertRaises(ValueError):
                        self.parser(reply).parse("按维度分析GMV")
                    with self.assertRaises(ValueError):
                        self.parser(reply).parse(json.dumps(reply))

    def test_schema_allows_only_knowledge_dimensions_or_null(self):
        payload = {
            "allowed_metrics": ["gross_gmv"],
            "allowed_dimensions": [d["id"] for d in self.knowledge.all("dimensions")],
        }
        schema = response_schema("intent", payload, {"type": "object"})
        for dimension in payload["allowed_dimensions"] + [None]:
            validate(dict(self.raw, context={"preferred_dimension": dimension}), schema)
        for context in (
            {"preferred_dimension": "invented"},
            {"preferred_dimension": 1},
            {"extra": "x"},
            {"traffic_view": True},
        ):
            with self.subTest(context=context), self.assertRaises(ValueError):
                validate(dict(self.raw, context=context), schema)
        self.assertFalse(schema["additionalProperties"])
        self.assertFalse(schema["properties"]["context"]["additionalProperties"])

    def test_null_context_preference_is_accepted_by_parser(self):
        reply = dict(self.raw, context={"preferred_dimension": None})
        self.assertIsNone(
            self.parser(reply).parse("分析GMV")["context"]["preferred_dimension"]
        )

    def test_explicit_structured_input_remains_supported(self):
        reply = dict(
            self.raw,
            filters={"channel": "paid_search"},
            context={"preferred_dimension": "region"},
        )
        self.assertEqual(self.parser(reply).parse(json.dumps(reply)), reply)

    def test_mapping_cannot_override_knowledge_or_add_dimension(self):
        for values in (
            {"invented": {"a": "b"}},
            {"customer_type": {"a": "invented"}},
            {"channel": {"all": "paid_search"}},
        ):
            with (
                self.subTest(values=values),
                self.assertRaises((ValueError, KeyError, BoundaryError)),
            ):
                self.parser(self.raw, filter_values=values)

    def test_knowledge_enum_filter_needs_no_external_mapping(self):
        reply = dict(self.raw, filters={"customer_type": "new"})
        self.assertEqual(
            self.parser(reply).parse("只看 new 客户")["filters"],
            {"customer_type": "new"},
        )
