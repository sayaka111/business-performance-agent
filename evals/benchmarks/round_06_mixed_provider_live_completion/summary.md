# Phase 2 Live Eval — Gemini → DeepSeek Continuation

# Offline Agent Eval

Run: `52bfe4d8-c811-4a1f-a63b-9ef24f6583bb`

Loaded 20; executed 20; passed 9; failed 11; review required 0.

| Metric | Value | Numerator / denominator |
|---|---:|---:|
| Calculation Accuracy | 84.21% | 16 / 19 |
| Workflow Path Accuracy | 55.00% | 11 / 20 |
| Primary Driver Accuracy | 61.54% | 8 / 13 |
| Correct Stop Rate | 95.00% | 19 / 20 |
| First-Level Driver Accuracy | 80.00% | 8 / 10 |
| Nested Driver Accuracy | 75.00% | 3 / 4 |
| Routing Validity | 100.00% | 10 / 10 |
| Evidence Coverage | 100.00% | 48 / 48 |
| Unsupported Claim Rate | 0.00% | 0 / 48 |
| Required Claim Coverage | N/A | 0 / 0 |
| Overall Case Pass Rate | 45.00% | 9 / 20 |

Hard constraint violations: 0

Overall pass rate uses all loaded Cases. Review-required cases are excluded from component accuracy denominators, and never count as passes. Component accuracy is per applicable case; routing is per candidate selection; evidence metrics are per output core claim. N/A is not 100%.

## Case results

| Case | Status | Details |
|---|---|---|
| `holdout_aov_price_down_units_offset_001` | FAIL | WorkflowPathGrader: relationship_gross_gmv_orders_aov: expected True, observed False; WorkflowPathGrader: relationship_aov_units_price: expected True, observed False; PrimaryDriverGrader: first_level_primary_driver: expected 'aov', observed None; PrimaryDriverGrader: nested_primary_driver: expected 'average_realized_unit_price', observed '<not observed>'; HoldoutBehaviorGrader: identify units_per_order as offsetting nested driver: expected True, observed False |
| `holdout_aov_units_down_price_offset_001` | PASS | All applicable checks passed |
| `holdout_category_multi_driver_001` | FAIL | CalculationGrader: No contribution observed for gross_gmv / category; required closure cannot be assessed; WorkflowPathGrader: Required gross_gmv × category analytical path was not executed; PrimaryDriverGrader: top_dimension_driver: expected 'category_a', observed '<not observed>'; HoldoutBehaviorGrader: expected_ranking: expected ['category_a', 'category_b'], observed []; HoldoutBehaviorGrader: offsetting_segment_category_c: expected True, observed False; HoldoutBehaviorGrader: dimension_selection: expected True, observed False; Intent mismatch: target, periods, filters or explicitly requested dimension |
| `holdout_channel_multi_driver_001` | FAIL | CalculationGrader: No contribution observed for gross_gmv / channel; required closure cannot be assessed; WorkflowPathGrader: Required gross_gmv × channel analytical path was not executed; PrimaryDriverGrader: top_dimension_driver: expected 'paid_search', observed '<not observed>'; HoldoutBehaviorGrader: expected_ranking: expected ['paid_search', 'organic', 'affiliate'], observed []; HoldoutBehaviorGrader: offsetting_segment_direct: expected True, observed False; HoldoutBehaviorGrader: dimension_selection: expected True, observed False; Intent mismatch: target, periods, filters or explicitly requested dimension |
| `holdout_channel_unknown_share_high_001` | FAIL | WorkflowPathGrader: Required gross_gmv × channel analytical path was not executed; HoldoutBehaviorGrader: preserve unknown segment: expected True, observed False; HoldoutBehaviorGrader: emit warning_or_limitation: expected True, observed False; HoldoutBehaviorGrader: avoid overconfident full attribution: expected True, observed False; HoldoutBehaviorGrader: dimension_selection: expected True, observed False; Intent mismatch: target, periods, filters or explicitly requested dimension |
| `holdout_dimension_zero_baseline_001` | FAIL | WorkflowPathGrader: Required gross_gmv × channel analytical path was not executed; HoldoutBehaviorGrader: segment relative_change undefined: expected True, observed False; HoldoutBehaviorGrader: absolute_change=1500: expected True, observed False; HoldoutBehaviorGrader: dimension_selection: expected True, observed False; Intent mismatch: target, periods, filters or explicitly requested dimension |
| `holdout_evidence_boundary_channel_002` | FAIL | WorkflowPathGrader: Required orders × channel analytical path was not executed; PrimaryDriverGrader: first_level_primary_driver: expected 'orders', observed None; PrimaryDriverGrader: top_dimension_driver: expected 'paid_search', observed '<not observed>'; StopGrader: Stop 'data_unavailable' outside Expected allowed_stop_reasons; HoldoutBehaviorGrader: state internal localization: expected True, observed False; HoldoutBehaviorGrader: state external cause not established: expected True, observed False; HoldoutBehaviorGrader: dimension_selection: expected True, observed False; Intent mismatch: target, periods, filters or explicitly requested dimension |
| `holdout_explicit_category_intent_001` | FAIL | WorkflowPathGrader: Required gross_gmv × category analytical path was not executed; HoldoutBehaviorGrader: execute gross_gmv x category drilldown: expected True, observed False; HoldoutBehaviorGrader: dimension_selection: expected True, observed False; Intent mismatch: target, periods, filters or explicitly requested dimension |
| `holdout_explicit_channel_intent_001` | FAIL | WorkflowPathGrader: Required gross_gmv × channel analytical path was not executed; HoldoutBehaviorGrader: execute gross_gmv x channel drilldown: expected True, observed False; HoldoutBehaviorGrader: preserve requested dimension scope: expected True, observed False; HoldoutBehaviorGrader: dimension_selection: expected True, observed False; Intent mismatch: target, periods, filters or explicitly requested dimension |
| `holdout_explicit_orders_category_illegal_001` | FAIL | Intent mismatch: target, periods, filters or explicitly requested dimension |
| `holdout_gmv_aov_down_orders_offset_001` | PASS | All applicable checks passed |
| `holdout_gmv_mixed_aov_primary_001` | PASS | All applicable checks passed |
| `holdout_gmv_mixed_orders_primary_001` | PASS | All applicable checks passed |
| `holdout_gmv_orders_down_aov_offset_001` | PASS | All applicable checks passed |
| `holdout_no_anomaly_001` | PASS | All applicable checks passed |
| `holdout_orders_buyers_down_frequency_offset_001` | PASS | All applicable checks passed |
| `holdout_orders_frequency_down_buyers_offset_001` | PASS | All applicable checks passed |
| `holdout_region_gmv_drilldown_001` | FAIL | CalculationGrader: No contribution observed for gross_gmv / region; required closure cannot be assessed; WorkflowPathGrader: Required gross_gmv × region analytical path was not executed; PrimaryDriverGrader: top_dimension_driver: expected 'south', observed '<not observed>'; HoldoutBehaviorGrader: dimension_selection: expected True, observed False; Intent mismatch: target, periods, filters or explicitly requested dimension |
| `holdout_requested_dimension_unavailable_001` | FAIL | HoldoutBehaviorGrader: report dimension unavailable: expected True, observed False; HoldoutBehaviorGrader: preserve valid overall diagnosis: expected True, observed False; Intent mismatch: target, periods, filters or explicitly requested dimension |
| `holdout_small_decline_below_threshold_001` | PASS | All applicable checks passed |

Agent and frozen specifications were not modified. Expected is loaded only after execution; Golden Set revisions are documented separately. Live Gemini and DeepSeek results are combined with explicit provenance.

Leakage controls: all execution precedes Expected loading; Actual is saved first; worker copies exclude Case/Expected/graders and use opaque filenames. Audit hooks block outside reads and networking. This is a trusted-code evaluation boundary, not an OS security sandbox.

Historical Gemini PASS and FAIL are preserved without re-execution or regrading. Provider reliability includes prior interrupted Gemini requests. DeepSeek smoke is excluded from Eval request counts. This is not a pure DeepSeek benchmark.

## Archive notes

Continuation of 192f066a-461f-4e9e-ae82-e51f75cf1c18; new DeepSeek run cde00ed0-50e6-44b0-8d84-2a52163d099a. Existing Gemini grades retained. No business logic, Cases, Expected, fixtures or graders changed. Single-attempt DeepSeek smoke passed before continuation and is excluded from provider metrics.
