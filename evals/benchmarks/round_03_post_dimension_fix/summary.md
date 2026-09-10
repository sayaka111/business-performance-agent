# Offline Agent Eval

Run: `4c98ee0c-ec72-4776-a273-676b276326e4`

Loaded 12; executed 12; passed 12; failed 0; review required 0.

| Metric | Value | Numerator / denominator |
|---|---:|---:|
| Calculation Accuracy | 100.00% | 11 / 11 |
| Workflow Path Accuracy | 100.00% | 11 / 11 |
| Primary Driver Accuracy | 100.00% | 10 / 10 |
| Correct Stop Rate | 100.00% | 12 / 12 |
| First-Level Driver Accuracy | 100.00% | 8 / 8 |
| Nested Driver Accuracy | 100.00% | 4 / 4 |
| Routing Validity | 100.00% | 11 / 11 |
| Evidence Coverage | 100.00% | 35 / 35 |
| Unsupported Claim Rate | 0.00% | 0 / 35 |
| Required Claim Coverage | 100.00% | 4 / 4 |
| Overall Case Pass Rate | 100.00% | 12 / 12 |

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
| `channel_gmv_drilldown_001` | PASS | All applicable checks passed |
| `category_gmv_contribution_001` | PASS | All applicable checks passed |
| `category_orders_illegal_contribution_001` | PASS | All applicable checks passed |
| `zero_baseline_001` | PASS | All applicable checks passed |
| `missing_paid_at_001` | PASS | All applicable checks passed |
| `evidence_boundary_paid_search_001` | PASS | All applicable checks passed |

Expected is loaded only after execution. Changes relative to previous benchmarks are documented in archive notes and metadata. No live API was used.

Leakage controls: all execution precedes Expected loading; Actual is saved first; worker copies exclude Case/Expected/graders and use opaque filenames. Audit hooks block outside reads and networking. This is a trusted-code evaluation boundary, not an OS security sandbox.

## Archive notes

Post-fix regression: only Runtime engine/router orchestration changed; same Round 2 Cases/Expected and fixture business data. Root-cause analysis is in evals/ROUND_3_ROOT_CAUSE.md. Software tests: 93 passed, 0 failed, 1 live skipped. No Agent edits after this run.
