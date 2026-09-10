# Evaluation and reliability

本页摘要来自冻结历史，Phase 4 未重跑 Eval 或调用模型。软件测试、合成场景 Eval、Provider 请求成功和真实数据 E2E 是不同证据，不能互相替代。

## Evaluation history

| 阶段 | 实际结果 | 解读 |
|---|---|---|
| Golden Round 1 → 2 → 3 | 4 PASS / 3 FAIL / 5 review → 9/12 PASS → 12/12 PASS | 校准与最小维度编排修复后的回归结果 |
| Holdout v1 offline，Round 4 | 13/20 PASS | Mock 运行，不能代表真实 LLM 意图质量 |
| Gemini provider-limited，Round 5 | 3 attempted，2 completed：1 PASS / 1 FAIL；17 not run | Provider 故障不能算业务评测通过 |
| Mixed Live，Round 6 | 9/20 PASS | 2 个 Gemini + 18 个 DeepSeek 场景，不是纯 DeepSeek 基准 |
| Post-fix DeepSeek，Round 7 | 16/20 PASS | 19 个 Workflow Result，1 个本地 Intent 拒绝仍计 FAIL |

[完整历史](../../evals/BENCHMARK_HISTORY.md) · [冻结回归结果](../../evals/benchmarks/round_07_post_intent_fix_deepseek_closure/summary.json) · [Round 7 原始指标](../../evals/benchmarks/round_07_post_intent_fix_deepseek_closure/summary.json)

**Holdout v1 已用于分析和修复，现为 regression set；不是严格未见 Holdout。** 45% → 80% 是不同 Provider 构成、不同随机响应下的前后观察，不能仅归因于修复，更不能证明泛化。

## Post-fix applicable checks

| 指标 | 分子 / 分母 | 比例 |
|---|---|---|
| Case pass | 16/20 | 80% |
| Calculation Accuracy | 19/19 | 100% |
| Workflow Path Accuracy | 17/19 | 89.47% |
| First-Level Driver Accuracy | 8/9 | 88.89% |
| Nested Driver Accuracy | 2/4 | 50% |
| Routing Validity | 17/17 | 100% |
| Evidence Coverage | 52/52 | 100% |
| Unsupported Claim Rate | 0/52 | 0% |
| Correct Stop Rate | 19/19 | 100% |
| Hard Constraint Violations | 0 | count |
| Required Claim Coverage | 0/0 | N/A |

统计只覆盖现有 grader 的适用检查。合法路由不等于满足用户意图；Evidence 引用覆盖不证明外部因果。嵌套 Driver 从上一轮 3/4 降为 2/4，不能被整体通过率掩盖。

## Remaining failures

- `holdout_aov_price_down_units_offset_001`：-8.8% 未达到冻结的 10% 异常阈值，Expected 却要求更深拆解，保留规范/预期不一致。
- `holdout_evidence_boundary_channel_002`：本地 Intent 校验拒绝，未查询数据；未保存被拒绝原始响应，不能断言具体错误值。
- `holdout_orders_frequency_down_buyers_offset_001`：额外 customer_type 偏好使路径偏离订单买家/频次分析，是新增回归。
- `holdout_requested_dimension_unavailable_001`：当轮缺少不可用维度披露。Phase 3 新数据能力入场检查已验证真实 channel 的安全停止，但**没有重跑此回归 Case**，不能改写其历史 FAIL。

## Provider reliability

Gemini 早期限定运行共 9 请求：2 成功、7 失败（429 两次、5xx 五次），4 次 retry、2 次报告 fallback。Round 7 DeepSeek 为 43/43 请求成功、无 retry/fallback；本地 Intent 拒绝仍是 Agent 失败。请求成功率不是业务准确率，也不是长期 SLA。

实现保留有限重试，报告失败只从已存在结果确定性渲染；不会为失败的意图/路由编造分析。

## Real-data E2E

Complete Journey 四场景分别以 Mock 和 DeepSeek 执行，保存结果均通过场景预定行为检查；其中 root 为 partial，channel 为 blocked。Live 共 7 次请求成功、0 retry。它们验证真实数据链路和能力边界，不是新的 20-case benchmark。[真实数据证据](../../examples/real_data/completejourney/portfolio.md) · [真实数据契约与验证](../COMPLETEJOURNEY.md)。
