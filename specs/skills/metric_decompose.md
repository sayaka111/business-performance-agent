# Skill: metric_decompose

## Purpose

读取 Knowledge 中某个指标的合法 decomposition relationship，并返回对应 Driver / Component 数据。

## Input Contract

```json
{
  "metric_id": "gross_gmv",
  "relationship_id": "gross_gmv_orders_aov",
  "current_period": {},
  "baseline_period": {},
  "filters": {}
}
```

`relationship_id` 可以由 Workflow 显式指定。

若未指定且存在多种合法 decomposition，本 Skill 只返回可用关系，不自行决定分析路线。

## Knowledge Dependencies

- `metrics.json`
- `metric_relationships.json`
- `business_rules.json`

## Process

1. 查询目标指标的合法 Relationships。
2. 验证指定 Relationship 是否适用于当前数据。
3. 获取各 Driver / Component 的 Current 与 Baseline。
4. 返回结构化 decomposition data。
5. 不在本 Skill 内判断“谁是主驱动”。

## Output Contract

```json
{
  "status": "success",
  "target_metric": "gross_gmv",
  "relationship": {
    "id": "gross_gmv_orders_aov",
    "type": "exact_multiplicative"
  },
  "drivers": [
    {"metric_id": "orders", "baseline": 10000, "current": 9000},
    {"metric_id": "aov", "baseline": 100, "current": 97.78}
  ],
  "warnings": [],
  "limitations": []
}
```

## Boundaries

不负责：

- 自主决定采用哪套 decomposition；
- 计算最终 Driver Contribution；
- 决定是否继续拆解；
- 决定下一步 Dimension。
