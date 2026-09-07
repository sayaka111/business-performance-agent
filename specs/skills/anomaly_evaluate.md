# Skill: anomaly_evaluate

## Purpose

判断已观察到的指标变化是否达到需要进一步诊断的异常程度。

## Input Contract

```json
{
  "metric_compare_result": {},
  "anomaly_policy": {
    "method": "relative_change_threshold",
    "warning_threshold": 0.10,
    "critical_threshold": 0.20
  }
}
```

## Knowledge Dependencies

- 指标 ID 与基本语义来自 Knowledge。
- 异常阈值属于 Workflow / Policy Config，不写死在 Skill。

## Process

1. 校验 compare result 是否有效。
2. 根据传入的 anomaly policy 进行判断。
3. 返回异常方向与严重度。

## Output Contract

```json
{
  "status": "success",
  "is_anomaly": true,
  "direction": "decrease",
  "severity": "warning",
  "warnings": [],
  "limitations": []
}
```

## Boundaries

不负责：

- 决定异常后调用哪个 Skill；
- 决定诊断路径；
- 修改异常阈值。
