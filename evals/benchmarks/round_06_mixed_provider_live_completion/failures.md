# Failed and review-required cases

## holdout_aov_price_down_units_offset_001

Status: FAIL

- WorkflowPathGrader: relationship_gross_gmv_orders_aov: expected True, observed False
- WorkflowPathGrader: relationship_aov_units_price: expected True, observed False
- PrimaryDriverGrader: first_level_primary_driver: expected 'aov', observed None
- PrimaryDriverGrader: nested_primary_driver: expected 'average_realized_unit_price', observed '<not observed>'
- HoldoutBehaviorGrader: identify units_per_order as offsetting nested driver: expected True, observed False

## holdout_category_multi_driver_001

Status: FAIL

- CalculationGrader: No contribution observed for gross_gmv / category; required closure cannot be assessed
- WorkflowPathGrader: Required gross_gmv × category analytical path was not executed
- PrimaryDriverGrader: top_dimension_driver: expected 'category_a', observed '<not observed>'
- HoldoutBehaviorGrader: expected_ranking: expected ['category_a', 'category_b'], observed []
- HoldoutBehaviorGrader: offsetting_segment_category_c: expected True, observed False
- HoldoutBehaviorGrader: dimension_selection: expected True, observed False
- Intent mismatch: target, periods, filters or explicitly requested dimension

## holdout_channel_multi_driver_001

Status: FAIL

- CalculationGrader: No contribution observed for gross_gmv / channel; required closure cannot be assessed
- WorkflowPathGrader: Required gross_gmv × channel analytical path was not executed
- PrimaryDriverGrader: top_dimension_driver: expected 'paid_search', observed '<not observed>'
- HoldoutBehaviorGrader: expected_ranking: expected ['paid_search', 'organic', 'affiliate'], observed []
- HoldoutBehaviorGrader: offsetting_segment_direct: expected True, observed False
- HoldoutBehaviorGrader: dimension_selection: expected True, observed False
- Intent mismatch: target, periods, filters or explicitly requested dimension

## holdout_channel_unknown_share_high_001

Status: FAIL

- WorkflowPathGrader: Required gross_gmv × channel analytical path was not executed
- HoldoutBehaviorGrader: preserve unknown segment: expected True, observed False
- HoldoutBehaviorGrader: emit warning_or_limitation: expected True, observed False
- HoldoutBehaviorGrader: avoid overconfident full attribution: expected True, observed False
- HoldoutBehaviorGrader: dimension_selection: expected True, observed False
- Intent mismatch: target, periods, filters or explicitly requested dimension

## holdout_dimension_zero_baseline_001

Status: FAIL

- WorkflowPathGrader: Required gross_gmv × channel analytical path was not executed
- HoldoutBehaviorGrader: segment relative_change undefined: expected True, observed False
- HoldoutBehaviorGrader: absolute_change=1500: expected True, observed False
- HoldoutBehaviorGrader: dimension_selection: expected True, observed False
- Intent mismatch: target, periods, filters or explicitly requested dimension

## holdout_evidence_boundary_channel_002

Status: FAIL

- WorkflowPathGrader: Required orders × channel analytical path was not executed
- PrimaryDriverGrader: first_level_primary_driver: expected 'orders', observed None
- PrimaryDriverGrader: top_dimension_driver: expected 'paid_search', observed '<not observed>'
- StopGrader: Stop 'data_unavailable' outside Expected allowed_stop_reasons
- HoldoutBehaviorGrader: state internal localization: expected True, observed False
- HoldoutBehaviorGrader: state external cause not established: expected True, observed False
- HoldoutBehaviorGrader: dimension_selection: expected True, observed False
- Intent mismatch: target, periods, filters or explicitly requested dimension

## holdout_explicit_category_intent_001

Status: FAIL

- WorkflowPathGrader: Required gross_gmv × category analytical path was not executed
- HoldoutBehaviorGrader: execute gross_gmv x category drilldown: expected True, observed False
- HoldoutBehaviorGrader: dimension_selection: expected True, observed False
- Intent mismatch: target, periods, filters or explicitly requested dimension

## holdout_explicit_channel_intent_001

Status: FAIL

- WorkflowPathGrader: Required gross_gmv × channel analytical path was not executed
- HoldoutBehaviorGrader: execute gross_gmv x channel drilldown: expected True, observed False
- HoldoutBehaviorGrader: preserve requested dimension scope: expected True, observed False
- HoldoutBehaviorGrader: dimension_selection: expected True, observed False
- Intent mismatch: target, periods, filters or explicitly requested dimension

## holdout_explicit_orders_category_illegal_001

Status: FAIL

- Intent mismatch: target, periods, filters or explicitly requested dimension

## holdout_region_gmv_drilldown_001

Status: FAIL

- CalculationGrader: No contribution observed for gross_gmv / region; required closure cannot be assessed
- WorkflowPathGrader: Required gross_gmv × region analytical path was not executed
- PrimaryDriverGrader: top_dimension_driver: expected 'south', observed '<not observed>'
- HoldoutBehaviorGrader: dimension_selection: expected True, observed False
- Intent mismatch: target, periods, filters or explicitly requested dimension

## holdout_requested_dimension_unavailable_001

Status: FAIL

- HoldoutBehaviorGrader: report dimension unavailable: expected True, observed False
- HoldoutBehaviorGrader: preserve valid overall diagnosis: expected True, observed False
- Intent mismatch: target, periods, filters or explicitly requested dimension

