# Skill: data_quality_guard

## Purpose

判断当前数据是否足以支撑本次分析，并对严重数据问题进行阻断。

## Input Contract

```json
{
  "analysis_scope": {
    "metrics": [],
    "dimensions": [],
    "current_period": {},
    "baseline_period": {}
  }
}
```

## Knowledge Dependencies

- `metrics.json`
- `dimensions.json`
- `business_rules.json`
- 实际 Dataset Schema / Adapter metadata

## MVP Checks

### 1. Period Completeness
当前分析周期与基准周期是否完整。

### 2. Duplicate Integrity
关键业务 ID 是否出现异常重复。

### 3. Metric Coverage
指标必需字段是否缺失，以及缺失率是否异常。

### 4. Join Coverage
关键关系覆盖率，例如：
- Order → Customer
- Order → Channel
- Order Item → Product

### 5. Unknown Share
`unknown` / `unattributed` 是否过高。

### 6. Comparison Consistency
Current 与 Baseline 是否使用一致的指标语义和过滤规则。

### 7. Optional Capability Availability
例如 Session 数据是否足够支持 Session-based decomposition。

## Output Contract

```json
{
  "status": "warning",
  "analysis_allowed": true,
  "issues": [
    {
      "type": "high_unknown_channel",
      "share": 0.18
    }
  ],
  "warnings": [],
  "limitations": [
    "Channel-level diagnosis should be treated cautiously."
  ]
}
```

阻断示例：

```json
{
  "status": "blocked",
  "analysis_allowed": false,
  "issues": [
    {"type": "incomplete_current_period"}
  ]
}
```

## Boundaries

第一阶段只负责：

```text
detect → report → warn/block
```

不负责自动修复数据。
