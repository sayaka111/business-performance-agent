# Knowledge Layer v1.0

## 1. 职责

Knowledge Layer 只负责定义：

- 指标是什么；
- 指标如何计算；
- 指标之间存在什么严格或诊断性关系；
- 维度如何定义；
- 哪些 Metric × Dimension 组合允许做严格贡献分析；
- 哪些业务规则必须被所有 Skill 与 Workflow 共同遵守。

Knowledge Layer **不负责**：

- 决定先分析哪个指标；
- 决定使用哪一种 decomposition；
- 决定维度下钻顺序；
- 决定什么时候停止；
- 解释外部因果；
- 生成最终业务动作。

## 2. 文件

- `metrics.json`：指标字典。
- `metric_relationships.json`：指标关系。
- `dimensions.json`：维度字典与贡献适用性。
- `business_rules.json`：全局业务语义规则。

## 3. 关系类型

当前支持：

- `exact_multiplicative`：严格乘法恒等关系。
- `exact_additive`：严格加法关系，可带正负 coefficient。
- `partition`：互斥且完备的结构划分。
- `diagnostic`：用于诊断但不保证数学闭合的关系。

## 4. 核心原则

`Relationship != Workflow`

Knowledge 可以声明：

```text
Orders = Buyers × OrdersPerBuyer
Orders = NewBuyerOrders + ReturningBuyerOrders
Orders = Sessions × OrdersPerSession
```

但不能声明：

```text
先查 Buyers，再查 Customer Type，再查 Sessions。
```

后者属于 Workflow。
