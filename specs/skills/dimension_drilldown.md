# Skill: dimension_drilldown

## Purpose

回答“某个指标的变化主要集中在哪些 Segment”，但不决定应该分析哪个 Dimension。

## Input Contract

```json
{
  "metric_id": "orders",
  "dimension_id": "channel",
  "current_period": {},
  "baseline_period": {},
  "filters": {}
}
```

## Knowledge Dependencies

- `metrics.json`
- `dimensions.json`
- `business_rules.json`

## Process

1. 校验 Metric 与 Dimension 是否存在。
2. 查询 `contribution_support`。
3. 按 Dimension Segment 计算：
   - Current
   - Baseline
   - Absolute Change
   - Relative Change
4. 如果 Contribution Supported，可将结果交给 `contribution_analysis`。
5. 如果不支持，只返回描述性比较结果。

## Output Contract — Contribution Supported

```json
{
  "status": "success",
  "metric_id": "orders",
  "dimension_id": "channel",
  "contribution_supported": true,
  "segments": []
}
```

## Output Contract — Contribution Blocked

例如 `orders × category`：

```json
{
  "status": "success",
  "metric_id": "orders",
  "dimension_id": "category",
  "contribution_supported": false,
  "segments": [],
  "limitations": [
    "One order may contain multiple categories; order contribution would double-count."
  ]
}
```

## Boundaries

不负责：

- 决定优先分析 Channel、Category 还是 Region；
- 自动继续到下一维度；
- 设置停止条件；
- 对非可加维度伪造贡献率。
