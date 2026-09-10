# Phase 2 Final Post-Fix Regression — Closure Report

## STATUS

COMPLETED

Final run: `5c7f83ec-1fac-4018-aeda-dc74649d9e28`. Pure DeepSeek / `deepseek-v4-flash`, Post-Intent-Fix code, existing Holdout v1 synthetic SQLite fixtures. All 20 Actual checkpoints are new. No Gemini calls, no reuse of old Actuals, no code or grading changes during this measurement.

## FINAL RESULT

| Total | PASS | FAIL | Pass Rate | Pending / Review |
|---:|---:|---:|---:|---:|
| 20 | 16 | 4 | 80.00% (16/20) | 0 / 0 |

20 executions include 19 Workflow Results and one locally rejected Intent. The existing grader counts that semantic rejection as a case FAIL, but calculation/path/stop checks are N/A for that case. The worker completion count does not mean 20 successful workflows.

## PRE-FIX VS POST-FIX

Baseline: mixed Gemini → DeepSeek run `52bfe4d8-c811-4a1f-a63b-9ef24f6583bb`, 9/20 PASS. This is a pre/post observation, not a controlled pure model experiment: provider composition and stochastic responses differ. Holdout v1 has already informed development.

| Metric | Pre-fix mixed Live | Post-fix pure DeepSeek |
|---|---:|---:|
| Overall Case Pass Rate | 45.00% (9/20) | 80.00% (16/20) |
| Calculation Accuracy | 84.21% (16/19) | 100.00% (19/19) |
| Workflow Path Accuracy | 55.00% (11/20) | 89.47% (17/19) |
| First-Level Driver Accuracy | 80.00% (8/10) | 88.89% (8/9) |
| Nested Driver Accuracy | 75.00% (3/4) | 50.00% (2/4) |
| Routing Validity | 100.00% (10/10) | 100.00% (17/17) |
| Evidence Coverage | 100.00% (48/48) | 100.00% (52/52) |
| Unsupported Claim Rate | 0.00% (0/48) | 0.00% (0/52) |
| Correct Stop Rate | 95.00% (19/20) | 100.00% (19/19) |
| Hard Constraint Violations | 0 | 0 |

Pass rate increased by 35 percentage points. Nested Driver Accuracy decreased from 3/4 to 2/4; this regression is retained, not hidden by the aggregate improvement. Calculation Accuracy measures existing applicable grader checks, not a universal proof of mathematical correctness. Changed denominators reflect one Intent rejection before Runtime. Required Claim Coverage remains N/A (0/0).

## RECOVERED CASES

### Pre-fix FAIL → Post-fix PASS

- `holdout_category_multi_driver_001`
- `holdout_channel_multi_driver_001`
- `holdout_channel_unknown_share_high_001`
- `holdout_dimension_zero_baseline_001`
- `holdout_explicit_category_intent_001`
- `holdout_explicit_channel_intent_001`
- `holdout_explicit_orders_category_illegal_001`
- `holdout_region_gmv_drilldown_001`

### Pre-fix FAIL → Post-fix FAIL

- `holdout_aov_price_down_units_offset_001`
- `holdout_evidence_boundary_channel_002`
- `holdout_requested_dimension_unavailable_001`

### Pre-fix PASS → Post-fix FAIL

- `holdout_orders_frequency_down_buyers_offset_001`

### Original 8 Offline PASS → Live FAIL cases

Recovered PASS: 7/8. Still FAIL: 1/8.

| Case | Post-fix |
|---|---|
| holdout_category_multi_driver_001 | PASS |
| holdout_channel_multi_driver_001 | PASS |
| holdout_channel_unknown_share_high_001 | PASS |
| holdout_dimension_zero_baseline_001 | PASS |
| holdout_evidence_boundary_channel_002 | FAIL |
| holdout_explicit_category_intent_001 | PASS |
| holdout_explicit_channel_intent_001 | PASS |
| holdout_explicit_orders_category_illegal_001 | PASS |

## REMAINING KNOWN ISSUES

| Category | Observed issue / boundary |
|---|---|
| Agent / Intent | `holdout_evidence_boundary_channel_002`: provider JSON succeeded, then local ValueError; parsed_input/result absent and no query executed. No misleading 0/0, but concrete Paid Search intent remains unresolved. Raw rejected response and precise exception message are not saved, so the exact rejected value cannot be established. |
| Agent / Intent | `holdout_orders_frequency_down_buyers_offset_001`: user asks whether orders changed due to fewer users or lower frequency. Parsed context adds preferred_dimension=customer_type; Runtime takes GMV×customer_type and stops at coverage rather than executing orders_buyers_frequency. This is the one new PASS→FAIL regression and explains the lost nested Driver check. No arithmetic error is demonstrated. |
| Agent / Intent | `holdout_requested_dimension_unavailable_001`: requested channel now preserved and filters empty; overall formulas run, but unavailable-channel disclosure is absent and allowed_statuses check fails. Actual warnings/limitations are empty, stop=evidence_boundary_reached. This run does not reproduce the earlier missing-string matcher false negative because no such disclosure exists here. |
| Eval / Expected | `holdout_aov_price_down_units_offset_001`: GMV 500→456 (-8.8%) does not meet frozen 10% anomaly threshold, so not_anomaly prevents the nested decomposition demanded by Expected. This known Case/Expected/policy inconsistency remains uncorrected. |
| Fixture | Existing synthetic fixtures reused unchanged. No new independently demonstrated construction defect; the aov_price numerical scenario matches Case but is incompatible with Expected deep-analysis demand under the frozen threshold. |
| Grader | All original graders preserved. Live Intent grading only checks explicit 渠道/品类/地区 in addition to target/periods/filters, so the spurious customer_type preference can still receive intent_correct=true while path/nested checks fail. Existing overall/subgrader presentation and text-matcher limitations are not repaired. |
| Provider | 43/43 transport/structured requests successful, no provider interruption. Local parsing rejection is not a provider failure. Single-run reliability is not a long-term guarantee. |
| Other | No evidence of a new systemic schema/runtime outage; one new semantic routing-scope regression exists. Holdout v1 is no longer unseen and cannot establish generalization. |

No fixes, Expected calibration or additional runs were performed after observing these issues.

## INTENT AND PATH OBSERVATIONS

Explicit channel/category/region cases now preserve their requested dimensions and execute the corresponding GMV dimension paths. Seven prior B-group cases recover; the Paid Search boundary case remains FAIL. All 19 accepted parsed inputs have filters={}; no dimension=all reached Runtime. The one rejected response is not available, so we cannot claim that the provider never generated all internally.

## PROVIDER RELIABILITY

| Metric | Value |
|---|---:|
| requests | 43 |
| successes | 43 |
| failures | 0 |
| 429 | 0 |
| 5xx | 0 |
| retries | 0 |
| fallbacks | 0 |

## PER-CASE TRACE INDEX

Each case is stored under the new run in `actual/<case_id>.json` and `cases/<case_id>.json`. The nested actual contains parsed_input, provider events, and the Runtime trace when execution reached Runtime. Case execution identity is the new Eval run ID plus case_id. No Runtime trace ID is invented for the rejected Intent.

| Case | Grade | preferred_dimension | Runtime run_id | stop_reason |
|---|---|---|---|---|
| holdout_aov_price_down_units_offset_001 | FAIL | N/A | 4f945152-a401-48fd-a8b7-0f964a3d868d | not_anomaly |
| holdout_aov_units_down_price_offset_001 | PASS | N/A | 69049b39-bbca-4e52-9e60-d4c2be875be8 | no_valid_dimension |
| holdout_category_multi_driver_001 | PASS | category | 2cdc3627-b00e-4535-8e87-0ee372220711 | target_coverage_reached |
| holdout_channel_multi_driver_001 | PASS | channel | 0732ef13-5bfb-4da0-ad22-a5b867e061fd | target_coverage_reached |
| holdout_channel_unknown_share_high_001 | PASS | channel | 8325dad1-6deb-450d-81d5-03e4ccc28a6c | target_coverage_reached |
| holdout_dimension_zero_baseline_001 | PASS | channel | beb57b99-22ee-4e8d-aab2-4e4abfe12e4f | target_coverage_reached |
| holdout_evidence_boundary_channel_002 | FAIL | N/A | N/A (Intent rejected) | N/A (ValueError) |
| holdout_explicit_category_intent_001 | PASS | category | e085ef31-041f-4fed-9b9e-cb6c54d61ae2 | target_coverage_reached |
| holdout_explicit_channel_intent_001 | PASS | channel | 9e4fd205-66f4-4f3d-8ba5-7a136037187e | target_coverage_reached |
| holdout_explicit_orders_category_illegal_001 | PASS | category | 3b816446-7b7f-461e-9516-766b58bed182 | target_coverage_reached |
| holdout_gmv_aov_down_orders_offset_001 | PASS | N/A | 165cbb6b-48f3-4d96-87cf-06f48e230f74 | no_valid_dimension |
| holdout_gmv_mixed_aov_primary_001 | PASS | N/A | 19d5eff3-299d-4f0c-aeee-3204146a88b7 | no_valid_dimension |
| holdout_gmv_mixed_orders_primary_001 | PASS | N/A | accd8f15-a9c8-4dcf-ba4f-6b40589a7e2e | evidence_boundary_reached |
| holdout_gmv_orders_down_aov_offset_001 | PASS | N/A | 97eb1f9b-ef8e-42d8-a2b6-41f9a8ea4026 | evidence_boundary_reached |
| holdout_no_anomaly_001 | PASS | N/A | 9fefafac-b479-4ec4-bfe0-b777294e833f | not_anomaly |
| holdout_orders_buyers_down_frequency_offset_001 | PASS | N/A | 2060e73f-4476-4d88-8e50-41efbe51a4b7 | target_coverage_reached |
| holdout_orders_frequency_down_buyers_offset_001 | FAIL | customer_type | 95ed592f-048d-4893-ad91-db472e1d502e | target_coverage_reached |
| holdout_region_gmv_drilldown_001 | PASS | region | 875612bb-370a-4b55-80ed-6275d3e6d336 | target_coverage_reached |
| holdout_requested_dimension_unavailable_001 | FAIL | channel | 5c023cb2-ffc2-48dd-b845-56079035c868 | evidence_boundary_reached |
| holdout_small_decline_below_threshold_001 | PASS | N/A | e9739b72-8454-4707-b2fa-fe9d65785677 | not_anomaly |

## INTEGRITY AND LEAKAGE

Expected leakage: PASS. The existing runner persisted all Actuals before opening Expected. Protected SHA-256 inventory in the run verifies Agent/specs/Eval code/Cases/Expected/fixtures and all earlier benchmarks/results unchanged. Exact post-fix source fingerprints are retained in closure_integrity.json. No software tests were rerun: this task changed no implementation. Prior software test outcomes are not represented as newly executed tests.

## PHASE 2 CLOSURE

**PHASE 2 EVAL: CLOSED**

Holdout v1 已用于诊断与修复，不再是真正未见的 Holdout；后续可作为 regression set。若未来要验证泛化能力，应另行创建 Holdout v2。本轮不创建 v2，不继续基于 Holdout v1 自动修复 Agent，不再运行 targeted regression，不开始下一阶段开发。Phase 2 以本次测量、归档和问题记录完成为结束条件，不以 100% PASS 为条件。
