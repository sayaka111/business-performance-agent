# Skill: contribution_analysis

## Purpose

计算 Driver 或互斥 Segment 对目标指标变化的贡献，并区分“推动目标变化”和“抵消目标变化”。

## Input Contract

```json
{
  "target_metric": "gross_gmv",
  "target_baseline": 1000000,
  "target_current": 880000,
  "relationship_type": "exact_multiplicative",
  "components": []
}
```

## Knowledge Dependencies

- `metric_relationships.json`
- `dimensions.json`
- `business_rules.json`

## Mode A — Two-driver Exact Multiplicative

对于：

\[
Y = A \times B
\]

使用对称分解：

\[
Effect_A = (A_1-A_0) \times \frac{B_0+B_1}{2}
\]

\[
Effect_B = (B_1-B_0) \times \frac{A_0+A_1}{2}
\]

满足：

\[
Effect_A + Effect_B = \Delta Y
\]

第一版仅保证 **two-driver exact multiplicative** 的严格实现；更高阶乘法关系以后单独扩展算法。

## Mode B — Exact Additive / Partition

对于：

\[
Y = \sum c_i X_i
\]

计算：

\[
Effect_i = c_i(X_{i,1}-X_{i,0})
\]

并检查 Effect Sum 是否闭合至目标变化。

## Mode C — Dimension Contribution

只有 `dimensions.json` 明确：

```json
{"contribution_support": {"<metric_id>": true}}
```

时允许计算严格贡献。

否则返回：

```json
{
  "status": "blocked",
  "reason": "non_additive_metric_dimension_pair"
}
```

## Direction-Aligned Contribution

定义目标变化方向：

```text
target_direction = sign(target_current - target_baseline)
```

若：

```text
target_direction × effect_i > 0
```

则该因素推动了当前目标变化。

若小于 0，则该因素属于 Offset。

## Output Contract

```json
{
  "status": "success",
  "target_change": -120000,
  "effects": [
    {
      "id": "orders",
      "effect": -105000,
      "role": "aligned_driver"
    },
    {
      "id": "aov",
      "effect": -15000,
      "role": "aligned_driver"
    }
  ],
  "closure_error": 0,
  "warnings": [],
  "limitations": []
}
```

## Boundaries

不负责：

- 选择哪个 Relationship；
- 选择哪个 Dimension；
- 设定 Top Coverage / Stop Threshold；
- 将贡献解释为外部因果。
