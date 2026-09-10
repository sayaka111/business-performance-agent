# Frozen benchmark index

Start with [evaluation and known failures](../docs/portfolio/evaluation.md). These small snapshots retain the evidence behind the published observations; they are not instructions to rerun or tune the Agent.

| Snapshot | Purpose | Result |
|---|---|---|
| [Round 1](benchmarks/round_01_golden_set_calibration/summary.json) | Golden calibration | 4 PASS / 3 FAIL / 5 review |
| [Round 2](benchmarks/round_02_pre_fix_baseline/summary.json) | Golden pre-fix | 9/12 PASS |
| [Round 3](benchmarks/round_03_post_dimension_fix/summary.json) | Golden post-fix | 12/12 PASS |
| [Round 4](benchmarks/round_04_holdout_offline_baseline/summary.json) | v1 offline | 13/20 PASS |
| [Round 5](benchmarks/round_05_holdout_live_provider_limited/summary.json) | Provider-limited Live | 1 PASS / 1 FAIL / 1 interrupted / 17 not run |
| [Round 6](benchmarks/round_06_mixed_provider_live_completion/summary.json) | Mixed Gemini / DeepSeek | 9/20 PASS |
| [Round 7](benchmarks/round_07_post_intent_fix_deepseek_closure/summary.json) | Post-fix DeepSeek | 16/20 PASS |

Each directory retains its original JSON, metadata hashes and associated summary/failure records unchanged. The archive helper refuses overwrites. Missing historical commit identifiers remain null; archive timestamps are not asserted to be original execution times. These are sanitized summary records, not all original transient traces.

Holdout v1 has informed fixes and is now an exposed regression set. Mixed-provider pre-fix and pure DeepSeek post-fix observations are not a controlled model comparison. Failures, provider interruptions and denominator limitations remain visible. Generated `evals/results/` is local and ignored.
