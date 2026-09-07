# Skills Layer v1.0

## 1. Skill 定义

Skill 是可复用的分析能力，回答：

> 某一种分析动作应该如何执行？

Skill 不应绑定某个具体 Workflow。例如 `metric_decompose` 可以服务 GMV、Revenue、Orders 等不同 Workflow。

## 2. 当前 Core Skills

1. `metric_compare`
2. `anomaly_evaluate`
3. `metric_decompose`
4. `contribution_analysis`
5. `dimension_drilldown`
6. `data_quality_guard`
7. `evidence_validate`

## 3. Skill 统一约束

所有 Skill 必须遵守：

- 只能读取 Knowledge，不得修改 Knowledge。
- 不决定完整 Workflow 的执行顺序。
- 不自行选择下一步分析路径，除非 Workflow 明确授权。
- 不管理递归深度、Top Coverage、最小贡献阈值等停止条件。
- 不将相关性 / 贡献定位包装成因果推断。
- 不产生无证据的外部原因。
- 不直接生成强业务动作。
- 指标与维度必须使用 Knowledge 中的稳定 ID。
- 所有核心输出应尽量结构化，便于 Workflow 与 Eval 消费。

## 4. 建议返回状态

每个 Skill 建议使用统一状态：

```json
{
  "status": "success | warning | blocked | failed",
  "warnings": [],
  "limitations": []
}
```
