class ReportGenerator:
    def __init__(self, client=None):
        self.client = client
        self.metadata = {}

    def generate(self, result, *, trace=None):
        """LLM may arrange validated phrases; free-form factual additions fail closed."""
        self.metadata = {
            "report_renderer": "deterministic_fallback",
            "provider_error_code": None,
            "retry_count": 0,
        }
        event_start = len(getattr(self.client, "events", []))
        findings = result["key_findings"]
        lines = [x["claim"] for x in findings]
        if self.client and findings:
            payload = {
                "claims": [
                    {"claim_id": x["claim_id"], "variants": [x["claim"]]}
                    for x in findings
                ]
            }
            try:
                response = self.client.structured_generate(
                    purpose="report",
                    payload=payload,
                    schema={
                        "type": "object",
                        "required": ["selections"],
                        "additionalProperties": False,
                    },
                )
                selections = response["selections"]
                by_id = {x["claim_id"]: x["claim"] for x in findings}
                if set(response) != {"selections"} or len(selections) != len(by_id):
                    raise ValueError("report additions/omissions")
                if {x["claim_id"] for x in selections} != set(by_id):
                    raise ValueError("report claims changed")
                if any(
                    set(x) != {"claim_id", "variant"}
                    or type(x["variant"]) is not int
                    or x["variant"] != 0
                    for x in selections
                ):
                    raise ValueError("unapproved wording")
                lines = [by_id[x["claim_id"]] for x in selections]
                if getattr(self.client, "provider_name", None) in (
                    "gemini",
                    "deepseek",
                ):
                    self.metadata["report_renderer"] = self.client.provider_name
            except Exception as exc:
                lines = [x["claim"] for x in findings]
                code = getattr(exc, "code", None)
                if type(code) is int:
                    self.metadata["provider_error_code"] = code
            finally:
                events = [
                    e
                    for e in getattr(self.client, "events", [])[event_start:]
                    if e.get("purpose") == "report"
                ]
                self.metadata["retry_count"] = max(
                    (e.get("attempt", 1) - 1 for e in events), default=0
                )
                codes = [
                    e["http_status"]
                    for e in events
                    if type(e.get("http_status")) is int
                ]
                if codes:
                    self.metadata["provider_error_code"] = codes[-1]
        if trace is not None:
            trace.update(self.metadata)
        return self.render_markdown(result, lines)

    @staticmethod
    def render_markdown(result, lines):
        """Only formatting; no recomputation, inferred causes or suggested actions."""
        blocks = [
            "# GMV 诊断报告",
            f"- GMV 诊断状态：{result['workflow_status']}\n- 停止原因：{result['stop_reason']}",
        ]
        for title, items in [
            ("分析发现", lines),
            ("警告", result["warnings"]),
            ("限制", result["limitations"]),
        ]:
            if items:
                blocks.extend(["## " + title, "\n".join("- " + item for item in items)])
        return "\n\n".join(blocks)
