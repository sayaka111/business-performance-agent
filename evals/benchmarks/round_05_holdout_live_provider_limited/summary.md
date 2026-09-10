# Offline Agent Eval

Run: `192f066a-461f-4e9e-ae82-e51f75cf1c18`

Loaded 20; executed 3; passed 1; failed 1; review required 18.

| Metric | Value | Numerator / denominator |
|---|---:|---:|
| Calculation Accuracy | 50.00% | 1 / 2 |
| Workflow Path Accuracy | 50.00% | 1 / 2 |
| Primary Driver Accuracy | 50.00% | 1 / 2 |
| Correct Stop Rate | 100.00% | 2 / 2 |
| First-Level Driver Accuracy | 100.00% | 1 / 1 |
| Nested Driver Accuracy | 100.00% | 1 / 1 |
| Routing Validity | N/A | 0 / 0 |
| Evidence Coverage | 100.00% | 6 / 6 |
| Unsupported Claim Rate | 0.00% | 0 / 6 |
| Required Claim Coverage | N/A | 0 / 0 |
| Overall Case Pass Rate | 50.00% | 1 / 2 |
| Intent Accuracy | 50.00% | 1 / 2 |

Hard constraint violations: 0

Overall pass rate uses all loaded Cases. Review-required cases are excluded from component accuracy denominators, and never count as passes. Component accuracy is per applicable case; routing is per candidate selection; evidence metrics are per output core claim. N/A is not 100%.

## Case results

| Case | Status | Details |
|---|---|---|
| `holdout_aov_price_down_units_offset_001` | REVIEW_REQUIRED | Provider failure interrupted intent/routing; business checks N/A |
| `holdout_aov_units_down_price_offset_001` | PASS | All applicable checks passed |
| `holdout_category_multi_driver_001` | FAIL | CalculationGrader: No contribution observed for gross_gmv / category; required closure cannot be assessed; WorkflowPathGrader: Required gross_gmv × category analytical path was not executed; PrimaryDriverGrader: top_dimension_driver: expected 'category_a', observed '<not observed>'; HoldoutBehaviorGrader: expected_ranking: expected ['category_a', 'category_b'], observed []; HoldoutBehaviorGrader: offsetting_segment_category_c: expected True, observed False; HoldoutBehaviorGrader: dimension_selection: expected True, observed False; Intent mismatch: target, periods, filters or explicitly requested dimension |
| `holdout_channel_multi_driver_001` | REVIEW_REQUIRED | three_consecutive_provider_failures |
| `holdout_channel_unknown_share_high_001` | REVIEW_REQUIRED | three_consecutive_provider_failures |
| `holdout_dimension_zero_baseline_001` | REVIEW_REQUIRED | three_consecutive_provider_failures |
| `holdout_evidence_boundary_channel_002` | REVIEW_REQUIRED | three_consecutive_provider_failures |
| `holdout_explicit_category_intent_001` | REVIEW_REQUIRED | three_consecutive_provider_failures |
| `holdout_explicit_channel_intent_001` | REVIEW_REQUIRED | three_consecutive_provider_failures |
| `holdout_explicit_orders_category_illegal_001` | REVIEW_REQUIRED | three_consecutive_provider_failures |
| `holdout_gmv_aov_down_orders_offset_001` | REVIEW_REQUIRED | three_consecutive_provider_failures |
| `holdout_gmv_mixed_aov_primary_001` | REVIEW_REQUIRED | three_consecutive_provider_failures |
| `holdout_gmv_mixed_orders_primary_001` | REVIEW_REQUIRED | three_consecutive_provider_failures |
| `holdout_gmv_orders_down_aov_offset_001` | REVIEW_REQUIRED | three_consecutive_provider_failures |
| `holdout_no_anomaly_001` | REVIEW_REQUIRED | three_consecutive_provider_failures |
| `holdout_orders_buyers_down_frequency_offset_001` | REVIEW_REQUIRED | three_consecutive_provider_failures |
| `holdout_orders_frequency_down_buyers_offset_001` | REVIEW_REQUIRED | three_consecutive_provider_failures |
| `holdout_region_gmv_drilldown_001` | REVIEW_REQUIRED | three_consecutive_provider_failures |
| `holdout_requested_dimension_unavailable_001` | REVIEW_REQUIRED | three_consecutive_provider_failures |
| `holdout_small_decline_below_threshold_001` | REVIEW_REQUIRED | three_consecutive_provider_failures |

Agent and frozen specifications were not modified. Expected is loaded only after execution; Golden Set revisions are documented separately. Live Gemini was used; Provider outcomes are reported separately.

Leakage controls: all execution precedes Expected loading; Actual is saved first; worker copies exclude Case/Expected/graders and use opaque filenames. Audit hooks block outside reads and networking. This is a trusted-code evaluation boundary, not an OS security sandbox.

## Live interpretation

Provider-interrupted and not-run cases are unscored/review-required, not calculation failures. Overall Case Pass Rate denominator is business-evaluable cases, not all loaded cases. Report fallback does not invalidate completed deterministic calculations. Intent accuracy requires target/periods/filters and explicit dimension preservation; it is separate from JSON schema compliance. Successful Gemini report behavior cannot be established when all reports fall back.

Provider metrics: {'provider_attempts': 9, 'provider_successes': 2, 'provider_failures': 7, 'provider_success_rate': {'numerator': 2, 'denominator': 9, 'value': 0.2222222222222222}, 'count_429': 2, 'count_5xx': 5, 'retry_count': 4, 'fallback_count': 2, 'fallback_rate': {'numerator': 2, 'denominator': 2, 'value': 1.0}, 'structured_output_compliance': {'numerator': 2, 'denominator': 2, 'value': 1.0}}

## Archive notes

Phase2B bounded Live Gemini attempt. Provider circuit stopped after3 consecutive provider-failed cases:3 attempted,2 business-evaluable (1pass/1fail),1 provider-interrupted,17not run. Nine requests:2 successes,7 failures (2x429,5x5xx),4 retries,2report fallbacks. Provider-interrupted/not-run cases are unscored and excluded from business metrics. No successful live routing/report sample; do not claim those capabilities validated. Agent and source Cases/Expected unchanged.
