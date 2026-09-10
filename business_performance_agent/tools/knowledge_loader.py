import copy
import hashlib
import json
from ..models.schemas import BoundaryError


class KnowledgeLoader:
    def __init__(self, directory):
        self._objects, self.fingerprints, self._metadata = {}, {}, {}
        for filename, collection in [
            ("metrics.json", "metrics"),
            ("metric_relationships.json", "relationships"),
            ("dimensions.json", "dimensions"),
            ("business_rules.json", "rules"),
        ]:
            path = directory / filename
            content = path.read_bytes()
            self.fingerprints[str(path)] = hashlib.sha256(content).hexdigest()
            document = json.loads(content)
            self._metadata[collection] = {
                key: value for key, value in document.items() if key != collection
            }
            entries = document[collection]
            if len({x["id"] for x in entries}) != len(entries):
                raise BoundaryError("semantic_conflict", "duplicate semantic IDs")
            self._objects[collection] = {x["id"]: x for x in entries}
        for metric in self.all("metrics"):
            for dependency in metric.get("required_metrics", []):
                self.get_metric(dependency)
        for rel in self.all("relationships"):
            self.get_metric(rel["target_metric"])
            for driver in (
                rel.get("drivers", [])
                + rel.get("related_metrics", [])
                + [c["metric"] for c in rel.get("components", [])]
            ):
                self.get_metric(driver)
        for dimension in self.all("dimensions"):
            for metric_id in dimension.get("contribution_support", {}):
                self.get_metric(metric_id)

    def _get(self, collection, identifier):
        try:
            return copy.deepcopy(self._objects[collection][identifier])
        except KeyError:
            raise BoundaryError(
                "semantic_conflict", f"unknown {collection} ID: {identifier}"
            )

    def all(self, collection):
        return copy.deepcopy(list(self._objects[collection].values()))

    def metadata(self, collection):
        return copy.deepcopy(self._metadata[collection])

    def get_metric(self, metric_id):
        return self._get("metrics", metric_id)

    def get_relationship(self, relationship_id):
        return self._get("relationships", relationship_id)

    def get_dimension(self, dimension_id):
        return self._get("dimensions", dimension_id)

    def get_business_rule(self, rule_id):
        return self._get("rules", rule_id)

    def get_metric_relationships(self, metric_id):
        self.get_metric(metric_id)
        return [
            r
            for r in self.all("relationships")
            if r["target_metric"] == metric_id and r["type"] != "diagnostic"
        ]
