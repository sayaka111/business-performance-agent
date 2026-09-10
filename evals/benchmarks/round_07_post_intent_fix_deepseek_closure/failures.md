# Failed and review-required cases

## holdout_aov_price_down_units_offset_001

Status: FAIL

- WorkflowPathGrader: relationship_gross_gmv_orders_aov: expected True, observed False
- WorkflowPathGrader: relationship_aov_units_price: expected True, observed False
- PrimaryDriverGrader: first_level_primary_driver: expected 'aov', observed None
- PrimaryDriverGrader: nested_primary_driver: expected 'average_realized_unit_price', observed '<not observed>'
- HoldoutBehaviorGrader: identify units_per_order as offsetting nested driver: expected True, observed False

## holdout_evidence_boundary_channel_002

Status: FAIL

- Structured/semantic intent rejected; no Workflow result, calculation N/A
- Intent mismatch: target, periods, filters or explicitly requested dimension

## holdout_orders_frequency_down_buyers_offset_001

Status: FAIL

- WorkflowPathGrader: relationship_orders_buyers_frequency: expected True, observed False
- PrimaryDriverGrader: nested_primary_driver: expected 'orders_per_buyer', observed '<not observed>'
- HoldoutBehaviorGrader: identify buyers as offsetting nested driver: expected True, observed False

## holdout_requested_dimension_unavailable_001

Status: FAIL

- HoldoutBehaviorGrader: report dimension unavailable: expected True, observed False
- HoldoutBehaviorGrader: allowed_statuses: expected True, observed False

