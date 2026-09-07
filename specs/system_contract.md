# Business Performance Agent — Implementation Constraints v1.0

> **Status**: Frozen Baseline  
> **Scope**: MVP 基础 Agent 架构实现约束  
> **Purpose**: Runtime、数据访问与证据边界的实现契约  
> **Out of Scope**: Eval、真实业务数据接入、Reviewer Agent、Memory、RAG、Multi-Agent、自反思循环、自动业务执行

---

# 1. 总体架构约束

Agent 必须遵循以下分层：

```text
User / Trigger
      ↓
Intent Parsing
      ↓
Workflow Runtime
      ↓
Workflow
      ↓
Skills
      ↓
Knowledge
      ↓
Tools / Dataset Adapter
      ↓
Data Source
```

四个已有核心层定义保持不变：

```text
Knowledge → 定义业务事实与语义
Skill     → 定义可复用分析动作
Workflow  → 定义任务级编排与状态流转
Tool      → 执行具体数据读取、计算或外部操作
```

实现不得重新合并这些层，也不得将其中任意两层退化为一个 Prompt。

---

# 2. Knowledge Layer 硬约束

## 2.1 唯一业务语义真源

Knowledge 是以下内容的唯一真源：

- Metric 定义；
- Metric Formula；
- Metric Relationship；
- Dimension 定义；
- Metric × Dimension Contribution Applicability；
- Business Rules。

任何其它模块只能读取 Knowledge，不得修改。

---

## 2.2 稳定 ID

所有业务对象必须使用稳定 ID，例如：

```text
gross_gmv
net_gmv
orders
aov
buyers
customer_type
channel
orders_buyers_frequency
```

禁止在运行过程中由 LLM 创建新的：

- Metric ID；
- Dimension ID；
- Relationship ID；
- Business Rule。

---

## 2.3 Knowledge 不参与执行顺序

Knowledge 不得决定：

- 先分析哪个指标；
- 先下钻哪个维度；
- Workflow 什么时候停止；
- Skill 调用顺序。

这些均由 Workflow 负责。

---

## 2.4 已冻结业务规则不得被运行时覆盖

包括但不限于：

- GMV 按 `paid_at` 归属；
- `gross_gmv` 与 `net_gmv` 分离；
- New Buyer / Returning Buyer 使用周期级分类；
- `orders = sessions × orders_per_session`；
- `session_conversion_rate` 仅作为诊断指标；
- Category / Product 不允许直接对 Orders 做严格贡献归因；
- Unknown / Unattributed 不允许因方便展示而直接过滤；
- 分母为 0 的派生指标返回 `undefined`，不返回 0。

---

# 3. Skills Layer 硬约束

Skills 必须保持为可复用分析能力。

当前 Skills：

```text
metric_compare
anomaly_evaluate
metric_decompose
contribution_analysis
dimension_drilldown
data_quality_guard
evidence_validate
```

---

## 3.1 Skill 只完成单一分析动作

Skill 不得：

- 决定完整 Workflow；
- 自行开始下一步分析；
- 无限递归调用自己；
- 修改 Knowledge；
- 改写 Business Rule；
- 生成外部因果解释；
- 直接生成高影响业务动作。

---

## 3.2 Skill 输入输出必须结构化

Skill 之间不得依赖自然语言段落传递核心状态。

必须优先使用：

```json
{
  "status": "success",
  "result": {},
  "warnings": [],
  "limitations": []
}
```

自然语言仅用于：

- debug message；
- user-facing explanation；
- final report。

不得作为核心程序控制信号。

---

## 3.3 数值计算必须 deterministic

以下计算必须使用确定性代码完成：

- Metric value；
- Absolute Change；
- Relative Change；
- Multiplicative Contribution；
- Additive Contribution；
- Direction-Aligned Contribution；
- Closure Check；
- Ranking；
- Coverage；
- Threshold Comparison。

禁止让 LLM 心算或直接生成数值结果。

---

## 3.4 Contribution 必须满足合法性检查

执行 Contribution Analysis 前必须检查：

```text
Knowledge
→ Metric Relationship
或
→ Metric × Dimension contribution_support
```

如果不合法：

```json
{
  "status": "blocked",
  "reason": "non_additive_metric_dimension_pair"
}
```

不得降级为“近似贡献”。

---

# 4. Workflow Layer 硬约束

Workflow 是任务级状态机。

当前 MVP 核心 Workflow：

```text
gmv_diagnosis
```

---

## 4.1 Workflow 必须显式维护 State

不得仅依赖 LLM Conversation Context 保存分析进度。

至少维护：

```text
workflow_status
target_metric
current_period
baseline_period
current_node
current_metric
analysis_path
selected_relationship
selected_driver
selected_dimension
depth
evidence
warnings
limitations
stop_reason
```

State 是 Runtime 的正式数据结构。

---

## 4.2 Workflow 路由分两类

### Deterministic Routing

只要可由确定性条件判断，就必须程序化。

例如：

```text
是否异常
最大贡献 Driver
是否超过 max_depth
是否低于 min_contribution
是否达到 target_coverage
Skill 是否 blocked
```

### Agentic Routing

只有存在多个合法候选，且需要结合语义上下文选择时才能调用 LLM。

例如：

```text
Orders 使用哪一种合法 decomposition
下一步选择哪个合法 Dimension
```

---

## 4.3 Agentic Router 必须受候选集约束

LLM Router 的输入必须包含：

```json
{
  "allowed_candidates": []
}
```

LLM 只能选择其中一项，或者返回：

```text
no_valid_choice
```

禁止创建新路径。

---

## 4.4 唯一路径禁止调用 LLM

如果只有一个合法路径：

```text
AOV → aov_units_price
```

必须 deterministic 选择。

不得为了“Agent 感”额外调用 LLM。

---

## 4.5 Stop Policy 必须强制执行

Workflow 必须支持并执行：

```text
max_depth
branch_min_contribution
target_aligned_coverage
no_valid_relationship
no_valid_dimension
data_unavailable
data_quality_boundary
evidence_boundary_reached
semantic_conflict
execution_failure
```

LLM 不得覆盖 Stop Policy。

---

# 5. Runtime / Orchestrator 硬约束

系统使用一个薄 Runtime，用于执行 Workflow。

Runtime 核心职责：

```text
load workflow
→ initialize state
→ execute node
→ call skill
→ update state
→ evaluate route
→ move to next node
→ repeat
→ terminate
```

---

## 5.1 Runtime 不承担业务知识

Runtime 不得硬编码：

```text
GMV = Orders × AOV
```

这种内容。

Runtime 只读取：

- Workflow definition；
- Routing Rules；
- Policy；
- Skill Result；
- Knowledge。

---

## 5.2 Runtime 必须可替换 LLM Provider

LLM Client 必须通过抽象接口调用。

业务代码不得散落：

```python
client.responses.create(...)
```

应统一通过类似：

```python
llm_client.generate(...)
llm_client.structured_generate(...)
```

调用。

目的是避免 Workflow 与某个具体模型 SDK 强绑定。

---

## 5.3 Runtime 必须支持无 LLM 节点

绝大多数 Skill 与确定性 Node 应能在无 LLM 调用情况下正常执行。

---

# 6. LLM 职责硬约束

MVP 中 LLM 只允许承担三类职责。

## 6.1 Intent Parsing

将自然语言转换成结构化任务，例如：

```json
{
  "intent": "metric_diagnosis",
  "metric_id": "gross_gmv",
  "current_period": {},
  "baseline_period": {},
  "filters": {}
}
```

---

## 6.2 Constrained Routing

只在 Workflow 明确标记为 Agentic Router 的节点进行有限路径选择。

---

## 6.3 Final Language Rendering

将结构化 Workflow Result 转换成人类可读文本。

---

# 7. LLM 明确禁止事项

LLM 不得：

1. 自行定义指标；
2. 修改指标口径；
3. 自行计算核心数值；
4. 自行决定 Contribution；
5. 自行创建 SQL Schema；
6. 猜测真实数据库字段；
7. 创建 Knowledge 中不存在的 Relationship；
8. 创建 Knowledge 中不存在的 Dimension；
9. 绕过 Workflow Stop Policy；
10. 无限规划下一步；
11. 将内部贡献定位表述为外部因果；
12. 输出 Evidence 不支持的核心结论；
13. 直接执行强业务动作。

---

# 8. Tool Layer 硬约束

MVP Tool Layer 建议至少提供：

```text
Knowledge Loader
Schema Tool
Query Tool
Calculation Functions
```

---

## 8.1 Knowledge Loader

提供结构化读取接口，例如：

```text
get_metric(metric_id)
get_relationship(relationship_id)
get_metric_relationships(metric_id)
get_dimension(dimension_id)
get_business_rule(rule_id)
```

禁止把整个 Knowledge 文件无条件塞给 LLM 作为 Prompt。

---

## 8.2 Schema Tool

未来数据接入时至少支持：

```text
list_tables
get_table_schema
validate_field
```

当前无真实数据时允许提供 Interface / Mock Implementation。

---

## 8.3 Query Tool

当前阶段允许先做：

```text
QueryTool interface
MockQueryTool
```

不要求真实数据库接入。

未来真实实现必须默认 Read Only。

---

## 8.4 Calculation Layer

数值算法应以普通 Python 函数实现，而不是全部封装成 LLM Tool。

例如：

```text
relative_change()
symmetric_two_factor_decomposition()
additive_contribution()
direction_aligned_effect()
closure_check()
```

这些函数应可独立 unit test。

---

# 9. Data Contract / Dataset Adapter 硬约束

当前阶段不绑定真实 Dataset，但必须预留明确接口。

Dataset Adapter 负责：

> 将稳定业务语义 ID 映射到真实数据源。

未来应支持类似：

```json
{
  "dataset_id": "example",
  "semantic_mapping": {
    "order_id": "...",
    "customer_id": "...",
    "paid_at": "...",
    "merchandise_amount": "..."
  }
}
```

---

## 9.1 禁止业务层直接引用物理字段

例如 Skill 不应写：

```python
df["order_payment_timestamp"]
```

而应请求：

```text
semantic field: paid_at
```

由 Dataset Adapter 解析。

---

## 9.2 禁止 LLM 猜 Schema Mapping

字段映射不存在时：

```text
data_unavailable
```

或：

```text
semantic_mapping_missing
```

不得让模型根据字段名猜测后继续。

---

# 10. SQL / Data Access 安全约束

未来接入真实数据库后默认：

```text
READ ONLY
```

允许：

```sql
SELECT
WITH ... SELECT
```

禁止：

```sql
INSERT
UPDATE
DELETE
DROP
ALTER
CREATE
TRUNCATE
MERGE
```

应预留：

```text
query_timeout
max_rows
table_allowlist
column_allowlist
```

即使当前阶段只做 Mock，也应保留 Policy Interface。

---

# 11. Evidence 硬约束

每个关键结论必须绑定 Evidence。

Evidence Level：

```text
direct
derived
unsupported
```

---

## 11.1 Direct Evidence

由数据查询直接获得。

例如：

```text
Gross GMV WoW = -12%
```

---

## 11.2 Derived Evidence

由合法 Knowledge Relationship + deterministic calculation 得到。

例如：

```text
Orders Effect accounts for most of GMV decline.
```

---

## 11.3 Unsupported

没有足够内部证据。

例如：

```text
用户消费意愿下降
竞品增加投放
广告素材疲劳
```

---

## 11.4 Final Output Rule

核心 Claim：

```text
evidence_level ∈ {direct, derived}
```

才能进入最终报告。

Unsupported Claim 必须被：

```text
remove
或
明确标记为待人工验证假设
```

MVP 默认采用：

> **不允许 Unsupported Core Claim 进入最终报告。**

---

# 12. Causal Boundary

系统必须严格区分：

```text
Contribution Attribution
```

与：

```text
Causal Inference
```

允许：

> Paid Search 新客订单下降是本次 GMV 下跌的主要内部贡献来源。

不允许：

> Paid Search 下跌是因为竞品提高了广告竞价。

除非未来加入相应数据与明确因果分析能力。

---

# 13. Error / Failure Contract

模块失败不得统一抛给 LLM 自行处理。

建议统一状态：

```text
success
warning
blocked
failed
```

并包含：

```json
{
  "status": "blocked",
  "reason": "...",
  "warnings": [],
  "limitations": []
}
```

---

## 13.1 Retry

Skill / Tool transient failure：

```text
retry_limit = Workflow Policy
```

超过后停止当前分支。

---

## 13.2 Semantic Conflict

如果实际数据与 Knowledge 语义冲突：

```text
semantic_conflict
```

必须停止。

禁止运行时临时改定义。

---

## 13.3 Partial Completion

如果主路径已有可靠 Evidence，但次要路径失败：

允许：

```text
workflow_status = partial
```

并明确：

```text
failed_branches
limitations
```

---

# 14. Context 管理约束

MVP 不使用 Conversation Context 作为唯一系统状态。

必须区分：

```text
User Conversation Context
Workflow State
Knowledge
Execution Results
```

Workflow State 必须显式存在。

---

## 14.1 Prompt 最小化

LLM 每次调用只提供当前任务需要的信息。

禁止无条件把：

- 全部 Knowledge；
- 完整 Workflow 历史；
- 全部 SQL 结果；
- 所有历史对话；

全部塞入 Prompt。

---

# 15. Trace / Logging 基础约束

虽然 Eval 当前不做，但系统必须留下后续可评测的执行记录。

每次 Workflow Run 应有：

```text
run_id
```

至少记录：

```text
workflow_id
workflow_version
input
nodes_executed
skills_called
router_decisions
warnings
limitations
evidence
stop_reason
final_structured_result
```

当前可以使用本地 JSON 日志。

不要求引入外部 Observability 平台。

---

# 16. Reporting Boundary

Workflow 最终必须先产生结构化结果。

例如：

```json
{
  "workflow_status": "completed",
  "target": {},
  "primary_driver": {},
  "diagnostic_path": [],
  "key_findings": [],
  "evidence": [],
  "warnings": [],
  "limitations": [],
  "stop_reason": "evidence_boundary_reached"
}
```

然后 Report Generator 才负责自然语言表达。

禁止：

```text
Workflow内部一路生成自然语言
→ 最后没有结构化状态
```

---

# 17. MVP 明确不做

实现不得主动加入：

- Reviewer Agent；
- Multi-Agent；
- Long-term Memory；
- Vector Database；
- RAG；
- MCP；
- Autonomous Planning Loop；
- Self-reflection Loop；
- Automatic Business Action；
- Complex Permission System；
- Production Authentication；
- Distributed Runtime；
- Message Queue；
- Kubernetes / Microservices；
- 大型 Agent Framework，仅为了增加架构复杂度。

如实现基础 Runtime 不需要 LangGraph，则优先使用轻量自定义 Runtime。

---

# 18. Agent Framework 原则

允许使用第三方库，但：

> 第三方 Agent Framework 不得成为业务架构本身。

Knowledge / Skill / Workflow / State / Policy 的定义必须保持框架无关。

即使未来从：

```text
Custom Runtime
```

切换到：

```text
LangGraph
```

业务规范无需重写。

---

# 23. 核心不可违背原则摘要

以下原则优先级高于具体代码实现：

1. **Knowledge 是唯一业务语义真源。**
2. **业务层与物理数据 Schema 解耦。**
3. **Skill 单一职责。**
4. **Workflow 负责编排，不负责业务知识。**
5. **State 显式存在，不依赖对话记忆。**
6. **能 deterministic 就不调用 LLM。**
7. **LLM Router 只能从合法候选中选择。**
8. **所有核心数值计算 deterministic。**
9. **所有核心 Claim 必须有 Evidence。**
10. **Contribution 不等于 Causality。**
11. **达到 Evidence Boundary 必须停止。**
12. **禁止 Runtime 临时修改业务规则。**
13. **MVP 不增加未经定义的复杂 Agent 架构。**
14. **先保证可运行、可追踪、可替换，再追求更高自治程度。**
