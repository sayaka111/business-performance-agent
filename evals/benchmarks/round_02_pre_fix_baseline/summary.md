# Offline Agent Eval

Run: `7bcf5d5d-a82b-4307-83b8-a9f8dbbf4f8d`

Loaded 12; executed 12; passed 9; failed 3; review required 0.

| Metric | Value | Numerator / denominator |
|---|---:|---:|
| Calculation Accuracy | 81.82% | 9 / 11 |
| Workflow Path Accuracy | 72.73% | 8 / 11 |
| Primary Driver Accuracy | 70.00% | 7 / 10 |
| Correct Stop Rate | 100.00% | 12 / 12 |
| First-Level Driver Accuracy | 100.00% | 8 / 8 |
| Nested Driver Accuracy | 100.00% | 4 / 4 |
| Routing Validity | 100.00% | 9 / 9 |
| Evidence Coverage | 100.00% | 34 / 34 |
| Unsupported Claim Rate | 0.00% | 0 / 34 |
| Required Claim Coverage | 50.00% | 2 / 4 |
| Overall Case Pass Rate | 75.00% | 9 / 12 |

Hard constraint violations: 0

Overall pass rate uses all loaded Cases. Review-required cases are excluded from component accuracy denominators, and never count as passes. Component accuracy is per applicable case; routing is per candidate selection; evidence metrics are per output core claim. N/A is not 100%.

## Case results

| Case | Status | Details |
|---|---|---|
| `gmv_orders_driver_001` | PASS | All applicable checks passed |
| `gmv_aov_driver_001` | PASS | All applicable checks passed |
| `orders_buyers_driver_001` | PASS | All applicable checks passed |
| `orders_frequency_driver_001` | PASS | All applicable checks passed |
| `aov_units_driver_001` | PASS | All applicable checks passed |
| `aov_price_driver_001` | PASS | All applicable checks passed |
| `channel_gmv_drilldown_001` | FAIL | CalculationGrader: paid_search_effect: expected -2000, observed '<not observed>'; CalculationGrader: organic_effect: expected 0, observed '<not observed>'; CalculationGrader: direct_effect: expected 0, observed '<not observed>'; CalculationGrader: No contribution observed for gross_gmv / channel; required closure cannot be assessed; WorkflowPathGrader: Required gross_gmv × channel analytical path was not executed; PrimaryDriverGrader: top_dimension_driver: expected 'paid_search', observed '<not observed>' |
| `category_gmv_contribution_001` | FAIL | CalculationGrader: category_a_effect: expected -2000, observed '<not observed>'; CalculationGrader: category_b_effect: expected 0, observed '<not observed>'; CalculationGrader: No contribution observed for gross_gmv / category; required closure cannot be assessed; WorkflowPathGrader: Required gross_gmv × category analytical path was not executed; PrimaryDriverGrader: top_dimension_driver: expected 'category_a', observed '<not observed>' |
| `category_orders_illegal_contribution_001` | PASS | All applicable checks passed |
| `zero_baseline_001` | PASS | All applicable checks passed |
| `missing_paid_at_001` | PASS | All applicable checks passed |
| `evidence_boundary_paid_search_001` | FAIL | WorkflowPathGrader: Required orders × channel analytical path was not executed; PrimaryDriverGrader: top_dimension_driver: expected 'paid_search', observed '<not observed>'; EvidenceGrader: Required claim not communicated: Orders下降主要集中在Paid Search; EvidenceGrader: Required claim not communicated: 现有数据不足以判断Paid Search下降的进一步外部原因 |

Agent and frozen specifications were not modified. Expected is loaded only after execution; Golden Set revisions are documented separately. No live API was used.

Leakage controls: all execution precedes Expected loading; Actual is saved first; worker copies exclude Case/Expected/graders and use opaque filenames. Audit hooks block outside reads and networking. This is a trusted-code evaluation boundary, not an OS security sandbox.

## Archive notes

Pre-fix baseline using corrected GMV-entry Golden Set. Three dimension/evidence failures remain. No Agent changes between Round 1 and Round 2.
