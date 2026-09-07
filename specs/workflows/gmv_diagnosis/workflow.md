# Workflow: GMV Diagnosis

## 1. Identity

- **Workflow ID**: `gmv_diagnosis`
- **Version**: `1.0`
- **Status**: Frozen Baseline
- **Primary Target Metric**: `gross_gmv`

---

## 2. Purpose

用于对指定分析周期内的 Gross GMV 异常进行内部经营诊断。

Workflow 目标是回答：

1. GMV 是否确实发生异常；
2. GMV 变化主要由哪个数学 Driver 驱动；
3. Driver 的变化主要集中在哪些内部业务结构；
4. 当前数据可以可靠证明到哪一层；
5. 哪些问题已经超出内部数据证据边界。

Workflow 不负责解释：

- 竞争对手行为；
- 市场需求变化；
- 用户心理；
- 广告竞价变化；
- 供应链外部事件；

除非未来 Knowledge 与数据源明确支持。

---

## 3. Trigger

支持三种 Trigger。

### 3.1 User Trigger

例如：

```text
为什么本周 GMV 比上周下降？
```

### 3.2 Event Trigger

上层监控发现：

```text
anomaly_evaluate(gross_gmv).is_anomaly == true
```

### 3.3 Parent Workflow Trigger

例如：

```text
daily_business_inspection
→ gmv_diagnosis
```

---

## 4. Input Contract

```json
{
  "metric_id": "gross_gmv",
  "current_period": {
    "start": "YYYY-MM-DD",
    "end": "YYYY-MM-DD"
  },
  "baseline_period": {
    "start": "YYYY-MM-DD",
    "end": "YYYY-MM-DD"
  },
  "filters": {}
}
```

### Hard Constraints

- `metric_id` 第一版仅允许 `gross_gmv`。
- Current / Baseline 必须使用相同业务口径。
- 时间归属必须继承 Knowledge 中的 `paid_at` 规则。
- Workflow 不得自行改写 Metric Definition。

---

## 5. Core State

Workflow 必须维护：

```text
target_metric
current_period
baseline_period
current_node
analysis_path
current_metric
current_filters
available_relationships
selected_relationship
decomposition_result
contribution_result
selected_driver
selected_dimension
depth
aligned_coverage
evidence
warnings
limitations
retry_count
stop_reason
workflow_status
```

正式字段定义见：

`state_schema.json`

---

# 6. Node Types

Workflow 节点分三类。

## 6.1 Skill Node

调用已有 Skill，例如：

```text
data_quality_guard
metric_compare
anomaly_evaluate
metric_decompose
contribution_analysis
dimension_drilldown
evidence_validate
```

## 6.2 Deterministic Node

使用程序化规则做判断，例如：

```text
select_largest_aligned_driver
check_max_depth
check_min_contribution
check_target_coverage
```

## 6.3 Agentic Router Node

仅在存在多条合法业务路径且无法仅靠数值规则决定时使用。

例如：

```text
select_next_relationship
select_next_dimension
```

Agentic Router 必须从 Knowledge / Routing Rules 给定的候选项中选择，不得创造新路径。

---

# 7. Main Workflow

```text
START
  │
  ↓
validate_input
  │
  ↓
data_quality_guard
  │
  ├── blocked → TERMINATE_BLOCKED
  │
  ↓
metric_compare(gross_gmv)
  │
  ↓
anomaly_evaluate
  │
  ├── not_anomaly → COMPLETE_NO_ANOMALY
  │
  ↓
metric_decompose
relationship = gross_gmv_orders_aov
  │
  ↓
contribution_analysis
  │
  ↓
select_primary_driver
  │
  ↓
evaluate_driver_branch
  │
  ├── stop → evidence_validate
  │
  └── continue
         ↓
   select_next_relationship
         ↓
   metric_decompose
         ↓
   contribution_analysis
         ↓
   evaluate_branch
         │
         ├── stop
         │
         └── continue
                ↓
        select_next_dimension
                ↓
        dimension_drilldown
                ↓
        [if contribution_supported]
        contribution_analysis
                ↓
        evaluate_stop_policy
                │
          ┌─────┴─────┐
          │           │
       continue      stop
          │           │
          └── loop ───┘
                      ↓
              evidence_validate
                      ↓
                 build_result
                      ↓
                    COMPLETE
```

---

# 8. Step Definitions

## Step 1 — validate_input

检查：

- metric_id 是否允许；
- Current / Baseline 是否完整；
- 时间顺序是否有效；
- Filters 是否可以解析。

失败：

```text
TERMINATE_INVALID_INPUT
```

---

## Step 2 — data_quality_guard

必须在任何业务诊断之前执行。

调用：

```text
Skill: data_quality_guard
```

结果：

### `blocked`

停止 Workflow。

### `warning`

允许继续，但：

```text
state.warnings
state.limitations
```

必须继承到最终 Output。

### `success`

继续。

---

## Step 3 — metric_compare

调用：

```text
metric_compare(gross_gmv)
```

得到：

```text
current_value
baseline_value
absolute_change
relative_change
```

记录为 Direct Evidence。

---

## Step 4 — anomaly_evaluate

调用：

```text
anomaly_evaluate
```

异常 Policy 从 `policy.json` 获取。

### 非异常

结束：

```text
workflow_status = completed_no_anomaly
```

### 异常

进入 GMV Driver 分解。

---

# 9. GMV First-Level Decomposition

第一层 Relationship 固定：

```text
gross_gmv_orders_aov
```

即：

\[
GrossGMV = Orders \times AOV
\]

Workflow 第一层不允许 Agentic Router 选择其它 Relationship。

调用：

```text
metric_decompose
↓
contribution_analysis
```

获得：

```text
Orders Effect
AOV Effect
```

---

# 10. Primary Driver Selection

第一层采用 Deterministic Rule。

优先选择：

```text
absolute aligned effect 最大
```

的 Driver。

如果多个 Driver 均达到 `branch_min_contribution`，Workflow 可以保留多个 Active Branch，但 MVP：

> 默认优先深入最大主驱动，同时将其它显著 Driver 作为 Secondary Finding 保存。

---

# 11. Orders Branch

Knowledge 当前允许：

```text
orders_buyers_frequency
orders_new_returning
orders_sessions_rate
```

## Default Relationship

对于普通整体 GMV 异常：

```text
orders_buyers_frequency
```

优先。

目的：

> 区分购买用户数量变化与人均购买频率变化。

## Agentic Relationship Selection

当满足以下情形之一时，可以选择其它合法 Relationship：

### User / Parent Context 明确要求新老客结构

候选：

```text
orders_new_returning
```

### Session Data 可用且当前问题需要流量视角

候选：

```text
orders_sessions_rate
```

### 已有 Evidence 表明 Customer Structure 是关键

候选：

```text
orders_new_returning
```

Agentic Router 只能从：

```text
routing_rules.json
```

允许的候选 Relationship 中选择。

---

# 12. AOV Branch

当前合法 Relationship：

```text
aov_units_price
```

即：

\[
AOV =
UnitsPerOrder
\times
AverageRealizedUnitPrice
\]

当前没有其它 AOV 数学拆分路线，因此无需 Agentic Router。

---

# 13. Dimension Drill-down

只有在：

- 已找到显著 Driver；
- 当前 Driver 仍存在值得解释的剩余变化；
- Knowledge 存在合法 Dimension；

时允许进入。

## Candidate Dimensions

来自：

`dimensions.json`

Workflow 不写死业务事实，只维护合法选择策略。

---

## 13.1 Contribution-Supported Dimension

例如：

```text
orders × channel
gross_gmv × category
```

如果 Knowledge 标记支持：

```text
contribution_support = true
```

流程：

```text
dimension_drilldown
→ contribution_analysis
→ rank aligned contributors
```

---

## 13.2 Non-Additive Dimension

例如：

```text
orders × category
orders × product
```

允许：

```text
descriptive drilldown
```

但禁止：

```text
strict contribution share
```

Workflow 必须保留 limitation。

---

# 14. Stop Policy

每次分解或下钻后都必须执行：

```text
evaluate_stop_policy
```

停止条件如下。

## 14.1 Maximum Depth

```text
depth >= max_depth
```

停止。

---

## 14.2 Minimum Contribution

当前分支：

```text
aligned_contribution < branch_min_contribution
```

停止继续下钻该分支。

---

## 14.3 Target Coverage

Top aligned contributors 已覆盖：

```text
>= target_aligned_coverage
```

时，可以停止横向继续搜索低贡献因素。

---

## 14.4 No Valid Relationship

Knowledge 中没有合法下一层 decomposition。

停止。

---

## 14.5 No Valid Dimension

没有适合当前 Metric 的合法 Dimension。

停止。

---

## 14.6 Data Unavailable

下一步需要的 Metric / Dimension 数据 unavailable。

停止当前分支并记录 limitation。

---

## 14.7 Data Quality Boundary

当前层数据质量已不足以支撑可靠继续分析。

停止。

---

## 14.8 Evidence Boundary

进一步解释已经需要 Knowledge / 当前数据之外的信息。

停止并记录：

```text
stop_reason = evidence_boundary_reached
```

---

# 15. Failure Handling

## 15.1 Skill Execution Failure

```text
skill_failed
↓
retry
↓
still_failed
↓
terminate_current_branch
```

重试次数由：

```text
policy.retry_limit
```

决定。

---

## 15.2 Semantic Conflict

如果 Skill / Dataset 与 Knowledge 定义冲突：

```text
semantic_conflict
```

必须停止相关分析路径。

Workflow 不允许临时修改 Metric Definition。

---

## 15.3 Partial Completion

如果部分分支失败，但已有主路径证据完整：

```text
workflow_status = partial
```

允许输出已有可靠结果，同时明确：

```text
limitations
failed_branches
```

---

# 16. Evidence Management

每个关键 Step 必须产生 Evidence Reference。

例如：

```text
E001: Gross GMV WoW = -12%
E002: Orders Effect = -105000
E003: AOV Effect = -15000
E004: Paid Search Orders Δ = ...
```

Evidence 分三类：

```text
direct
derived
unsupported
```

最终核心 Claim 必须通过：

```text
evidence_validate
```

---

# 17. Output

Workflow 不直接以自由文本作为唯一结果。

必须首先生成结构化 Output。

正式 Schema：

```text
output_schema.json
```

至少包含：

```text
workflow_status
target_metric
target_change
primary_driver
secondary_drivers
diagnostic_path
key_findings
evidence
warnings
limitations
stop_reason
```

自然语言日报 / 诊断报告属于后续 Presentation / Reporting Layer。

---

# 18. Workflow Boundaries

GMV Diagnosis Workflow 可以输出：

> Gross GMV 下降 12%。

> Orders 是主要数学驱动。

> 新客订单下降是主要结构因素。

> Paid Search 是主要内部贡献来源。

不允许在没有数据证据时进一步输出：

> 竞品提高了广告竞价。

> 用户需求疲软。

> 素材质量下降。

> 建议立即增加 20% 投放预算。

---

# 19. MVP Success Definition

一次 GMV Diagnosis Workflow 被视为成功，不要求找到“现实世界最终原因”。

成功标准是：

1. 正确确认异常；
2. 正确完成数学分解；
3. 找到主要内部变化来源；
4. 所有核心 Claim 有 Direct / Derived Evidence；
5. 在内部数据证据边界处正确停止；
6. 明确指出仍需人工验证的问题。

最终目标：

> **找到当前数据系统能够可靠证明的最深层变化来源，而不是强行生成完整商业故事。**
