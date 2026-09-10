# Offline Agent Eval

Run: `5c7f83ec-1fac-4018-aeda-dc74649d9e28`

Loaded 20; executed 20; passed 16; failed 4; review required 0.

| Metric | Value | Numerator / denominator |
|---|---:|---:|
| Calculation Accuracy | 100.00% | 19 / 19 |
| Workflow Path Accuracy | 89.47% | 17 / 19 |
| Primary Driver Accuracy | 83.33% | 10 / 12 |
| Correct Stop Rate | 100.00% | 19 / 19 |
| First-Level Driver Accuracy | 88.89% | 8 / 9 |
| Nested Driver Accuracy | 50.00% | 2 / 4 |
| Routing Validity | 100.00% | 17 / 17 |
| Evidence Coverage | 100.00% | 52 / 52 |
| Unsupported Claim Rate | 0.00% | 0 / 52 |
| Required Claim Coverage | N/A | 0 / 0 |
| Overall Case Pass Rate | 80.00% | 16 / 20 |
| Intent Accuracy | 95.00% | 19 / 20 |

Hard constraint violations: 0

Overall pass rate uses all loaded Cases. Review-required cases are excluded from component accuracy denominators, and never count as passes. Component accuracy is per applicable case; routing is per candidate selection; evidence metrics are per output core claim. N/A is not 100%.

## Case results

| Case | Status | Details |
|---|---|---|
| `holdout_aov_price_down_units_offset_001` | FAIL | WorkflowPathGrader: relationship_gross_gmv_orders_aov: expected True, observed False; WorkflowPathGrader: relationship_aov_units_price: expected True, observed False; PrimaryDriverGrader: first_level_primary_driver: expected 'aov', observed None; PrimaryDriverGrader: nested_primary_driver: expected 'average_realized_unit_price', observed '<not observed>'; HoldoutBehaviorGrader: identify units_per_order as offsetting nested driver: expected True, observed False |
| `holdout_aov_units_down_price_offset_001` | PASS | All applicable checks passed |
| `holdout_category_multi_driver_001` | PASS | All applicable checks passed |
| `holdout_channel_multi_driver_001` | PASS | All applicable checks passed |
| `holdout_channel_unknown_share_high_001` | PASS | All applicable checks passed |
| `holdout_dimension_zero_baseline_001` | PASS | All applicable checks passed |
| `holdout_evidence_boundary_channel_002` | FAIL | Structured/semantic intent rejected; no Workflow result, calculation N/A; Intent mismatch: target, periods, filters or explicitly requested dimension |
| `holdout_explicit_category_intent_001` | PASS | All applicable checks passed |
| `holdout_explicit_channel_intent_001` | PASS | All applicable checks passed |
| `holdout_explicit_orders_category_illegal_001` | PASS | All applicable checks passed |
| `holdout_gmv_aov_down_orders_offset_001` | PASS | All applicable checks passed |
| `holdout_gmv_mixed_aov_primary_001` | PASS | All applicable checks passed |
| `holdout_gmv_mixed_orders_primary_001` | PASS | All applicable checks passed |
| `holdout_gmv_orders_down_aov_offset_001` | PASS | All applicable checks passed |
| `holdout_no_anomaly_001` | PASS | All applicable checks passed |
| `holdout_orders_buyers_down_frequency_offset_001` | PASS | All applicable checks passed |
| `holdout_orders_frequency_down_buyers_offset_001` | FAIL | WorkflowPathGrader: relationship_orders_buyers_frequency: expected True, observed False; PrimaryDriverGrader: nested_primary_driver: expected 'orders_per_buyer', observed '<not observed>'; HoldoutBehaviorGrader: identify buyers as offsetting nested driver: expected True, observed False |
| `holdout_region_gmv_drilldown_001` | PASS | All applicable checks passed |
| `holdout_requested_dimension_unavailable_001` | FAIL | HoldoutBehaviorGrader: report dimension unavailable: expected True, observed False; HoldoutBehaviorGrader: allowed_statuses: expected True, observed False |
| `holdout_small_decline_below_threshold_001` | PASS | All applicable checks passed |

Agent and frozen specifications were not modified. Expected is loaded only after execution; Golden Set revisions are documented separately. Live deepseek was used; Provider outcomes are reported separately.

Leakage controls: all execution precedes Expected loading; Actual is saved first; worker copies exclude Case/Expected/graders and use opaque filenames. Audit hooks block outside reads and networking. This is a trusted-code evaluation boundary, not an OS security sandbox.

## Live interpretation

Provider-interrupted and not-run cases are unscored/review-required, not calculation failures. Overall Case Pass Rate denominator is business-evaluable cases, not all loaded cases. Report fallback does not invalidate completed deterministic calculations. Intent accuracy requires target/periods/filters and explicit dimension preservation; it is separate from JSON schema compliance. Successful provider report behavior cannot be established when all reports fall back.

Provider metrics: {'provider_attempts': 43, 'provider_successes': 43, 'provider_failures': 0, 'provider_success_rate': {'numerator': 43, 'denominator': 43, 'value': 1.0}, 'count_429': 0, 'count_5xx': 0, 'retry_count': 0, 'fallback_count': 0, 'fallback_rate': {'numerator': 0, 'denominator': 19, 'value': 0.0}, 'structured_output_compliance': {'numerator': 43, 'denominator': 43, 'value': 1.0}}

## Archive notes

Final Phase 2 closure measurement. Pure DeepSeek, post Intent Contract Fix v1. Pre-fix comparison is mixed-provider Round 6, not a controlled model-only comparison. 20 cases; 16 PASS, 4 FAIL. Holdout v1 is now a regression set. PHASE 2 EVAL: CLOSED.
