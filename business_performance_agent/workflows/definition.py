import hashlib
import json


def load_workflow(directory):
    definition = {}
    fingerprints = {}
    for name in (
        "workflow.md",
        "state_schema.json",
        "routing_rules.json",
        "policy.json",
        "output_schema.json",
    ):
        content = (directory / name).read_bytes()
        fingerprints[str(directory / name)] = hashlib.sha256(content).hexdigest()
        definition[name.split(".")[0]] = (
            content.decode("utf-8") if name.endswith(".md") else json.loads(content)
        )
    definition["fingerprints"] = fingerprints
    definition["workflow_id"] = definition["policy"]["workflow_id"]
    definition["workflow_version"] = definition["output_schema"]["output"][
        "workflow_version"
    ]
    if any(
        definition[k]["workflow_id"] != definition["workflow_id"]
        for k in ("state_schema", "routing_rules", "output_schema")
    ):
        raise ValueError("specification workflow identity conflict")
    return definition
