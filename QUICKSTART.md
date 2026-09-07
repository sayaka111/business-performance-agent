# Quick Start — Business Performance Agent 0.1.0

目标：下载源码 → 创建环境 → 安装 → Smoke Test → Mock GMV 诊断 → 在 Codex 中使用。

**当前是功能原型。所有示例使用 Mock 数据，不代表真实经营情况。**

## 1. Prerequisites

| 项目 | 要求 |
|---|---|
| Python | 3.11+，具备标准库 venv 与 pip；本次验证版本为 Windows Python 3.12.14 |
| 操作系统 | 核心 Python 代码无特定系统依赖，适用于 Windows / macOS / Linux；run.ps1 仅用于 Windows |
| Codex | 命令行运行不需要；只有“让 Codex 操作 Agent”时需要 Codex |
| OpenAI API Key | Mock 模式不需要；当前没有真实模型 Provider |
| 数据库 | 不需要；当前没有真实数据库连接 |
| 网络 | 首次 pip 安装可能下载 setuptools 构建依赖；安装后的 Mock 运行无需网络 |

本次实际执行验证在 Windows，未宣称在 macOS / Linux 原生系统完成测试。

## 2. Download / Clone

从维护者提供的真实 repository 地址使用平台的 Clone 功能，或 Download ZIP 后完整解压。也可解压维护者提供的源码压缩包。当前未提供公开仓库 URL，不要照抄不存在的 GitHub 地址。

进入解压/clone 后包含 `pyproject.toml`、`AGENTS.md` 和本文档的目录。以下命令均从此根目录运行。必须保留 `specs/` 规范目录；不要只复制 Python 包。发布源码不包含 `.venv`、`.env`、本机日志和构建产物；examples/ 保留一组明确标注的 synthetic 示例。

## 3. Create Virtual Environment

Windows / PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

如果系统只提供 Python Launcher，可用已安装的 Python 3.11+ 完整路径创建环境。若 PowerShell 阻止激活脚本，不必修改全局执行策略：后续命令中的 `python` 可直接替换为 `.\.venv\Scripts\python.exe`。

macOS / Linux（对应 POSIX 路径）：

```bash
python3 -m venv .venv
source .venv/bin/activate
```

打开新的终端后重新激活已有环境，不需要重复创建。

## 4. Install Dependencies

唯一推荐安装方法，在已激活环境和项目根目录执行：

```text
python -m pip install -e .
```

`pyproject.toml` 是唯一依赖管理入口；没有 requirements.txt。无第三方运行时依赖；pip 会按 pyproject 安装构建所需的 setuptools，并注册项目入口。测试使用标准库 unittest，不需额外测试框架。

此版本支持 **源码目录 + editable 安装**。保留该目录；移动源码目录后，在新位置重新执行相同安装命令。当前不将非 editable wheel 作为独立交付物，也不发布到 PyPI。

Mock 模式无需环境变量、API Key 或数据库配置。当前程序不读取 `.env`；真实 Provider / Adapter 接入后再定义相应配置。

## 5. Smoke Test

复用现有入口集成测试，一条命令：

```text
python -m unittest discover -s tests -p test_cli_integration.py -v
```

测试实际调用 CLI → 原 Runtime → 7 个 Skill → Mock Dataset/Query Tool，验证 Knowledge/Relationship、Workflow/State、合法终止、Output Schema、Mock 标识、Trace 和规范文件不变。正常末尾显示 `OK`；非 Windows 会跳过 PowerShell 专用测试。Smoke Test 不是 Eval。

## 6. Run Mock GMV Diagnosis

以下单行命令可在 PowerShell、macOS 或 Linux 终端使用：

```text
python -m business_performance_agent --input examples/gmv_input.json --mock-llm --json
```

未提供 `--input` 或 `--question` 时会执行内置 Mock 示例；建议显式传入上述示例文件，以明确使用的周期。

输入来自 [gmv_input.json](examples/gmv_input.json)，使用现有 Workflow 字段，**不添加 intent 字段**。Mock 固定比较 2026-08-24～2026-08-30 与 2026-08-31～2026-09-06，不随今天日期变化。

应看到：`execution_mode.dataset="mock"`、`llm="mock"`、`real_business_data=false`；`result.workflow_status="completed"`；GMV 10,000 → 7,350，relative_change=-0.265；primary_driver 为 orders，stop_reason 为 target_coverage_reached。

输出包含新 `run_id` 与 `trace_path`。对应 `logs/<run_id>.json` 记录 State、Skill 调用、路由、Evidence 和 `final_structured_result`。结果与 Trace 应一致。

需要自然语言报告时移除 `--json`；首行标明 MOCK DATA。去掉 `--mock-llm` 表示 LLM 未配置，多候选可能停在证据边界。不要只看退出码，须检查 workflow_status、warnings、limitations 与 stop_reason。

已有 [Schema Mapping](business_performance_agent/data_contract/schema_mapping.example.json) 展示 Semantic ID → Mock Physical Field，直接复用。仅改 mapping 不会接通真实数据库，也不得反向修改 Knowledge。

## 7. Use with Codex

1. 打开 Codex，将解压/clone 后的 repository 根目录作为项目打开。
2. 让 Codex 从该目录开始工作，读取根目录 `AGENTS.md`；详细说明见 [Codex Usage](docs/CODEX_USAGE.md)。
3. 输入：

```text
Use the repository's Business Performance Agent to run the existing mock GMV diagnosis workflow.
Do not bypass the agent runtime.
```

Codex 应调用现有 CLI，获取 Runtime structured output，再呈现结果和 Trace。开发请求按开发任务处理。Mock 只验证功能；真实分析必须先接入真实数据源，不能用 Mock 冒充真实数据或自行补充外部因果。

## 8. More checks / troubleshooting

全部 unit / integration tests：

```text
python -m unittest discover -s tests -v
```

单独运行 Runtime 测试：

```text
python -m unittest tests.test_runtime -v
```

测试覆盖计算、Knowledge/State、Skills、路由与停止策略、接口和 CLI；包括 Orders × Category / Product 禁止严格贡献。

| 现象 | 处理 |
|---|---|
| 找不到 python | 使用标准 Python 3.11+ 或完整解释器路径，不依赖作者机器的 Codex Python |
| pip 下载构建依赖失败 | 检查配置的包索引网络访问；Mock 运行本身无需联网 |
| 找不到 Knowledge / Workflow | 完整解压并保留规范目录，按 editable 安装；不要只复制 Python 包 |
| 无效 JSON / 文件路径 | 从项目根目录运行，输入 UTF-8 JSON（可带 BOM） |
| invalid_input / blocked | 检查现有 Schema，不改 Stop Policy 或用户的业务周期 |
| 需要真实数据或模型 | 当前未接入，需另行授权开发 |

Windows 的已有 `run.ps1` 也可使用，Python 顺序为已激活环境 → 项目 `.venv` → PATH Python。跨平台统一以 `python -m` 为主，不新增重复 wrapper。
