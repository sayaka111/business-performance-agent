# Business Performance Agent — Codex operator guide

## Repository Purpose

This repository implements a specification-driven Business Performance Agent.
当前核心 Workflow：`gmv_diagnosis`。Codex 是 Agent operator / development interface；经营分析由现有 Runtime 执行。

## Source of Truth

此文件仅是操作入口，不是第二套业务 Specification。详细定义以以下冻结资产为准（统一保存在 specs/）：

- [Product Scope](specs/product_scope.md)
- [Knowledge](specs/knowledge/README.md)：同目录四个 JSON 定义指标、公式、关系、维度与业务规则。
- [Skills](specs/skills/README.md)：同目录七个 Skill 规范。
- [Workflow](specs/workflows/gmv_diagnosis/workflow.md)：同目录 `state_schema.json`、`routing_rules.json`、`policy.json`、`output_schema.json`。
- [System Contract](specs/system_contract.md)

普通运行任务不得修改 Knowledge、指标定义/关系、Dimension/Business Rules、冻结 Workflow 或 Stop Policy。开发任务也只修改用户授权范围；发现真实规范冲突时列明冲突并暂停冲突部分，不自行覆盖业务定义。

## When to Invoke the Agent

用户要求经营分析、GMV diagnosis、“使用当前 Agent”、“运行一下 Agent”或“按已有 Workflow 分析”时：

1. 优先调用现有 CLI；不自行取数、重算指标、设计路径或直接调用零散 Skill 代替 Workflow。
2. 先区分示例运行和真实业务分析。可使用 Mock 或兼容 Olist 原始表结构的 SQLite；真实分析须指定数据文件，不用示例替代真实数据。
3. 示例/演示任务可使用 `examples/gmv_input.json` 并明确说明 Mock 周期；用户指定的日期、Metric、Filters 不得静默替换。必需信息缺失且非示例运行时向用户说明缺什么。
4. 将请求转成现有 JSON Input，用 `--input ... --json` 获取结果。不要依赖 Mock 自然语言解析理解复杂请求。
5. 读取 `result`、`execution_mode`、`run_id`、`trace_path`，保留状态、警告、限制和停止原因。

## When NOT to Invoke the Agent

修改代码、增加 Skill、调整 Workflow、接数据库、接真实 LLM、修改报告格式属于开发任务；架构问答按项目代码解释，不触发经营诊断。开发验证可以运行测试或示例，但不能把验证结果当作用户的真实经营分析。

## How to Run

在此 repository 根目录运行；需要 Python 3.11+。首次使用按 [QUICKSTART.md](QUICKSTART.md) 创建并激活 `.venv`，执行 `python -m pip install -e .`。基础离线运行无第三方依赖；Gemini 另需安装 `python -m pip install -e ".[gemini]"` 并设置进程环境变量 `GEMINI_API_KEY`。保留源码目录及冻结规范，当前交付方式为源码目录 + editable 安装。

```text
python -m business_performance_agent --help
python -m business_performance_agent --input examples/gmv_input.json --json
python -m business_performance_agent --input examples/gmv_input.json --mock-llm --json
python -m unittest discover -s tests -v
python -m unittest discover -s tests -p test_cli_integration.py -v
```

Windows 可使用已有 PowerShell 入口（依次寻找已激活环境、项目 `.venv`、PATH Python）：

```powershell
.\run.ps1 -InputFile .\examples\gmv_input.json -MockLLM -Json
.\run.ps1 -Test
```

已有 `python -m` / `run.ps1` 足够，不新建 wrapper。输入是 `metric_id`、`current_period`、`baseline_period`、`filters`，可选 `context`；**不接受 `intent` 字段**。参数、合法输入、输出外层和失败码见 [Codex Usage](docs/CODEX_USAGE.md)。

## Runtime Authority / Evidence Boundary

运行任务的 Agent structured output（`result`）是分析结论的 authoritative source。Codex 只总结、格式化、解释字段和展示 Trace；核心结论引用 `key_findings.evidence_refs` 对应的 direct / derived Evidence，不增加外部原因、跨层贡献比例或强业务动作。

允许转述有证据的“Orders 是 GMV 下降的主要内部驱动”；无证据时不补充“因为竞品加大广告投放”。

当 `stop_reason=evidence_boundary_reached`，停止继续分析并说明证据边界。只有 Trace 确认是数据/知识证据边界时，才可表述“当前 Agent 已分析到内部数据可证明的最深层级”。如果路由理由是 `llm_provider_not_configured`，必须说明缺少 LLM 导致多候选未选择，不能声称穷尽证据，不能由 Codex 接管选路或偷偷换 Mock LLM 重跑。

## Runtime Modes / Data Status

- 不带 `--database` 使用 `MockDatasetAdapter`（`mock_retail_v1`）；带参数使用 Olist 原始表专用 `SQLiteDatasetAdapter`（`olist_raw_sqlite_v1`），只读访问本地数据，不代表生产数据库接入。
- 两个 Mock 完整周期：2026-08-24～2026-08-30、2026-08-31～2026-09-06。它们是固定 fixture，不能冒充用户的“本周”。
- `--mock-llm` 使用离线 Mock；`--gemini` 使用真实 Gemini；两者均不带时 LLM 未配置，确定性节点仍可运行，多候选节点可能停止。
- SQLite 必须显式提供输入或问题。数据质量不足可合法 blocked，不得修改业务口径使其通过。范围见 [Data Sources](docs/DATA_SOURCES.md)。
- Gemini 报告失败会回退为基于既有结果的确定性 Markdown；这不补救意图、路由或数据质量失败。Trace 记录 renderer、provider error code 与 retry count。
- `execution_mode` 是 CLI 元数据，不属于业务 Output Schema。根据其数据和模型标记说明实际模式，不把 Mock 结果描述为真实经营分析。

SQLite 示例（数据库与 Gemini 配置先按 Quick Start 准备）：

```text
python -m business_performance_agent --database data/olist_raw.db --input examples/olist_input.json --mock-llm --json
python -m business_performance_agent --database data/olist_raw.db --input examples/olist_input.json --gemini --json
```

`run.ps1` 不传递 SQLite、Gemini 或模型参数，这些模式使用 Python CLI。全量测试在设置 `GEMINI_API_KEY` 时可能调用真实 API；纯离线验证使用 Quick Start 中隔离密钥的测试命令。

## Failure Behavior

先报告真实失败原因；可以只读检查配置、代码和 Trace。输入不支持、缺数据、缺 semantic mapping、blocked/failed、LLM/Dataset 未配置时，明确补充项；不得绕过 Runtime 或修改冻结定义使其“成功”。

退出码 0 仍可能是 partial 或边界停止，必须读 `result.workflow_status` 和 `stop_reason`。退出码 1 的 blocked/failed 仍有 JSON；输入文件/参数错误通常退出码 2，stderr 有原因，不生成虚构业务结果。没有新 run_id 时不得用旧日志假装本次成功。

## Usage Examples

- “Use the Business Performance Agent to diagnose the GMV anomaly.” → 确认周期和数据范围；示例任务使用现有 fixture，构造合法 JSON，运行 CLI，返回带 Mock 标识的结果与 Trace。
- “Add a new retention analysis skill.” → 开发任务；检查授权范围及规范，不自动执行 GMV 诊断，不擅自扩展冻结业务范围。
- “分析竞品降价为什么影响我们的 GMV。” → 当前 Agent 无竞品数据或因果能力；说明无法证明该外部因果，不自行编造解释。
