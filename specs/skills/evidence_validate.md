# Skill: evidence_validate

## Purpose

验证最终分析 Claim 是否由已有结构化分析证据支持，防止报告阶段产生无证据扩写。

## Input Contract

```json
{
  "claim": "订单量是 GMV 下降的主要内部驱动因素。",
  "evidence": []
}
```

## Knowledge Dependencies

- `metrics.json`
- `metric_relationships.json`
- `business_rules.json`
- 前序 Skill 的结构化输出

## Evidence Levels

### Direct
查询或指标比较直接得到的事实。

例：

```text
Gross GMV WoW = -12%
```

### Derived
通过 Knowledge 中合法公式与 Skill 计算得到。

例：

```text
Orders Effect accounts for most of ΔGMV.
```

### Unsupported
分析链中没有相应证据。

例：

```text
用户消费意愿下降。
```

## Process

1. 将 Claim 中的 Metric、Dimension、方向、程度与原因类型解析出来。
2. 检查是否存在 Direct / Derived Evidence。
3. 检查 Claim 是否越过 causal boundary。
4. 返回 supported / unsupported / partially_supported。
5. 核心 Unsupported Claim 不允许进入最终 Report。

## Output Contract

```json
{
  "status": "success",
  "claim_status": "supported",
  "evidence_level": "derived",
  "evidence_refs": ["analysis_step_3"],
  "warnings": [],
  "limitations": []
}
```

## Boundaries

不负责：

- 创造新的业务解释；
- 补齐缺失证据；
- 把“Campaign A 流量下降”扩写成“竞争对手竞价上升”。
