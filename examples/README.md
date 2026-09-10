# Synthetic examples

- `gmv_input.json`：固定 Mock 周期请求，也可用于覆盖相同周期的自建 SQLite 数据。
- `demo_result.json`：Mock 业务结果与来源元数据快照，省略随机 run_id 和本机 trace_path。
- `demo_report.md`：相同结果的公开内容快照，排版可能与当前 renderer 不同。

这些文件均不代表真实业务。重新运行：

```bash
python -m business_performance_agent --input examples/gmv_input.json --mock-llm --json
```

Eval support 的独立 SQLite smoke 生成方法见 [Quick Start](../QUICKSTART.md#sqlite-smoke)。其数据规模与上述 Mock 快照不同，不应直接比较金额。Golden Set 位于 evals，不是这里的演示快照；尚未集成 Runner / Graders。
