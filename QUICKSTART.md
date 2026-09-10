# Quick Start — Business Performance Agent

## Environment

需要 Python 3.11+。从包含 `pyproject.toml` 的完整源码根目录执行，保留 `specs/` 与 `evals/`。当前采用 editable 安装。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

macOS/Linux 激活命令为 `source .venv/bin/activate`。若 PowerShell 激活受限，可用 `.\.venv\Scripts\python.exe` 代替后续 `python`，不必修改全局策略。

## Offline Mock

首次运行不需要 API Key、Gemini SDK 或 Complete Journey 原始数据。安装可能需要访问 Python 包索引获取构建工具；安装后的 Mock 执行和普通测试不需要网络。

```bash
python -m business_performance_agent --input examples/gmv_input.json --mock-llm
python -m business_performance_agent --input examples/gmv_input.json --mock-llm --json
python -m unittest discover -s tests -v
```

Mock 是固定合成数据：GMV 10,000 → 7,350，停止原因为 `target_coverage_reached`。去掉 `--json` 查看 Markdown。也可使用安装后的 `bpa` 入口。

## SQLite smoke

以下构建器属于 Eval support，仅生成合成数据用于后端 smoke，不运行任何 Golden Set Case，也不加载 Expected：

```bash
python -m evals.support.fixture_builder --database evals/results/smoke.db
python -m business_performance_agent --database evals/results/smoke.db --mapping evals/results/smoke.mapping.json --input examples/gmv_input.json --mock-llm --json
```

生成器拒绝覆盖已有目标；再次生成请使用新路径。该 smoke 数据 GMV 为 1,000 → 700，不是 Mock 快照中的数值，也不是 Golden Set 的预期答案。

正式 CLI 的 SQLite 是通用单表映射入口，不依赖 `evals`。对自己的规范化明细表，提供 `--database PATH --mapping PATH`；映射字段、数据来源及完整周期契约见 [DATA_SOURCES](docs/DATA_SOURCES.md)。SQL 只读，不允许 LLM 猜测映射。SQLite 必须显式提供输入或问题。

## Optional Live: DeepSeek

以下为显式 opt-in，会产生 Provider 请求及潜在费用。DeepSeek 使用标准库 HTTP，不需要额外 SDK。先完成上面的离线示例。

```powershell
$env:DEEPSEEK_API_KEY="your-key"
$env:DEEPSEEK_MODEL="deepseek-v4-flash"
python -m business_performance_agent --input examples/gmv_input.json --provider deepseek --json
```

此命令仍使用 synthetic Mock 数据，真实 Provider 不等于真实经营数据。程序不自动加载 `.env`。只设置当前终端环境变量，不把真实 Key 写入文件。更多配置见 [DeepSeek](docs/DEEPSEEK_PROVIDER.md)。无需运行文档中的 Live Eval 来完成安装。

## Optional Live: Gemini

```bash
python -m pip install -e ".[gemini]"
```

在运行程序的 PowerShell 中设置变量；以下 Key 只是占位值：

```powershell
$env:GEMINI_API_KEY="your-key"
$env:GEMINI_MODEL="gemini-3.8-flash"
```

`.env.example` 仅说明配置，程序不自动加载 `.env`，不要把真实 Key 提交到 Git。

```bash
python -m business_performance_agent --database evals/results/smoke.db --mapping evals/results/smoke.mapping.json --input examples/gmv_input.json --gemini --json
```

可将 `--input ...` 换成 `--question "Diagnose gross_gmv. Current 2026-08-31 to 2026-09-06. Baseline 2026-08-24 to 2026-08-30. No filters."`。`--mock-llm` 与 `--gemini` 互斥；`--model MODEL_ID` 需与 `--gemini` 一起使用，并优先于 `GEMINI_MODEL`。

Gemini 只负责意图、合法候选选择、已验证 Claim 编排。结构化输入和唯一候选不必调用模型。429/503/504 等暂时故障最多重试一次；SDK `attempts=1`，避免叠加。单次请求超时 60 秒，重试间隔 2 秒。报告最终失败使用确定性 Markdown，不生成额外原因或建议，不掩盖意图、路由或数据质量失败。

## Windows entry

```powershell
.\run.ps1 -InputFile examples/gmv_input.json -MockLLM -Json
.\run.ps1 -Database evals/results/smoke.db -Mapping evals/results/smoke.mapping.json -InputFile examples/gmv_input.json -MockLLM -Json
```

支持 `-Gemini`、`-Model`、`-Question`、`-Test`；参数冲突仍由同一 CLI 校验。

## Testing

普通 discovery 永远不调用真实 Gemini，包括已设置 Key 或 live opt-in 变量的环境：

```bash
python -m unittest discover -s tests -v
```

Live 测试只在**显式模块调用**且同时满足两个环境条件时执行：

```powershell
$env:BPA_RUN_LIVE_TESTS="1"
python -m unittest tests.test_gemini_live -v
```

还必须已安装 Gemini SDK 并设置 `GEMINI_API_KEY`。未 opt-in 或无 Key 时 skip。可执行 `Remove-Item Env:BPA_RUN_LIVE_TESTS` 关闭开关。Live 使用 synthetic SQLite，不是正式 Eval；普通 CI 无需 Key。

Core / integration 测试用文件名区分，见 [tests/README.md](tests/README.md)。独立实验不在正式 discovery 中。格式检查：

```bash
python -m pip install -e ".[dev]"
ruff format --check business_performance_agent tests evals
```

## Output and Trace

CLI 返回 `run_id`、`result`、`trace_path`、`execution_mode`。元数据区分 `data_backend`（memory/sqlite）和 `data_origin`（synthetic/public_historical/user_supplied），不从文件存在推断真实性。当前 `production_database=false`。

报告 Trace 记录 `report_renderer`、`provider_error_code`、`retry_count`；Gemini JSON 输出还包含报告。Mock JSON 不执行报告渲染。日志和生成数据库不提交 Git。

退出码 0 可代表 partial 或合法边界停止，blocked/failed 为 1，参数/路径错误通常为 2；须阅读状态与停止原因。字段缺失、周期不完整、数据质量边界都不应靠更改业务定义绕过。

## Eval status

已提供第一版 Offline Eval，见 [Eval 文档](evals/README.md)。执行顺序为 fixture → Agent → actual result → load Expected → grading；Agent 不接收 case_id 或 Expected。
