# Public repository pruning

## STATUS

**PUBLIC REPOSITORY PRUNING: COMPLETE**

移出 27 个过程性文件，合并核心结论，保留最终系统、可读 Demo 和可信评测证据。业务代码、冻结规范、Case/Expected、grader 和保存的 benchmark / Demo 证据保持原始字节；没有运行 Live API 或 Holdout。

## REMOVED

从公开候选移出，保存于仓库外本地归档以便恢复：

- `experiments/` 的 12 个工具调用实验与 Provider 临时诊断文件。
- `docs/phase3/` 的 3 个阶段性审计、契约和交付报告。
- `evals/PHASE2_RESULTS.md`、`PHASE2_CLOSURE_REPORT.md`、`ROUND_3_ROOT_CAUSE.md` 及 `analysis/offline_vs_live_holdout_diagnosis.md`。
- `docs/portfolio/` 原 Phase 4 发布过程报告及 7 个测试输出、审计 JSON、哈希清单。

公开候选中没有 `*_prompt.md`。新增忽略与打包排除规则，防止指令文件和退役实验重新进入分发包。忽略的临时 Eval outputs、日志与原始数据仍留在本地，不作为公开内容。

## CONSOLIDATED

- Phase 3 契约、审计和验证 → [Complete Journey 最终技术说明](../COMPLETEJOURNEY.md)：basket 粒度、销售金额语义、混合数量单位、unknown category、能力限制和可复现准备证据。
- Phase 2 结果及诊断 → [Eval 概览](evaluation.md)：45% → 80% 的非受控前后观察、四个失败、分母与 Provider 限制，以及已暴露回归集声明。
- Round 3 作用域修复与 Intent contract 修复 → [项目设计复盘](project_overview.md)，保留问题与最小修复的技术解释。
- Provider 接入流水 → [配置与使用参考](../DEEPSEEK_PROVIDER.md)；Eval README 保留方法、接口与复现边界，移除过时阶段状态。

## KEPT AND WHY

- 完整运行源码、冻结 specs、软件测试、Case/Expected、grader 和执行工具：系统运行与复现需要。
- 七个小型 frozen benchmark 快照：支撑校准、失败、修复与 Provider 中断的诚信记录。未改机器结果或关联哈希文件；首页主要引导到最终 Eval 概览。
- 两批真实数据保存结果和 Trace、validation、准备 manifest：支持 Demo 与一致性结论，不以摘要替代关键 Evidence。
- 数据来源、软件许可状态与数据契约：不掩盖授权和语义边界。
- 简短 AI-assisted engineering 披露：不保留对话流水，也不宣称完全手写。

## PUBLIC REPO STRUCTURE

```text
README.md / QUICKSTART.md / AGENTS.md / pyproject.toml
business_performance_agent/   # final system
specs/                       # frozen specifications
tests/                       # offline software validation
docs/
  ARCHITECTURE.md / CODEX_USAGE.md / DATA_SOURCES.md
  DEEPSEEK_PROVIDER.md / COMPLETEJOURNEY.md
  portfolio/                 # overview, evaluation, resume, interview, this report
examples/                    # Mock examples and real-data demos / evidence
data/contracts/ + mappings/  # explicit dataset contract
scripts/                     # preparation and optional demo entry
evals/                       # methodology, runners, cases, expected, graders, frozen snapshots
.github/workflows/           # offline CI
```

`data/processed/completejourney/preparation_manifest.json` 是小型准备证据，明确纳入；大型 SQLite 不纳入。

## LINK / HYGIENE CHECK

本地文件链接检查通过；未发现常见密钥模式或当前环境密钥值，公开文件无超过 5 MB 的文件。扫描是有限自动检查，不是任意秘密格式的完整证明。原始数据、SQLite、日志、临时输出未纳入公开源码包。源码包构建和必需文件核对通过；已同步 MANIFEST 与忽略规则。

哈希检查曾发现批量文档整理影响八份保存报告的末尾换行，已从经原始 SHA-256 验证的副本恢复，最终受保护文件无变化。

## TESTS

完整离线软件套件：**128 total，126 passed，0 failed，2 Live tests skipped**。Mock JSON CLI exit 0，`completed / target_coverage_reached`。源码分发包检查通过。真实 API 请求 0；新 benchmark 0。详细临时检查输出存于仓库外归档，不再增加公开过程文件。

## KNOWN REMAINING INTERNAL-LOOKING FILES

`AGENTS.md` 是维护契约；benchmark 目录保留轮次命名以维持来源与哈希；Demo 的 run ID 和 Trace 为可追踪证据；本报告是本次明确要求的单一清理记录。它们不是 README 的主要阅读路径。历史回归失败、数据限制和无软件许可证状态仍公开说明。

## RELEASE READINESS

README → Demo / Architecture / Eval / Quick Start 路径完整。公开目录已去除重复阶段流水，业务行为和证据未改。仅完成本地整理；未 commit、push、tag 或创建 GitHub Release。

**PUBLIC REPOSITORY PRUNING: COMPLETE**
