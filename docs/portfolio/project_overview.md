# Business Performance Agent — Project Overview

## Problem

经营分析反复进行周期比较、拆解变化、贡献排序和报告整理。关键困难是口径一致、路径合法、结果可复核，而不是单纯生成流畅文字。

## My Design

我把业务语义保存在冻结 JSON 规范中，以七个单一职责 Skill 和显式状态机执行 GMV 诊断。LLM 负责意图解析、必要时从合法候选选择，以及编排已验证结论；Python 负责数值与证据规则。

## Architecture

[架构图与实现映射](../ARCHITECTURE.md)：自然语言或结构化输入 → 数据契约/映射检查 → Runtime → Skills/Tools → Evidence → Result → 报告。SQLite 是只读单表接入，Mock 可完全离线；Gemini 和 DeepSeek 通过共享 Provider 接口替换。

## Key Engineering Decisions

- **计算不交给 LLM**：差值、乘法/加法贡献、闭合和阈值可以确定性计算，重复结果应可检查。
- **Dataset Contract 必须显式**：字段名称不足以证明业务等价；交易有效性可以是来源契约，不需要虚构 payment_success 字段。
- **Contribution 不等于 causality**：AOV 是内部贡献来源，并不证明促销、竞价或竞争对手造成变化。
- **安全停止是有效结果**：缺少渠道或数量能力时披露限制，保留可支持的结论，不继续造路径。
- **评测历史不能洗掉失败**：Expected 与 Actual 隔离，冻结每轮结果；被用于修复的数据集改称 regression set。

## Evaluation Strategy

离线合成场景验证确定性行为，Live 回归验证意图和受约束路由，Provider 事件单独统计。修复后 DeepSeek 回归 16/20 PASS，计算检查 19/19、路径 17/19、嵌套 Driver 2/4；不把子指标满分包装成系统满分。[完整口径及失败](evaluation.md)。

## Real-Data Integration

Complete Journey 1,469,307 行历史交易经保留行的商品 left join 转成 SQLite；两次构建哈希一致。gross_gmv 是零售商商品销售所得，不是顾客自付或标价。缺失 category 保留 unknown；household 是家庭实体，数量混合单位未擅自换算。

[三个示例](../../examples/real_data/completejourney/portfolio.md) 展示 AOV 主贡献、合法 category 排名以及 channel 不可用时的 blocked。四场景离线/Live 保存结果经一致性验证，Live 7 请求成功；这是有限真实数据接入验证。

## What Failed and What Was Changed

早期 Intent schema 没有保存 requested dimension 的 context，导致模型识别维度后信息不能进入 Runtime。修复共享 Intent contract，区分分组偏好与过滤值，并拒绝未验证的过滤别名。整体回归改善，但还存在错误添加 customer_type 偏好导致的路径回归。

Gemini 曾出现 429/503/504。通过统一有限应用重试、关闭 SDK 叠加重试、确定性报告回退保留已验证结果，而不是改业务规则迁就 Provider。Phase 3 进一步通过来源契约处理交易有效性，并在不可用维度入场时停止。所有历史失败仍可阅读。

## Current Boundaries

单一 GMV Workflow，本地原型；没有生产长期验证。真实数据不支持退款、数量单位相关指标、channel/region/campaign 或生命周期新老客。没有 RAG、Reviewer、Memory、多 Agent 或自动业务行动。未验证独立 wheel 分发。

## What I Would Build Next in Production

先建立数据契约版本、质量告警及访问控制，测量数据库规模下的资源消耗；收集独立未见场景评测意图和嵌套路径，再根据失败决定扩展。生产监控与部署是未来工作，不是当前项目成绩。

## Engineering disclosure

项目使用 Codex 辅助工程实现与验证；公开材料展示业务语义、架构决策、测试和证据，不将实现描述成完全手写。

早期 Golden 失败还暴露了维度下钻时丢失输入指标作用域的问题：保留 GMV 根分解，再优先处理输入指标的显式合法维度，并在原生粒度下定位嵌套指标。该最小编排修复对应冻结 Round 2 的 9/12 到 Round 3 的 12/12；公式和贡献合法性未改。后续 Live Intent contract 修复的 45% → 80% 及四个残留失败见 [Eval](evaluation.md)，不视为受控模型比较。
