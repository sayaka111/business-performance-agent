# Skill: metric_compare

## Purpose

比较同一指标在 Current Period 与 Baseline Period 的表现，只回答“指标变了多少”。

## Input Contract

```json
{
  "metric_id": "gross_gmv",
  "current_period": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"},
  "baseline_period": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"},
  "dimensions": [],
  "filters": {}
}
```

## Knowledge Dependencies

- `metrics.json`
- `business_rules.json`

## Process

1. 按 Metric Dictionary 获取指标定义、时间口径、过滤规则。
2. 使用完全一致的语义分别计算 Current 与 Baseline。
3. 计算：
   - `absolute_change = current - baseline`
   - `relative_change = (current - baseline) / baseline`
4. Baseline 为 0 时，`relative_change = undefined`。

## Output Contract

```json
{
  "status": "success",
  "metric_id": "gross_gmv",
  "current_value": 880000,
  "baseline_value": 1000000,
  "absolute_change": -120000,
  "relative_change": -0.12,
  "warnings": [],
  "limitations": []
}
```

## Boundaries

不负责：

- 判断为什么变化；
- 选择 Driver；
- 自动下钻；
- 决定是否停止。
