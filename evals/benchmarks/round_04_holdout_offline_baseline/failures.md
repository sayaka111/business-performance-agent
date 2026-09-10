# Failed and review-required cases

## holdout_aov_price_down_units_offset_001

Status: FAIL

- WorkflowPathGrader: relationship_gross_gmv_orders_aov: expected True, observed False
- WorkflowPathGrader: relationship_aov_units_price: expected True, observed False
- PrimaryDriverGrader: first_level_primary_driver: expected 'aov', observed None
- PrimaryDriverGrader: nested_primary_driver: expected 'average_realized_unit_price', observed '<not observed>'
- HoldoutBehaviorGrader: identify units_per_order as offsetting nested driver: expected True, observed False

## holdout_aov_units_down_price_offset_001

Status: FAIL

- WorkflowPathGrader: relationship_gross_gmv_orders_aov: expected True, observed False
- WorkflowPathGrader: relationship_aov_units_price: expected True, observed False
- PrimaryDriverGrader: first_level_primary_driver: expected 'aov', observed None
- PrimaryDriverGrader: nested_primary_driver: expected 'units_per_order', observed '<not observed>'
- HoldoutBehaviorGrader: identify average_realized_unit_price as offsetting nested driver: expected True, observed False

## holdout_gmv_mixed_aov_primary_001

Status: FAIL

- CalculationGrader: delta_gmv: expected -4100, observed '<not observed>'
- CalculationGrader: orders_effect: expected -1850, observed '<not observed>'
- CalculationGrader: aov_effect: expected -2250, observed '<not observed>'
- CalculationGrader: No contribution observed for gross_gmv / relationship; required closure cannot be assessed
- WorkflowPathGrader: relationship_gross_gmv_orders_aov: expected True, observed False
- PrimaryDriverGrader: first_level_primary_driver: expected 'aov', observed None

## holdout_gmv_mixed_orders_primary_001

Status: FAIL

- CalculationGrader: delta_gmv: expected -4100, observed '<not observed>'
- CalculationGrader: orders_effect: expected -2250, observed '<not observed>'
- CalculationGrader: aov_effect: expected -1850, observed '<not observed>'
- CalculationGrader: No contribution observed for gross_gmv / relationship; required closure cannot be assessed
- WorkflowPathGrader: relationship_gross_gmv_orders_aov: expected True, observed False
- PrimaryDriverGrader: first_level_primary_driver: expected 'orders', observed None

## holdout_orders_frequency_down_buyers_offset_001

Status: FAIL

- WorkflowPathGrader: relationship_gross_gmv_orders_aov: expected True, observed False
- WorkflowPathGrader: relationship_orders_buyers_frequency: expected True, observed False
- PrimaryDriverGrader: first_level_primary_driver: expected 'orders', observed None
- PrimaryDriverGrader: nested_primary_driver: expected 'orders_per_buyer', observed '<not observed>'
- HoldoutBehaviorGrader: identify buyers as offsetting nested driver: expected True, observed False

## holdout_region_gmv_drilldown_001

Status: FAIL

- CalculationGrader: No contribution observed for gross_gmv / region; required closure cannot be assessed
- WorkflowPathGrader: Required gross_gmv × region analytical path was not executed
- PrimaryDriverGrader: top_dimension_driver: expected 'south', observed '<not observed>'
- HoldoutBehaviorGrader: dimension_selection: expected True, observed False

## holdout_requested_dimension_unavailable_001

Status: FAIL

- HoldoutBehaviorGrader: report dimension unavailable: expected True, observed False

