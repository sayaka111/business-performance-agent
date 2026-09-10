# Offline Agent Eval v1

本目录用于评测当前 Agent 行为，独立于验证软件正确性的 `tests/`。Golden Set 包含 12 个场景；Case 失败不会触发 Agent 自动修复，也不意味着框架运行失败。

## Golden Set 与边界

- `cases/` 保存用户问题、周期、`fixture_spec` 和评测关注点。
- `expected/` 保存数值、关键路径、Driver、禁止声明与允许停止原因。
- `manifest.json` 只索引文件，不把 Expected 内容交给 Agent。
- Product、Knowledge、Skills、Workflow、Routing、Stop Policy 和贡献公式保持冻结。

当前 Golden 有 12 个场景；另有 20 个已暴露的 v1 回归场景。不可构造的新 Case 应进入 review，不能以 Expected 补造数据。历史校准与残留问题见 [评测概览](../docs/portfolio/evaluation.md)。

## Fixture generation

`support/case_fixture.py` 从 **fixture_spec.description** 的 v1 限定语法提取数值，调用通用 `support/fixture_builder.py`。支持 Orders/AOV、Buyers/Orders、件数/成交单价、品类金额、渠道金额、跨品类订单、零基期以及支付时间缺失场景。

这是确定性构造器，不是通用自然语言规划器。不能解析的新描述或无法满足的数学约束进入 review；不会根据 Expected 补全。当前 `construction_requirements` 的边界通过构造与软件测试验证，新增描述需同时扩展构造规则及测试，不能假定任意文字要求都被自动解释。

生成文件：

```text
fixtures/<case_id>.db
fixtures/<case_id>.mapping.json
```

Case ID 仅用于外部文件索引，不用于业务记录、SQL、模型输入或 Agent 分支。相同约束生成相同数据库字节；已有同名 fixture 相同时复用，不同时拒绝覆盖，修改 Case 后使用新的 `--fixture-dir`。

Canonical 字段见 [canonical_mapping.json](support/canonical_mapping.json)。`customer_type` 从稳定客户身份、首购日期与分析周期派生。数据是订单明细记录，不是答案列。构造器真实生成跨品类订单；缺失时间场景的 paid_at/首购时间为 null，并提供未映射的 created_at/delivered_at 干扰列；零基期没有基期有效记录；证据边界场景没有外部广告因果字段。

## Offline execution

先在源码根目录完成 `python -m pip install -e .`，然后：

```bash
python -m evals.runner --mode offline
```

可选参数：`--manifest PATH`、`--fixture-dir PATH`、`--results-dir PATH`。只支持 offline，不提供 live provider 开关，不需要 Key。

Case 的用户问题被确定性转为结构化输入：显式 GMV/订单量/客单价决定目标，显式渠道/品类决定 `preferred_dimension`。这一步只适用于当前问题词汇，不评测自然语言模型质量。不会从 evaluation_focus 或 Expected 注入路线，不强迫 Runtime 执行某个 Skill，不把不支持的目标偷偷替换为 GMV。

每个 Case 调用原有 Runtime、MockLLMClient 和通用 SQLite Adapter。子进程超时 60 秒。某 Case 的框架错误或行为失败被记录后，继续其它 Cases。

退出码：0 为所有 Case 通过；1 为存在行为失败或 review；2 为存在框架执行/评分错误。判断结果请读 summary，不要只看退出码。

## Expected leakage protection

执行分两个阶段：

```text
所有 Cases -> fixtures -> 所有 Agent executions -> Actual checkpoints
                                                      |
                                    ExpectedGate 开放读取
                                                      |
                                         Expected -> graders
```

每次 Agent 执行在匿名临时目录进行，只复制 Agent 源码、冻结 specs、`data.db`、`mapping.json` 和结构化 `input.json`。不复制 Cases、Expected、manifest、构造规则或 graders，不传入 Case ID。

子进程使用隔离模式；审计钩子拒绝读取/列举目录边界之外的文件，拒绝外部 SQLite 连接、网络与新子进程。密钥类环境变量被移除，LLM 固定为 Mock。这是针对受信任项目代码的评测隔离机制，不宣称是防恶意原生代码的 OS sandbox。

Actual 先持久化；ExpectedGate 必须确认全部执行阶段终止，并存在已完成 Actual，才可读相应 Expected。不可构造的 Case 不加载 Expected 评分业务行为，仅生成 review 记录。Agent Trace 内不含 Expected 或 Case ID；Case 级索引位于外部结果封装中。

## Deterministic graders

| Grader | 检查内容 |
|---|---|
| CalculationGrader | 已观测值、变化率、乘法/加法贡献、闭合与零分母；绝对及相对容差 1e-7 |
| WorkflowPathGrader | 目标、必需/禁止关系、带 Metric scope 的关键维度、状态；不要求内部节点逐个一致 |
| PrimaryDriverGrader | 第一层数学 Driver 与要求的维度 Driver，不能跨指标复用 Effect |
| ConstraintGrader | 合法候选、Knowledge 贡献适用性、禁止关系、支付时间和数值边界 |
| EvidenceGrader | direct/derived 引用、必需声明、禁止声明、归一化匹配与明确否定识别 |
| StopGrader | Expected 的 allowed_stop_reasons、状态和实际阈值条件 |
| OverallCaseGrader | 所有适用检查通过且无 hard violation、无 review 才通过 |

数值参考检查独立实现，不调用 Agent 的计算函数。缺失观测不从 Expected 或重新取数中补齐。Claim 匹配依赖结构化事实和有限文本规则，不使用 LLM-as-a-Judge；不能覆盖所有自然语言同义表达。未支持的 required claim 匹配需要 review。

## Metrics

每个比例同时保存 numerator、denominator、value。分母为 0 时为 null/N/A，绝不视为 100%。

- Overall Case Pass Rate：通过数 / 全部加载数，review 不算通过。
- Calculation / Workflow Path / Primary Driver Accuracy / Correct Stop Rate：对应 Grader 通过的 Case / 可评且适用的 Case。review 排除在组件准确率分母外。
- Routing Validity：合法候选选择 / 已观测候选选择，不等同于路径是否满足 Expected。
- Evidence Coverage：有 direct/derived 引用的输出核心 Claim / 输出核心 Claim。
- Unsupported Claim Rate：缺少合格引用的输出核心 Claim / 输出核心 Claim。此值不是通用语义真实性证明。
- Required Claim Coverage：满足的必需声明 / Expected 中的必需声明，单独显示遗漏的解释。
- Hard Constraint Violation Count：失败的硬约束检查、unsupported 核心 Claim 和禁止声明检查数。

仅记录结果中实际输出的声明；没有输出某个必需 Claim 会失败，不能用高 Evidence Coverage 掩盖该遗漏。

## Results

```text
results/<run_id>/
├── actual/                  # 在加载 Expected 前写入
├── cases/<case_id>.json     # Actual、graders、failures、review、生命周期
├── summary.json
└── summary.md
```

每个 Case 区分 execution_status、grading_status、overall_pass 和 review_required。Agent 自身的 blocked/partial/completed 状态保留在 actual.result，不把“成功运行”混同于“通过 Case”。

生成的数据库、映射和每次运行结果被 Git 忽略，源码包排除这些产物。结果报告需要展示时再人工选择。Runner 不提交 Git、不调用真实服务、不修复 Agent。

## Adding cases and software tests

新增 Case 与 Expected 分开保存并更新 manifest；先确保描述可确定性构造、数值符合冻结语义，再为新增构造/Grader 能力写软件测试。不得新增按 Case ID 执行的 Agent 分支。

```bash
python -m unittest tests.test_eval_framework -v
python -m unittest discover -s tests -v
```

软件测试验证构造重复性、物理边界、Grader 正反例、ExpectedGate、子进程隔离、发现全部 Case 和失败后继续。它们不要求 Golden Set 全部通过。


## Regression set and frozen evidence

`manifest.json` indexes the 12 Golden cases; `holdout_manifest.json` indexes the separate 20-case v1 set. The latter has informed development and is now an exposed regression set, not unseen validation. [Results and limitations](../docs/portfolio/evaluation.md) are the primary reading path.

[Selected benchmark history](BENCHMARK_HISTORY.md) retains seven small frozen snapshots, including failures and provider interruptions, to substantiate pre/post observations. Their JSON, metadata hashes and associated reports remain byte-for-byte unchanged. They are summaries, not redistributed full transient runs. `evals/results/` remains ignored. No benchmark rerun is needed to read the evidence.

The optional `holdout_runner`, `live_runner` and `continue_live` modules remain for reproducibility. Real provider execution requires explicit opt-in and keys; it is not part of Quick Start or CI. Use each module's `--help` for current arguments. Expected is opened only after Actual persistence. Do not use repeated runs to relabel the existing set as unseen.
