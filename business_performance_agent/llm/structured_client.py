"""Provider-independent structured response contract; no business planning."""

import copy
import json
import time

from .client import LLMClient
from ..models.schemas import BoundaryError

TRANSIENT_PROVIDER_CODES = frozenset((429, 500, 502, 503, 504))


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Duplicate JSON key")
        value[key] = item
    return value


def reject_constant(value):
    raise ValueError("Nonfinite JSON")


def error_category(exc):
    """Classify provider text locally; never persist or print the provider message."""
    if getattr(exc, "failure_kind", None) in ("timeout", "network"):
        return "deadline" if exc.failure_kind == "timeout" else "connection"
    if getattr(exc, "code", None) == 429:
        return "rate_or_quota_limit"
    message = str(getattr(exc, "message", "")).lower()
    for category, terms in (
        ("capacity", ("high demand", "overloaded", "capacity", "resource exhausted")),
        ("deadline", ("deadline", "timed out", "timeout")),
        ("request_validation", ("schema", "invalid argument", "unsupported")),
    ):
        if any(term in message for term in terms):
            return category
    return "unspecified"


def validate(value, schema):
    kinds = {
        "object": dict,
        "array": list,
        "string": str,
        "integer": int,
        "boolean": bool,
        "null": type(None),
    }
    kind = schema.get("type")
    if isinstance(kind, list):
        for option in kind:
            try:
                validate(value, dict(schema, type=option))
                return
            except ValueError:
                pass
        raise ValueError("Invalid structured type")
    if kind and (
        not isinstance(value, kinds[kind])
        or kind == "integer"
        and isinstance(value, bool)
    ):
        raise ValueError("Invalid structured type")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError("Value outside allowed candidates")
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        if set(schema.get("required", [])) - value.keys():
            raise ValueError("Missing fields")
        if (
            schema.get("additionalProperties") is False
            and value.keys() - properties.keys()
        ):
            raise ValueError("Unexpected fields")
        for key, item in value.items():
            if key in properties:
                validate(item, properties[key])
            elif isinstance(schema.get("additionalProperties"), dict):
                validate(item, schema["additionalProperties"])
    if isinstance(value, list):
        for item in value:
            validate(item, schema.get("items", {}))


def response_schema(purpose, payload, schema):
    result = copy.deepcopy(schema)
    result["additionalProperties"] = False
    if purpose == "routing":
        result["properties"] = {
            "choice": {
                "type": "string",
                "enum": payload["allowed_candidates"] + ["no_valid_choice"],
            },
            "rationale": {"type": "string"},
        }
    elif purpose == "intent":
        period = {
            "type": "object",
            "required": ["start", "end"],
            "additionalProperties": False,
            "properties": {"start": {"type": "string"}, "end": {"type": "string"}},
        }
        result["properties"] = {
            "metric_id": {"type": "string", "enum": payload["allowed_metrics"]},
            "current_period": period,
            "baseline_period": period,
            "context": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "preferred_dimension": {
                        "type": ["string", "null"],
                        "enum": payload["allowed_dimensions"] + [None],
                        "description": "Dimension to analyze/group by, not a segment filter.",
                    }
                },
            },
            "filters": {
                "type": "object",
                "description": "Only explicit restrictions to verified concrete segments. Never use all or a grouping dimension as a filter value.",
                "properties": {
                    d: {"type": "string"} for d in payload["allowed_dimensions"]
                },
                "additionalProperties": False,
            },
        }
    elif purpose == "report":
        result["properties"] = {
            "selections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["claim_id", "variant"],
                    "additionalProperties": False,
                    "properties": {
                        "claim_id": {
                            "type": "string",
                            "enum": [c["claim_id"] for c in payload["claims"]],
                        },
                        "variant": {"type": "integer", "enum": [0]},
                    },
                },
            }
        }
    else:
        raise ValueError("LLM purpose not allowed")
    return result


class StructuredLLMClient(LLMClient):
    """Shared JSON schemas, local validation, bounded retry and safe events."""

    def __init__(self, *, transport=None, sleep=time.sleep, max_attempts=2):
        self.transport, self.sleep = transport, sleep
        self.events = []
        if type(max_attempts) is not int or max_attempts not in (1, 2):
            raise ValueError("Provider attempts must be 1 or 2")
        self.max_attempts = max_attempts

    def _request(self, payload, schema):
        raise NotImplementedError

    def close(self):
        pass

    def structured_generate(self, *, purpose, payload, schema):
        expected = response_schema(purpose, payload, schema)
        request = {"purpose": purpose, "payload": payload}
        for attempt in range(self.max_attempts):
            try:
                raw = self._request(request, expected)
                value = json.loads(
                    raw, parse_constant=reject_constant, object_pairs_hook=unique_object
                )
                validate(value, expected)
                if purpose == "report":
                    wanted = {c["claim_id"] for c in payload["claims"]}
                    chosen = [x["claim_id"] for x in value["selections"]]
                    if len(chosen) != len(wanted) or set(chosen) != wanted:
                        raise ValueError("Report omitted or duplicated claims")
                self.events.append(
                    {
                        "purpose": purpose,
                        "attempt": attempt + 1,
                        "status": "success",
                        "model": self.model,
                        "provider": self.provider_name,
                    }
                )
                return value
            except Exception as exc:
                code = getattr(exc, "code", None)
                retryable = (
                    isinstance(exc, (ValueError, TypeError))
                    or getattr(exc, "transient_provider_failure", False)
                    or type(exc).__name__
                    in ("ConnectTimeout", "ReadTimeout", "ConnectError", "TimeoutError")
                    or type(code) is int
                    and code in TRANSIENT_PROVIDER_CODES
                )
                self.events.append(
                    {
                        "purpose": purpose,
                        "attempt": attempt + 1,
                        "status": "failed",
                        "error_type": type(exc).__name__,
                        "provider": self.provider_name,
                        "failure_kind": getattr(exc, "failure_kind", None),
                        "http_status": code if type(code) is int else None,
                        "error_category": error_category(exc),
                        "transient_provider_failure": bool(
                            getattr(exc, "transient_provider_failure", False)
                            or type(code) is int
                            and code in TRANSIENT_PROVIDER_CODES
                        ),
                    }
                )
                if not retryable or attempt + 1 >= self.max_attempts:
                    detail = f"{self.provider_name} {type(exc).__name__}; HTTP {code if type(code) is int else 'unavailable'}; structured request failed."
                    raise BoundaryError("evidence_boundary_reached", detail) from None
                if type(code) is int:
                    self.sleep(2)
        raise AssertionError("Unreachable")
