# Offline Agent Eval

Run: `8b2add8a-dfde-45ba-af47-f752ecae70fe`

Loaded 12; executed 11; passed 4; failed 3; review required 5.

| Metric | Value | Numerator / denominator |
|---|---:|---:|
| Calculation Accuracy | 66.67% | 4 / 6 |
| Workflow Path Accuracy | 50.00% | 3 / 6 |
| Primary Driver Accuracy | 40.00% | 2 / 5 |
| Correct Stop Rate | 100.00% | 7 / 7 |
| Routing Validity | 100.00% | 4 / 4 |
| Evidence Coverage | 100.00% | 18 / 18 |
| Unsupported Claim Rate | 0.00% | 0 / 18 |
| Required Claim Coverage | 50.00% | 2 / 4 |
| Overall Case Pass Rate | 33.33% | 4 / 12 |

Hard constraint violations: 0

Overall pass rate uses all loaded Cases. Review-required cases are excluded from component accuracy denominators, and never count as passes. Component accuracy is per applicable case; routing is per candidate selection; evidence metrics are per output core claim. N/A is not 100%.

## Case results

| Case | Status | Details |
|---|---|---|
| `gmv_orders_driver_001` | PASS | All applicable checks passed |
| `gmv_aov_driver_001` | PASS | All applicable checks passed |
| `orders_buyers_driver_001` | REVIEW_REQUIRED | Frozen gmv_diagnosis accepts ['gross_gmv'], but Case/Expected requests orders; no substitute workflow or retargeting was used. |
| `orders_frequency_driver_001` | REVIEW_REQUIRED | Impossible active-buyer constraint: Orders=90, distinct Buyers=100; every buyer needs at least one valid order with one customer identity. |
| `aov_units_driver_001` | REVIEW_REQUIRED | Frozen gmv_diagnosis accepts ['gross_gmv'], but Case/Expected requests aov; no substitute workflow or retargeting was used. |
| `aov_price_driver_001` | REVIEW_REQUIRED | Frozen gmv_diagnosis accepts ['gross_gmv'], but Case/Expected requests aov; no substitute workflow or retargeting was used. |
| `channel_gmv_drilldown_001` | FAIL | CalculationGrader: paid_search_effect: expected -2000, observed '<not observed>'; CalculationGrader: organic_effect: expected 0, observed '<not observed>'; CalculationGrader: direct_effect: expected 0, observed '<not observed>'; CalculationGrader: No contribution observed for gross_gmv / channel; required closure cannot be assessed; WorkflowPathGrader: Required gross_gmv × channel analytical path was not executed; PrimaryDriverGrader: top_dimension_driver: expected 'paid_search', observed '<not observed>' |
| `category_gmv_contribution_001` | FAIL | CalculationGrader: category_a_effect: expected -2000, observed '<not observed>'; CalculationGrader: category_b_effect: expected 0, observed '<not observed>'; CalculationGrader: No contribution observed for gross_gmv / category; required closure cannot be assessed; WorkflowPathGrader: Required gross_gmv × category analytical path was not executed; PrimaryDriverGrader: top_dimension_driver: expected 'category_a', observed '<not observed>' |
| `category_orders_illegal_contribution_001` | REVIEW_REQUIRED | Frozen gmv_diagnosis accepts ['gross_gmv'], but Case/Expected requests orders; no substitute workflow or retargeting was used. |
| `zero_baseline_001` | PASS | All applicable checks passed |
| `missing_paid_at_001` | PASS | All applicable checks passed |
| `evidence_boundary_paid_search_001` | FAIL | WorkflowPathGrader: Required orders × channel analytical path was not executed; PrimaryDriverGrader: top_dimension_driver: expected 'paid_search', observed '<not observed>'; EvidenceGrader: Required claim not communicated: Orders下降主要集中在Paid Search; EvidenceGrader: Required claim not communicated: 现有数据不足以判断Paid Search下降的进一步外部原因 |

Agent/specifications/Expected were not modified. No live API was used.

Leakage controls: all execution precedes Expected loading; Actual is saved first; worker copies exclude Case/Expected/graders and use opaque filenames. Audit hooks block outside reads and networking. This is a trusted-code evaluation boundary, not an OS security sandbox.

## Archive notes

Golden Set calibration: five cases required correction. Historical Case/Expected revisions are not reconstructed from the current Golden Set.
