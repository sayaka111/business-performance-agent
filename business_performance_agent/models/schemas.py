from dataclasses import dataclass, field, asdict
from datetime import date
from typing import Any, Literal

Status = Literal['success', 'warning', 'blocked', 'failed']
EvidenceLevel = Literal['direct', 'derived', 'unsupported']

class BoundaryError(Exception):
    def __init__(self, reason, detail=''):
        self.reason, self.detail = reason, detail or reason
        super().__init__(self.detail)

class TransientError(Exception):
    """Only this error is eligible for tool/skill retries."""

@dataclass(frozen=True)
class Period:
    start: str
    end: str

    def __post_init__(self):
        if date.fromisoformat(self.start) > date.fromisoformat(self.end):
            raise ValueError('period start must be <= end')

    def contains(self, value):
        return self.start <= value <= self.end

@dataclass(frozen=True)
class WorkflowInput:
    metric_id: str
    current_period: Period
    baseline_period: Period
    filters: dict[str, str] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def parse(cls, raw, knowledge, definition):
        allowed = {'metric_id', 'current_period', 'baseline_period', 'filters', 'context'}
        if not isinstance(raw, dict) or set(raw) - allowed:
            raise ValueError('unknown input fields')
        if raw.get('metric_id') not in definition['state_schema']['state']['target_metric']['allowed']:
            raise ValueError('unsupported target metric')
        current, baseline = Period(**raw['current_period']), Period(**raw['baseline_period'])
        if baseline.end >= current.start:
            raise ValueError('baseline must precede current period')
        filters = raw.get('filters', {})
        if not isinstance(filters, dict):
            raise ValueError('filters must be a semantic dimension map')
        for key, value in filters.items():
            dimension = knowledge.get_dimension(key)
            if not isinstance(value, str):
                raise ValueError('filter values must be strings')
            if dimension.get('values') and value not in dimension['values']:
                raise ValueError('filter value outside frozen dimension values')
        context = raw.get('context', {})
        if not isinstance(context, dict) or set(context) - {'customer_structure', 'traffic_view', 'preferred_dimension'}:
            raise ValueError('unsupported context')
        for flag in ('customer_structure', 'traffic_view'):
            if flag in context and not isinstance(context[flag], bool):
                raise ValueError('context flags must be booleans')
        if context.get('preferred_dimension'):
            knowledge.get_dimension(context['preferred_dimension'])
        return cls(raw['metric_id'], current, baseline, filters, context)

@dataclass
class ModuleResult:
    status: Status = 'success'
    result: dict = field(default_factory=dict)
    reason: str | None = None
    warnings: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)

@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    evidence_level: EvidenceLevel
    source_step: str
    payload: dict

def validate_shape(value, spec, path='state'):
    """Validate the frozen descriptive state format without rewriting it."""
    types = {'string': str, 'object': dict, 'array': list, 'integer': int, 'number': (int, float), 'null': type(None)}
    declared = spec.get('type')
    if declared:
        declared = [declared] if isinstance(declared, str) else declared
        if not any(isinstance(value, types[t]) and not (isinstance(value, bool) and t in ('integer','number')) for t in declared):
            raise ValueError(f'{path}: invalid type')
    for key in ('enum', 'allowed'):
        if key in spec and value not in spec[key]:
            raise ValueError(f'{path}: value outside {key}')
    if value is None:
        return
    if isinstance(value, (int, float)):
        if value < spec.get('minimum', float('-inf')) or value > spec.get('maximum', float('inf')):
            raise ValueError(f'{path}: outside bounds')
    if isinstance(value, dict):
        if set(spec.get('required', [])) - value.keys():
            raise ValueError(f'{path}: missing fields')
        for key, child in spec.get('properties', {}).items():
            if key in value:
                validate_shape(value[key], child, f'{path}.{key}')
    if isinstance(value, list) and 'items' in spec:
        for item in value:
            validate_shape(item, spec['items'], path + '[]')
