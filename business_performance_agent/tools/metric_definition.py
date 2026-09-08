"""Read-only semantic tool; definitions remain in Knowledge JSON."""

RETURN_SCHEMA = {"type": "object", "required": ["status", "metric"],
                 "properties": {"status": {"enum": ["success"]}, "metric": {"type": "object"}}}

def declaration(knowledge):
    return {
        "name": "get_metric_definition",
        "description": "Read the authoritative definition of a business metric. Use for metric meaning, formula or scope questions; does not query business data.",
        "parameters": {"type": "object", "properties": {
            "metric_id": {"type": "string", "enum": [m["id"] for m in knowledge.all("metrics")]}},
            "required": ["metric_id"]},
    }

def execute(knowledge, arguments):
    if not isinstance(arguments, dict) or set(arguments) != {"metric_id"} or not isinstance(arguments["metric_id"], str):
        raise ValueError("Expected exactly one string parameter: metric_id")
    metric = knowledge.get_metric(arguments["metric_id"])
    return {"status": "success", "metric": metric}
