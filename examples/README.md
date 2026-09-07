# Mock / synthetic example

这是一组固定合成数据示例，仅用于展示功能，不代表真实经营分析。

- `gmv_input.json`：符合 Workflow Input 的固定周期请求。为保持合法 Schema，不添加备注字段。
- `demo_result.json`：完整业务 result 和 Mock 元数据；公开快照省略随机 run_id 与本机 trace_path，不是完整 CLI 输出外层。
- `demo_report.md`：由相同 result 生成的报告。

重新运行：

```text
python -m business_performance_agent --input examples/gmv_input.json --mock-llm --json
```

新运行返回独立 run_id 和 trace_path，日志写入被 Git 忽略的 logs/。示例快照中的核心 Claim 和 Evidence 来自 Runtime，未经人工添加解释。
