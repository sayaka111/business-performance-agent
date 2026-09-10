# Offline Agent Eval

Run: `69f53752-09dd-4ac0-8d74-8d6dcbad7b33`

Loaded 20; executed 20; passed 13; failed 7; review required 0.

| Metric | Value | Numerator / denominator |
|---|---:|---:|
| Calculation Accuracy | 83.33% | 15 / 18 |
| Workflow Path Accuracy | 70.00% | 14 / 20 |
| Primary Driver Accuracy | 53.85% | 7 / 13 |
| Correct Stop Rate | 100.00% | 20 / 20 |
| First-Level Driver Accuracy | 50.00% | 5 / 10 |
| Nested Driver Accuracy | 25.00% | 1 / 4 |
| Routing Validity | 100.00% | 15 / 15 |
| Evidence Coverage | 100.00% | 46 / 46 |
| Unsupported Claim Rate | 0.00% | 0 / 46 |
| Required Claim Coverage | N/A | 0 / 0 |
| Overall Case Pass Rate | 65.00% | 13 / 20 |
| Dimension Selection Accuracy | 87.50% | 7 / 8 |

Hard constraint violations: 0

Overall pass rate uses all loaded Cases. Review-required cases are excluded from component accuracy denominators, and never count as passes. Component accuracy is per applicable case; routing is per candidate selection; evidence metrics are per output core claim. N/A is not 100%.

## Case results

| Case | Status | Details |
|---|---|---|
| `holdout_aov_price_down_units_offset_001` | FAIL | WorkflowPathGrader: relationship_gross_gmv_orders_aov: expected True, observed False; WorkflowPathGrader: relationship_aov_units_price: expected True, observed False; PrimaryDriverGrader: first_level_primary_driver: expected 'aov', observed None; PrimaryDriverGrader: nested_primary_driver: expected 'average_realized_unit_price', observed '<not observed>'; HoldoutBehaviorGrader: identify units_per_order as offsetting nested driver: expected True, observed False |
| `holdout_aov_units_down_price_offset_001` | FAIL | WorkflowPathGrader: relationship_gross_gmv_orders_aov: expected True, observed False; WorkflowPathGrader: relationship_aov_units_price: expected True, observed False; PrimaryDriverGrader: first_level_primary_driver: expected 'aov', observed None; PrimaryDriverGrader: nested_primary_driver: expected 'units_per_order', observed '<not observed>'; HoldoutBehaviorGrader: identify average_realized_unit_price as offsetting nested driver: expected True, observed False |
| `holdout_category_multi_driver_001` | PASS | All applicable checks passed |
| `holdout_channel_multi_driver_001` | PASS | All applicable checks passed |
| `holdout_channel_unknown_share_high_001` | PASS | All applicable checks passed |
| `holdout_dimension_zero_baseline_001` | PASS | All applicable checks passed |
| `holdout_evidence_boundary_channel_002` | PASS | All applicable checks passed |
| `holdout_explicit_category_intent_001` | PASS | All applicable checks passed |
| `holdout_explicit_channel_intent_001` | PASS | All applicable checks passed |
| `holdout_explicit_orders_category_illegal_001` | PASS | All applicable checks passed |
| `holdout_gmv_aov_down_orders_offset_001` | PASS | All applicable checks passed |
| `holdout_gmv_mixed_aov_primary_001` | FAIL | CalculationGrader: delta_gmv: expected -4100, observed '<not observed>'; CalculationGrader: orders_effect: expected -1850, observed '<not observed>'; CalculationGrader: aov_effect: expected -2250, observed '<not observed>'; CalculationGrader: No contribution observed for gross_gmv / relationship; required closure cannot be assessed; WorkflowPathGrader: relationship_gross_gmv_orders_aov: expected True, observed False; PrimaryDriverGrader: first_level_primary_driver: expected 'aov', observed None |
| `holdout_gmv_mixed_orders_primary_001` | FAIL | CalculationGrader: delta_gmv: expected -4100, observed '<not observed>'; CalculationGrader: orders_effect: expected -2250, observed '<not observed>'; CalculationGrader: aov_effect: expected -1850, observed '<not observed>'; CalculationGrader: No contribution observed for gross_gmv / relationship; required closure cannot be assessed; WorkflowPathGrader: relationship_gross_gmv_orders_aov: expected True, observed False; PrimaryDriverGrader: first_level_primary_driver: expected 'orders', observed None |
| `holdout_gmv_orders_down_aov_offset_001` | PASS | All applicable checks passed |
| `holdout_no_anomaly_001` | PASS | All applicable checks passed |
| `holdout_orders_buyers_down_frequency_offset_001` | PASS | All applicable checks passed |
| `holdout_orders_frequency_down_buyers_offset_001` | FAIL | WorkflowPathGrader: relationship_gross_gmv_orders_aov: expected True, observed False; WorkflowPathGrader: relationship_orders_buyers_frequency: expected True, observed False; PrimaryDriverGrader: first_level_primary_driver: expected 'orders', observed None; PrimaryDriverGrader: nested_primary_driver: expected 'orders_per_buyer', observed '<not observed>'; HoldoutBehaviorGrader: identify buyers as offsetting nested driver: expected True, observed False |
| `holdout_region_gmv_drilldown_001` | FAIL | CalculationGrader: No contribution observed for gross_gmv / region; required closure cannot be assessed; WorkflowPathGrader: Required gross_gmv × region analytical path was not executed; PrimaryDriverGrader: top_dimension_driver: expected 'south', observed '<not observed>'; HoldoutBehaviorGrader: dimension_selection: expected True, observed False |
| `holdout_requested_dimension_unavailable_001` | FAIL | HoldoutBehaviorGrader: report dimension unavailable: expected True, observed False |
| `holdout_small_decline_below_threshold_001` | PASS | All applicable checks passed |

Expected is loaded only after execution. Changes relative to previous benchmarks are documented in archive notes and metadata. No live API was used.

Leakage controls: all execution precedes Expected loading; Actual is saved first; worker copies exclude Case/Expected/graders and use opaque filenames. Audit hooks block outside reads and networking. This is a trusted-code evaluation boundary, not an OS security sandbox.

## Holdout interpretation

unchanged Round 3 deterministic workflow_input; offline does not assess a real intent LLM

First offline baseline includes deterministic input-translation mismatches; these are not claims about live model intent accuracy.

Qualitative construction choices are disclosed per Actual fixture; source Case/Expected remain unchanged.

## Archive notes

First Holdout Offline baseline, separate from the original 12-case Golden Set. Agent unchanged. 20 executed, 13 pass, 7 fail. Four failures are preceded by the inherited eval input translator selecting AOV/Orders rather than GMV; the Region wording is not recognized by that translator. One Case asks for decomposition with stable Orders and AOV100→91.2, only an8.8% GMV decline below frozen10% warning threshold. The requested unavailable Channel is not disclosed explicitly. These are raw benchmark failures, not seven proven Agent business-logic defects. Do not overwrite; any corrected evaluation must be a new round. No live API was used.
