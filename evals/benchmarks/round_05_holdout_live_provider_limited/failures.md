# Failed and review-required cases

## holdout_aov_price_down_units_offset_001

Status: REVIEW_REQUIRED

- Provider failure interrupted intent/routing; business checks N/A

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

Status: REVIEW_REQUIRED

- three_consecutive_provider_failures

## holdout_channel_unknown_share_high_001

Status: REVIEW_REQUIRED

- three_consecutive_provider_failures

## holdout_dimension_zero_baseline_001

Status: REVIEW_REQUIRED

- three_consecutive_provider_failures

## holdout_evidence_boundary_channel_002

Status: REVIEW_REQUIRED

- three_consecutive_provider_failures

## holdout_explicit_category_intent_001

Status: REVIEW_REQUIRED

- three_consecutive_provider_failures

## holdout_explicit_channel_intent_001

Status: REVIEW_REQUIRED

- three_consecutive_provider_failures

## holdout_explicit_orders_category_illegal_001

Status: REVIEW_REQUIRED

- three_consecutive_provider_failures

## holdout_gmv_aov_down_orders_offset_001

Status: REVIEW_REQUIRED

- three_consecutive_provider_failures

## holdout_gmv_mixed_aov_primary_001

Status: REVIEW_REQUIRED

- three_consecutive_provider_failures

## holdout_gmv_mixed_orders_primary_001

Status: REVIEW_REQUIRED

- three_consecutive_provider_failures

## holdout_gmv_orders_down_aov_offset_001

Status: REVIEW_REQUIRED

- three_consecutive_provider_failures

## holdout_no_anomaly_001

Status: REVIEW_REQUIRED

- three_consecutive_provider_failures

## holdout_orders_buyers_down_frequency_offset_001

Status: REVIEW_REQUIRED

- three_consecutive_provider_failures

## holdout_orders_frequency_down_buyers_offset_001

Status: REVIEW_REQUIRED

- three_consecutive_provider_failures

## holdout_region_gmv_drilldown_001

Status: REVIEW_REQUIRED

- three_consecutive_provider_failures

## holdout_requested_dimension_unavailable_001

Status: REVIEW_REQUIRED

- three_consecutive_provider_failures

## holdout_small_decline_below_threshold_001

Status: REVIEW_REQUIRED

- three_consecutive_provider_failures

