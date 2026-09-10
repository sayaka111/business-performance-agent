# 简历候选文本

**精简项目名称：经营分析 Agent**

**定位：** 结合确定性数据分析与受约束 LLM 的个人工程项目，提供可追踪的 GMV 诊断与证据边界。

- 实现语义规范驱动的 GMV 诊断 Agent，将 7 个分析 Skill、显式状态机、贡献闭合校验与 Evidence/Trace 结合，支持 Mock、SQLite 及 Gemini/DeepSeek，避免由模型自由计算和推断口径。
- 接入 Complete Journey 约 147 万行公开历史交易，以数据契约和显式映射完成可复现 SQLite 准备；保存主 Driver、品类贡献和渠道不可用安全停止示例，明确数量与退款等能力限制。
- 建立离线/Live 评测与冻结历史；修复后 20 场景回归 16 通过、4 个失败保留，适用计算检查 19/19、Evidence 覆盖 52/52；实现 Provider 有限重试与确定性报告回退。

数字来源：[Eval](evaluation.md)、[真实数据报告](../COMPLETEJOURNEY.md)。这是个人原型，没有虚构企业部署或业务收益；20 场景已经用于修复，是回归集。
