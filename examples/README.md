# Example inputs and synthetic snapshots

## Mock / synthetic example

这是一组固定合成数据示例，仅用于展示功能，不代表真实经营分析。

- `gmv_input.json`：符合 Workflow Input 的固定周期请求。为保持合法 Schema，不添加备注字段。
- `demo_result.json`：完整业务 result 和 Mock 元数据；公开快照省略随机 run_id 与本机 trace_path，不是完整 CLI 输出外层。
- `demo_report.md`：相同 result 的公开报告内容快照；当前 renderer 的 Markdown 排版可能不同。

重新运行：

```text
python -m business_performance_agent --input examples/gmv_input.json --mock-llm --json
```

新运行返回独立 run_id 和 trace_path，日志写入被 Git 忽略的 logs/。示例快照中的核心 Claim 和 Evidence 来自 Runtime，未经人工添加解释。

## SQLite input

`olist_input.json` 仅定义 2018 年 6 月与 5 月的比较请求，不包含真实数据，也不保证诊断完成。先按 [Quick Start](../QUICKSTART.md) 准备兼容 Olist 原始表结构的 SQLite 文件：

```text
python -m business_performance_agent --database data/olist_raw.db --input examples/olist_input.json --mock-llm --json
```

配置 Gemini 后可将 `--mock-llm` 替换为 `--gemini`。相同的数据质量检查仍然生效；缺失商品行等问题可能使分析 blocked，不把该输入视为真实数据验收通过的证据。

## Test fixtures

测试中的合成 SQLite 数据与脱敏报告 fixture 用于重复验证接口和失败路径，不是用户原始订单，也不证明任意真实数据均可通过。范围见 [Data Sources](../docs/DATA_SOURCES.md)。
