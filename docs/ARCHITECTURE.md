# Architecture

Business Performance Agent 是独立 Python 功能原型。`specs/` 定义业务契约，`business_performance_agent/` 执行契约；CLI 和 Codex 操作层调用同一个 Runtime。

## Separation of responsibilities

| 层 | 职责 | 边界 |
|---|---|---|
| Knowledge | 指标、公式、关系、维度和业务规则 | 唯一语义真源，不定义执行顺序 |
| Skill | 可复用的单一分析动作 | 不发起下一步、不修改 Knowledge |
| Workflow | 任务编排、状态流转和停止策略 | 不重新定义指标或贡献算法 |
| Tool / Adapter | 读取、计算和 Semantic ID 映射 | 不让 LLM 猜物理 Schema |

Settings 统一解析 `specs/knowledge` 与 `specs/workflows/gmv_diagnosis`。KnowledgeLoader 读取 JSON、校验稳定 ID 引用并向调用者返回副本；Workflow Loader 读取 Markdown、State、Routing、Policy 和 Output Schema。二者保留文件指纹供 Trace 和不可变性测试检查。

## Explicit workflow state

Runtime 执行加载、初始化、节点调用、状态更新、路由、终止循环。正式 State 包含状态、目标/当前指标、周期、当前节点、分析路径、关系、Driver、Dimension、深度、Evidence、警告、限制和停止原因。

Workflow JSON 为描述性 Schema；代码按其结构校验，不将其冒充通用 JSON Schema。Markdown 中的顺序节点与 Routing JSON 一起定义执行流程。

根节点和每个新增分析范围执行 Data Quality Guard。Semantic conflict 立即停止；暂时性失败按 Policy 有限重试；已有可靠证据而次要分支失败时允许 partial，并保存 failed_branches。

## Deterministic analysis and routing

变化、乘法/加法贡献、方向对齐、排序、覆盖率和阈值比较均由普通 Python 函数完成。两因子乘法分解采用对称分配；带符号 coefficient 的加法按关系执行。两个周期的总量和变化量都必须闭合；数值容差用于浮点误差，不用于容忍语义冲突。零分母产生 undefined，在 JSON 中表示为 null。

同向份额为 `abs(effect) / sum(abs(aligned effects))`；offset 不进入该分母。并列项按 ID 排序。份额属于当前分析层，不自动相乘为跨层 GMV 总贡献。深度按实际 decomposition / dimension drilldown 动作递增。

最大 Driver、是否异常、深度/贡献/覆盖率阈值均使用确定性路由。多个合法候选且 Workflow 允许时，ConstrainedRouter 才调用模型，传入 allowed_candidates；返回只能是其中一项或 no_valid_choice。唯一候选直接选定。无 Provider 时不自由选路，保留 llm_provider_not_configured 的真实停止原因。

## Contribution applicability

贡献计算前检查 Knowledge 中的 Relationship 或 Metric × Dimension contribution_support。Orders × Category / Product 非可加，严格贡献返回 blocked；维度下钻只能提供描述性比较。Unknown / Unattributed 保留，避免人为丢失贡献和破坏闭合。

GMV 按 paid_at 归属；gross_gmv 与 net_gmv 分离；新老客按分析周期分类；流量关系为 orders = sessions × orders_per_session，session_conversion_rate 仅为诊断指标。这些定义从 Knowledge 读取。

## Evidence and reporting

查询产生 direct Evidence；合法关系与确定性计算产生 derived Evidence。Evidence Validator 核对 Claim 的事实、范围和引用，unsupported 核心 Claim 不进入最终结果。Report Generator 先接收合规结构化结果，再表达已经验证的 Claim；越界模型输出回退到认可文本。

内部贡献定位不能证明外部因果。系统可以指出 Orders 对 GMV 下降的贡献，不能由此推断竞品竞价、用户意愿或市场变化。Evidence Boundary 和 Stop Policy 对模型同样有效。

## Data adapters and trace

Skill 使用稳定 Semantic ID；QueryTool 通过 DatasetAdapter 访问物理字段。缺少映射即阻断，不猜字段。当前仅有 MockDatasetAdapter / MockQueryTool；只读接口预留 query_timeout、max_rows、table_allowlist、column_allowlist。现有 SQL 检查是保守只读校验，不等于生产数据库权限或取消机制。

每次运行生成 run_id 和本地 JSON Trace，包含 Workflow 版本、输入、节点快照、Skill 调用、路由决策、Evidence、限制、停止原因与最终结果。Trace 运行时生成，Git 不收录。公开 examples 是单独标注的 synthetic 快照，不携带个人路径或随机运行日志。

## Interfaces and extension boundaries

LLM 仅有 Intent Parsing、Constrained Routing、Final Rendering 三个职责。当前 MockLLMClient 是离线接口替身，不具有真实语义推理能力。核心运行不依赖第三方 Agent Framework。

运行契约见 [system contract](../specs/system_contract.md)，业务目标见 [product scope](../specs/product_scope.md)。将来可替换 Provider / Adapter，但不能更改 Knowledge、放宽贡献合法性或用无证据解释填补失败分支。
