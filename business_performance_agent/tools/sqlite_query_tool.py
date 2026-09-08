"""Semantic query boundary; SQL is generated only by the adapter."""
import math
from .query_tool import QueryTool
from ..models.schemas import BoundaryError


class SQLiteQueryTool(QueryTool):
    def __init__(self, adapter):
        self.adapter = adapter
        self.calls = []

    def _run(self, operation, request, callback):
        start = len(self.adapter.operations)
        value = callback()
        def finite(item):
            if isinstance(item, float) and not math.isfinite(item):
                raise BoundaryError('semantic_conflict', 'Nonfinite query value')
            if isinstance(item, dict):
                for v in item.values(): finite(v)
            if isinstance(item, list):
                for v in item: finite(v)
        finite(value)
        provenance = dict(query_id=f'Q{len(self.calls)+1:05d}', dataset_id=self.adapter.mapping['dataset_id'],
                          backend='SQLite', operation=operation, request=request, read_only=True,
                          sql_query_ids=[x['query_id'] for x in self.adapter.operations[start:]])
        self.calls.append(provenance)
        return value, provenance

    def metric(self, metric_id, period, filters):
        value, source = self._run('metric', dict(metric_id=metric_id, period=period, filters=filters),
                                  lambda: self.adapter.metric(metric_id, period, filters))
        return dict(value=value, provenance=source)

    def segments(self, metric_id, dimension_id, period, filters):
        value, source = self._run('segments', dict(metric_id=metric_id, dimension_id=dimension_id, period=period, filters=filters),
                                  lambda: self.adapter.segments(metric_id, dimension_id, period, filters))
        return dict(values=value, provenance=source)

    def quality(self, scope):
        return self._run('quality', scope, lambda: self.adapter.quality(scope))[0]

    def relationship_available(self, relationship):
        metrics = relationship.get('drivers', [c['metric'] for c in relationship.get('components', [])])
        return all(self.adapter.capabilities.get(r, False) for r in relationship.get('requirements', [])) and all(self.adapter.metric_available(m) for m in metrics)

    def dimension_available(self, dimension_id):
        return self.adapter.dimension_available(dimension_id)
