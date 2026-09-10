# Codex Usage

Codex 可作为项目操作入口，正式分析必须调用既有 CLI，不能自行替代 Runtime 取数、计算或规划。首先阅读 [AGENTS.md](../AGENTS.md)。CLI 不依赖 Codex 安装。

## Inputs and runtime modes

```bash
python -m business_performance_agent --input examples/gmv_input.json --mock-llm --json
```

SQLite 加 `--database PATH --mapping PATH`；Gemini 使用 `--gemini` 代替 `--mock-llm`。自然语言通过 `--question TEXT` 提供，与 `--input` 互斥。Gemini 模型可用 `--model` 覆盖，需已安装可选依赖并配置 Key。

DeepSeek 使用 `--provider deepseek`，通过 `DEEPSEEK_API_KEY` 配置，`--model` 同样可覆盖所选 Provider。真实 API 是显式 opt-in；首次使用按 [离线 Quick Start](../QUICKSTART.md) 操作。

输入字段是 metric_id、current_period、baseline_period、filters、可选 context；不接受 intent 字段。不得静默替换用户周期或把 synthetic 数据当作用户真实数据。无 Provider 时，多候选可能在未配置边界停止。

`run.ps1` 支持 -MockLLM、-Gemini、-Database、-Mapping、-Model、-InputFile、-Question、-Json、-Test，统一转交 CLI，不是另一套 Runtime。

## Results

以 result 为业务结论依据，检查 workflow_status、stop_reason、warnings、limitations、failed_branches 和 evidence_refs。execution_mode 的 data_backend 与 data_origin 分开说明数据位置和来源；不把 SQLite 自动视为真实数据。

退出码 0 不保证完整完成；blocked/failed 返回 1；输入/路径错误通常返回 2。新运行必须使用新 run_id/trace_path，不用旧日志冒充成功。

## Evidence and fallback

只总结 direct / derived Evidence 支持的内部贡献，不补外部因果或强业务动作。Gemini 报告失败可使用确定性 Markdown，保留已有状态与限制；这不证明 Provider 已恢复或其他失败已修复。

## Software tests and Eval

普通 discovery 不调用真实 API。Live 必须显式运行 tests.test_gemini_live，并同时设置 BPA_RUN_LIVE_TESTS=1 与 GEMINI_API_KEY。软件测试、live 服务验证与正式 Eval 是不同任务。

Golden Set 与 Offline Runner / Graders 已提供，见 [Eval 文档](../evals/README.md)。不得将 Expected、case_id 或案例提示注入 Agent。完整命令见 [Quick Start](../QUICKSTART.md)。
