# Codex → Business Performance Agent

将 repository 根目录作为项目打开，按 [AGENTS.md](../AGENTS.md) 操作。Codex 是可选的开发/操作界面，CLI 可独立运行。分析必须调用现有 Runtime，不由 Codex 自行重算指标或补写因果解释。

## Actual entry points

`python -m business_performance_agent` → `app/cli.py` → `Runtime.run`。没有 HTTP API。环境和可选 SDK 安装见 [QUICKSTART](../QUICKSTART.md)。

| Python CLI | 用途 | run.ps1 对应 |
|---|---|---|
| `--input PATH` | UTF-8 JSON，允许 BOM | `-InputFile` |
| `--question TEXT` | JSON 文本或自然语言；与 input 互斥 | `-Question` |
| `--mock-llm` | 离线 Mock Provider | `-MockLLM` |
| `--gemini` | Gemini Provider，与 mock-llm 互斥 | 不支持，用 Python CLI |
| `--model MODEL_ID` | 覆盖 Gemini 模型，要求 gemini | 不支持，用 Python CLI |
| `--database PATH` | 只读 Olist SQLite，要求显式输入 | 不支持，用 Python CLI |
| `--json` | 输出结构化 JSON | `-Json` |
| `--help` | 查看真实参数 | 用 Python CLI |

无 database 时使用 Mock；无 Provider 标志时 LLM 未配置。默认输入仅供 Mock 演示，常规操作显式传文件。不要发明 `--mapping`、Policy 覆盖参数或新的输入字段。

## Mode selection

```bash
python -m business_performance_agent --input examples/gmv_input.json --mock-llm --json
python -m business_performance_agent --database data/olist_raw.db --input examples/olist_input.json --mock-llm --json
python -m business_performance_agent --database data/olist_raw.db --input examples/olist_input.json --gemini --json
```

第二、三条要求先准备兼容数据库，第三条还要求 SDK 和 `GEMINI_API_KEY`。实际源是 Olist 历史公开数据，不是生产数据库；质量检查可能 blocked。原始导入、映射和限制见 [DATA_SOURCES](DATA_SOURCES.md)。不静默切换真实/Mock 模式或替换用户周期。

## Workflow input

输入是 `metric_id`、`current_period`、`baseline_period`、`filters`，可选 `context`，参见 [Mock 输入](../examples/gmv_input.json) 与 [Olist 周期输入](../examples/olist_input.json)。

当前目标仅 `gross_gmv`；日期有效且 baseline 早于 current。Filters 使用 Knowledge 中的维度 ID 和字符串值。Context 仅接受 `customer_structure`、`traffic_view`、`preferred_dimension`，不能为改变路径而伪造上下文。`intent` 不是合法输入字段。

只有明确的示例请求才使用 synthetic 固定周期。自然语言解析需要 Provider，Mock parser 仅是有限的离线替身，不具备通用语义理解能力。

## Read result and trace

```powershell
$agentJson = python -m business_performance_agent --input examples/gmv_input.json --mock-llm --json
$agentExit = $LASTEXITCODE
if ($agentJson) {
    $agentOutput = ($agentJson -join "`n") | ConvertFrom-Json
    $agentOutput.execution_mode
    $agentOutput.result.workflow_status
    $agentOutput.result.key_findings
    $agentOutput.result.stop_reason
    $agentOutput.trace_path
}
```

输出含 `run_id`、`result`、`trace_path`、`execution_mode`。Mock 数据标识 `mock_retail_v1`、`real_business_data=false`；SQLite 标识 `olist_raw_sqlite_v1`、`production_database=false`。Provider 为 mock、gemini 或 unconfigured。

Gemini 模式还提供 report、`llm_requests_succeeded` 和 `report_rendering`。配置 Gemini 并不保证实际调用；唯一候选或无 Claim 时可不调用。核心结论以 `result` 为准，必须保留 Evidence 引用、警告和限制；Trace 中 `final_structured_result` 应与其一致。

报告生成后 Trace 记录 `report_renderer=gemini/deterministic_fallback`、`provider_error_code` 和报告 `retry_count`。SDK 不重试，应用最多重试一次。报告回退不改变业务结果，不证明模型调用成功，也不能代替失败的路由或意图解析。

## Failure handling

| 情况 | 操作 |
|---|---|
| 退出 0 | 仍检查 workflow_status / stop_reason，可能 partial 或边界终止 |
| Workflow blocked / failed，退出 1 | 读取结果和 Trace，展示 failed_branches、warnings、limitations |
| 参数/路径/解析错误，通常退出 2 | 不把终端错误当报告；Gemini intent 失败可能有独立 Trace，无业务结果 |
| `llm_provider_not_configured` | 说明缺少 Provider，不接管路由或偷偷换 Mock |
| 缺失字段/不兼容 Schema/semantic conflict | 核对数据契约，不猜字段、不删单补值或改变冻结口径 |
| 429 / 503 / 504 | 视为 Provider 暂时性故障，保留有限重试和报告回退记录，不反复重跑完整 E2E |
| 外部竞争、市场、心理因果 | 没有证据时不提供解释或强业务动作 |

新 Workflow、Adapter 或指标属于开发任务，按用户授权和冻结规范处理；运行请求不自行扩展业务范围。

## Tests

入口验证：`python -m unittest discover -s tests -p test_cli_integration.py -v`。
完整离线及可选 live 测试见 [Testing](../QUICKSTART.md#testing)。`run.ps1 -Test` 执行测试发现，若环境已有 Key 也可能执行 live 测试；要求离线时使用文档中的隔离子进程命令。
