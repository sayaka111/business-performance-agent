# Quick Start — Business Performance Agent

项目可本地运行，支持 Mock、Olist SQLite + Mock LLM、Olist SQLite + Gemini 三条路径，尚未经过企业生产环境验证。以下命令均从包含 `pyproject.toml` 的 repository 根目录执行。

## Environment

需要 Python 3.11+，保留完整源码与 `specs/`。当前使用源码 + editable 安装，不要只复制 Python 包。版本号由 `pyproject.toml` 管理。

Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

如果激活脚本受限，可将后续 `python` 替换为 `.\.venv\Scripts\python.exe`，不必修改全局执行策略。

macOS / Linux：

```bash
python3 -m venv .venv
source .venv/bin/activate
```

基础运行使用标准库；Gemini 另安装可选依赖。首次安装可能下载构建依赖，安装后的 Mock 运行无需网络。Codex 不是 CLI 的运行依赖。

## A. Offline Demo

```bash
python -m pip install -e .
python -m business_performance_agent --help
python -m business_performance_agent --input examples/gmv_input.json --mock-llm --json
```

这是 **Mock / synthetic dataset**。预期 GMV 为 10,000 → 7,350，`workflow_status=completed`，`stop_reason=target_coverage_reached`。模式为 `dataset=mock`、`llm=mock`、`real_business_data=false`。移除 `--json` 查看 Markdown。

固定周期为 2026-08-24～2026-08-30 与 2026-08-31～2026-09-06，不代表今天。无输入时默认使用 Mock 示例，推荐显式传文件。无 `--mock-llm` 且无 `--gemini` 时，LLM 未配置，多候选可能在边界停止。

## B. SQLite Mode

### Prepare database and mapping

当前 Adapter 面向 Olist 原始 Schema，不是任意 SQLite/SQL 生成器。使用已有兼容数据库，或准备以下原始 CSV：

```text
olist_orders_dataset.csv
olist_order_items_dataset.csv
olist_order_payments_dataset.csv
olist_customers_dataset.csv
olist_products_dataset.csv
```

下面的 `$source` 是占位路径，请替换为本机 CSV 目录。该操作只创建新数据库，不改原 CSV；数据库已存在时拒绝覆盖。

```powershell
$source = "C:\path\to\olist_raw_csv"
python -m business_performance_agent.data_contract.olist_raw --source "$source" --database data/olist_raw.db
```

导入保存原字段及来源摘要，再执行只读审阅。审阅发现缺失时可退出 1 并留下数据库及 Trace，不表示导入撤销。导入错误退出 2，新建的不完整数据库会清理。不要为通过审阅而直接删单或补值。

已有数据库只读审阅：

```bash
python -m business_performance_agent.data_contract.olist_raw --database data/olist_raw.db
```

核对 [Olist 映射](business_performance_agent/data_contract/olist_mapping.json) 和 [数据源契约](docs/DATA_SOURCES.md)。映射 JSON 不是通用 SQL 映射引擎，没有 `--mapping` 参数；仅编辑 JSON 不改变 Adapter 中的 SQL/物理字段转换。其他 Schema 需通过数据层开发适配，不能修改 Knowledge 迁就字段。

### Run with Mock LLM

```bash
python -m business_performance_agent --database data/olist_raw.db --input examples/olist_input.json --mock-llm --json
```

`--database` 支持相对当前目录的路径或绝对路径，含空格时加引号。SQLite 必须显式提供 `--input` 或 `--question`。

`olist_input.json` 是 2018 年 6 月对比 5 月的**周期请求**，不含数据，也不是成功结果快照。已审阅的 Olist 数据存在商品明细和支付时间缺失，此请求可能返回 `blocked / data_quality_boundary`。保留该状态，不改写为成功诊断。

数据标识为 `dataset=SQLite`、`dataset_id=olist_raw_sqlite_v1`、`production_database=false`。是否完整执行取决于数据质量、可用关系及停止策略。

## C. Gemini + SQLite

安装官方 SDK 可选依赖：

```bash
python -m pip install -e ".[gemini]"
```

设置当前 PowerShell 进程的变量；示例只是占位值，不要提交真实 Key 或将其粘贴到聊天中：

```powershell
$env:GEMINI_API_KEY = "your-key"
$env:GEMINI_MODEL = "gemini-3.8-flash"
```

程序读取进程环境变量，不自动加载 `.env`。Windows 可自行通过用户环境变量持久保存，随后重开终端使其生效；项目没有独立凭证存储功能。

结构化请求：

```bash
python -m business_performance_agent --database data/olist_raw.db --input examples/olist_input.json --gemini --json
```

自然语言意图解析：

```bash
python -m business_performance_agent --database data/olist_raw.db --gemini --question "Diagnose gross_gmv. Current 2018-06-01 to 2018-06-30. Baseline 2018-05-01 to 2018-05-31. No filters."
```

`--gemini` 与 `--mock-llm` 互斥。`--model MODEL_ID` 覆盖 `GEMINI_MODEL`，且必须与 `--gemini` 一起使用；默认模型 `gemini-3.8-flash`。

结构化输入不调用模型解析，唯一合法候选不调用模型。数据提前 blocked 且无 Claim 时也不会调用报告模型，因此 `--gemini` 不等于每次都有 API 请求，应查看 `llm_requests_succeeded` 和 Trace。

Gemini 仅接收所需的意图文本、合法路由候选或已验证 Claim，不自由查询数据库。报告阶段仅允许编排已有 Claim 的顺序，状态、警告和限制由程序保留。报告失败回退为确定性 Markdown，不掩盖数据阻断或失败的意图解析/路由。

## Output and Trace

JSON 外层含 `run_id`、`result`、`trace_path`、`execution_mode`。Gemini 模式额外含 `report`，模式元数据增加 `llm_requests_succeeded`、`report_rendering`。

本地 `logs/` 记录输入、Workflow 版本、State、Skills、路由、Evidence、警告、限制、停止原因及 `final_structured_result`。SQLite 还记录数据库指纹及 SQL 操作；报告渲染记录：

| 字段 | 含义 |
|---|---|
| `report_renderer` | `gemini` 或 `deterministic_fallback` |
| `provider_error_code` | 本次报告最近一次 HTTP 错误码；无错误为 null，恢复成功后也可能保留错误码 |
| `retry_count` | 本次报告的额外尝试次数，与 State 中 Skill 的重试次数分开 |

Mock + `--json` 不执行报告渲染，所以没有新增报告字段。Gemini 意图阶段失败保存独立 intent Trace，没有 Workflow result。

退出码 0 仍可能代表 partial 或边界终止；Workflow blocked/failed 退出 1；参数、路径和解析错误通常退出 2。须阅读真实状态，不能只看退出码。Trace 和真实数据库默认不提交 Git。

## Testing

未设置 `GEMINI_API_KEY` 时：

```bash
python -m unittest discover -s tests -v
```

已设置 Key 时，下面在子进程中移除它，确保整套测试离线，且不改变当前终端配置：

```bash
python -c "import os, subprocess, sys; env = os.environ.copy(); env.pop('GEMINI_API_KEY', None); raise SystemExit(subprocess.call([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'], env=env))"
```

可选 live 测试（安装 `.[gemini]` 并配置 Key 后会调用外部服务）：

```bash
python -m unittest tests.test_gemini_live -v
```

Live 使用 synthetic SQLite fixture，验证意图、路由和报告/回退，不是实际 Olist 数据验收。无 Key 自动 skip，未装 SDK 时部分 SDK 测试也 skip。CI 不需私人 Key；现有矩阵为 Windows / Ubuntu、Python 3.11 / 3.12，结果以实际 CI 为准。软件测试不等于系统化 Eval。

## Troubleshooting

| 现象 | 处理 |
|---|---|
| 找不到包或 tests | 进入项目根目录，用同一解释器执行 editable 安装 |
| 找不到 Knowledge / Workflow | 保留 `specs/`，不要只复制 Python 包 |
| SQLite schema 不兼容 | 核对原始 Olist 表结构及 Adapter，不是任意 SQLite 都兼容 |
| 已有数据库无法重新导入 | 已有库用只读审阅命令；重新导入选择新路径 |
| `data_quality_boundary` | 查看 Trace 的具体周期与缺失字段，不改业务口径或静默补值 |
| Key 不可访问 | 在运行程序的同一终端设置 `GEMINI_API_KEY`；不会自动读取 `.env` |
| 429 | Provider quota / rate limit；不要重复完整 E2E |
| 503 / 504 | Provider 临时不可用或请求超时，不等于业务实现必然有错 |
| report Provider 最终失败 | SDK 不重试，应用最多重试一次、间隔 2 秒，再采用确定性报告 |

每次 Gemini 请求超时 60 秒。报告回退不修复其他阶段的错误。独立指标字典实验见 [Gemini Tool Calling](docs/GEMINI_TOOL_CALLING.md)，其重试预算与主 Provider 不同。

Codex 操作说明见 [CODEX_USAGE.md](docs/CODEX_USAGE.md)。`run.ps1` 仅转发原有输入、Mock、JSON 参数和测试入口；SQLite/Gemini 使用 Python 命令。
