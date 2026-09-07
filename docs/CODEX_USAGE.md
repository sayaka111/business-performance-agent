# Codex → Existing Agent 使用说明

操作规则入口：[AGENTS.md](../AGENTS.md)。此文档记录现有调用契约，不新增业务 Schema。

## 打开方式

将 repository 根目录作为 Codex 项目打开。根目录 `AGENTS.md` 为项目操作索引。官方说明指出指令在运行开始时发现；没有可识别项目根目录时仅检查当前目录，因此从此文件夹开始最明确。已有会话未加载新文件时可重新打开项目任务，或明确让 Codex 阅读该文件。[官方 AGENTS.md 文档](https://learn.chatgpt.com/docs/agent-configuration/agents-md)

## 已核对的实际入口

`business_performance_agent/__main__.py` → `app/cli.py:main` → `Runtime(...).run(raw)`。没有 HTTP API。首次使用按 [QUICKSTART](../QUICKSTART.md) 创建并激活 Python 3.11+ 环境，执行 `python -m pip install -e .`。没有第三方运行时依赖；保留源码与规范目录。Windows 的 `run.ps1` 优先使用已激活环境或项目 `.venv`，不要求安装 Codex Python。

| Python CLI | PowerShell 入口 | 作用 |
|---|---|---|
| `--input PATH` | `-InputFile PATH` | 读取 UTF-8 JSON（允许 BOM） |
| `--question TEXT` | `-Question TEXT` | JSON 文本或有限自然语言解析；与 input 互斥 |
| `--mock-llm` | `-MockLLM` | 离线候选选择替身；无真实模型调用 |
| `--json` | `-Json` | stdout 只输出一个 JSON 对象 |
| `--help` | 使用 Python 入口 | 显示真实参数 |
| `python -m unittest discover -s tests -v` | `-Test` | 全部 tests |

不传 input/question 时原入口使用示例输入；Codex 常规调用应显式传入文件，避免误用默认周期。不添加新的 intent 字段、路径选择字段、数据源切换参数或 Policy 覆盖参数。

## 结构化请求

复用 [examples/gmv_input.json](../examples/gmv_input.json)：

```json
{
  "metric_id": "gross_gmv",
  "current_period": {"start": "2026-08-31", "end": "2026-09-06"},
  "baseline_period": {"start": "2026-08-24", "end": "2026-08-30"},
  "filters": {},
  "context": {}
}
```

实际校验来自 `models/schemas.py:WorkflowInput.parse`。目标仅 gross_gmv，日期必须有效且 baseline 早于 current；filters 使用已有维度 ID 与字符串值。可选 context 只接受 `customer_structure`、`traffic_view`、`preferred_dimension`；只能表达用户已有上下文，不能为了改变路径而伪造上下文。`intent` 不在当前输入字段中，传入会被 Runtime 判定 invalid_input。

用户明确要求 Demo / 运行当前示例时，说明 Mock 后可直接使用上述请求；真实业务任务不能把用户日期替换为 fixture。当前真实数据源尚未接入，需先完成独立数据接入开发。

## 稳定调用与读取

```powershell
# 在下载/解压后的项目根目录执行；无需使用作者机器的绝对路径。
$agentJson = .\run.ps1 -InputFile .\examples\gmv_input.json -MockLLM -Json
$agentExit = $LASTEXITCODE
if ($agentJson) {
    $agentOutput = ($agentJson -join "`n") | ConvertFrom-Json
    $agentOutput.execution_mode
    $agentOutput.result.workflow_status
    $agentOutput.result.target
    $agentOutput.result.key_findings
    $agentOutput.result.stop_reason
    $agentOutput.trace_path
}
```

其他具备 Python 的环境等价命令：

```text
python -m business_performance_agent --input examples/gmv_input.json --mock-llm --json
```

JSON 外层保留原 `run_id`、`result`、`trace_path`，包含应用层 `execution_mode`：

```json
{
  "dataset": "mock",
  "dataset_id": "mock_retail_v1",
  "llm": "mock",
  "real_business_data": false
}
```

不带 mock-llm 时 `llm="unconfigured"`，其余相同。此元数据由 CLI 实际装配模式产生，用户输入不能覆盖；业务 `result` 和 Runtime Trace 不改写。Trace 的 `final_structured_result` 应与返回的 `result` 完全相等。应用模式在 CLI 输出中；Trace 格式保持独立，脱离 CLI 的日志可从数据 provenance 与 router_decisions 核实模式。

`result` 完整复用冻结 `output_schema.json`：workflow_status、target、primary_driver、secondary_drivers、diagnostic_path、key_findings、evidence、warnings、limitations、failed_branches、stop_reason 等。不得创建替代结果定义；展示时保留 Evidence 引用与限制。无 `--json` 时首行也会明确标记 MOCK DATA / 非真实经营数据。

## 失败与边界

| 情况 | 真实行为 / Codex 处理 |
|---|---|
| 完成、非异常、partial、证据边界停止 | CLI 可退出 0；继续检查业务状态和 stop_reason，不凭退出码声称全部成功 |
| Workflow blocked / failed | 退出 1，仍有 JSON 与 Trace；展示 warnings、limitations、failed_branches |
| 参数互斥、文件不存在、无效 JSON、未配置 LLM 的自然语言问题 | 退出 2，stderr 错误，无本次业务输出；不尝试解析终端错误为报告 |
| 未配置 LLM，多候选无法选择 | 可能 completed + evidence_boundary_reached；Trace 中 `llm_provider_not_configured` 是准确原因，Codex 不接管路由 |
| 不支持的输入字段/指标 | Runtime 返回 invalid_input；只修正输入表达，不改变用户目标、不改业务定义 |
| 非 Mock 完整周期、数据缺失 | 报告数据限制；不换日期或造数据 |
| semantic_mapping_missing / semantic_conflict | 报告映射缺失或冲突并停止；不猜字段 |
| 真实数据库或真实模型请求 | 当前未接入；说明需要相应 Adapter / Provider 开发，不能把 Mock 说成 Real |
| 竞争、市场、用户心理等外部因果 | 不支持；不绕过 Evidence Boundary 自己完成解释 |

## 三种任务示例

1. **使用 Agent**：“用当前示例诊断 GMV 异常。” → 说明 Mock 周期，运行上述命令，从 result 转述数值与引用，附本次 run_id / trace_path。
2. **修改 Agent**：“Add a new retention analysis skill.” → 按开发任务检查规范和授权范围，实施必要改动与验证；不将它识别为 GMV 分析请求。
3. **当前无法处理**：“分析竞品降价为什么影响我们的 GMV。” → 当前无外部竞品数据与因果能力，说明不能证明；不编造竞争故事，不自动新增 Skill。

## Smoke test

```text
python -m unittest discover -s tests -p test_cli_integration.py -v
```

测试通过真正的 `python -m business_performance_agent` 子进程验证输入、原 Runtime、JSON、Mock 标识、失败状态与 Trace，并比较运行前后规范文件哈希。完整测试另运行 `run.ps1 -Test`。这是入口集成测试，不是 Eval，也不宣称测试了新 Codex 会话的实际指令加载或自然语言任务分类准确率。
