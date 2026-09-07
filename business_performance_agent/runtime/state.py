from dataclasses import dataclass, field, asdict
from ..models.schemas import validate_shape

@dataclass
class WorkflowState:
    workflow_status: str = 'initialized'
    target_metric: str = 'gross_gmv'
    current_period: dict = field(default_factory=lambda: {'start':None,'end':None})
    baseline_period: dict = field(default_factory=lambda: {'start':None,'end':None})
    current_node: str | None = 'validate_input'
    current_metric: str | None = None
    current_filters: dict = field(default_factory=dict)
    analysis_path: list = field(default_factory=list)
    available_relationships: list = field(default_factory=list)
    selected_relationship: str | None = None
    decomposition_result: dict | None = None
    contribution_result: dict | None = None
    selected_driver: dict | None = None
    selected_dimension: str | None = None
    depth: int = 0
    aligned_coverage: float = 0.0
    evidence: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    limitations: list = field(default_factory=list)
    failed_branches: list = field(default_factory=list)
    retry_count: int = 0
    stop_reason: str | None = None

    def validate(self, schema):
        value = asdict(self)
        for key,spec in schema['state'].items():
            validate_shape(value[key],spec,key)
        return value
