# Gemini Tool Calling — module 1

此入口只验证真实 Gemini 调用本地指标字典工具，不是完整 GMV 诊断，不读取经营数据。
主 GMV CLI 已支持 SQLite + Gemini，见 [Quick Start](../QUICKSTART.md)。本页是独立指标工具演示，其工具循环与重试策略不属于 GMV Workflow。

## Run

在已配置 Gemini 密钥的 Python 环境中，从项目根目录执行：

```powershell
python -m pip install -e ".[gemini]"
python -m business_performance_agent.app.gemini_tool_demo --question "请读取指标字典，解释 gross_gmv 的定义和口径。"
```

默认模型 gemini-3.8-flash；可用 --model 或 GEMINI_MODEL 更改。密钥从 GEMINI_API_KEY（优先）或 GOOGLE_API_KEY 读取，不从聊天、源码或日志获取。`.env.example` 是配置说明，程序不自动加载 .env 文件。

## What to inspect

输出应有模型解释、Tool called: True 和 Trace 路径。打开该 JSON，检查 events 中的 get_metric_definition、metric_id 参数及返回的原始指标定义。
如果 Tool called: False，模型没有调用工具，不能算作工具闭环验收通过。

## Code concepts

- Function declaration（函数声明）：用 name、description、parameters 告诉模型有哪些工具；声明本身不执行 Python。
- Dictionary（字典）：`{"metric_id": "gross_gmv"}` 用键和值传参数；execute 只允许该参数并读取 KnowledgeLoader。
- Manual tool loop（手动工具循环）：读取 function_call，校验并执行，再用 FunctionResponse 回传结果和同一个 call ID；保留原模型 content 以维持协议上下文。
- Dependency extra（可选依赖组）：`.[gemini]` 安装项目及 Gemini SDK；原 Mock 模式仍不需要第三方运行时依赖。

最多允许两轮工具调用、每轮四个调用；最后一轮禁用工具。AUTO 允许模型选择不调用。这里只记录可检查的调用与工具结果，不保存完整 API response 或思考内容。
模型解释尚未经过现有 GMV Evidence Validator，因此不能作为正式诊断结论；原始工具返回的指标字典才是定义依据。

## Tests

```powershell
python -m unittest tests.test_gemini_tool_demo -v
```

测试使用接口替身，不消耗 API，不代表真实模型已验收。
协议参考：[Gemini Generate Content API](https://ai.google.dev/api/generate-content)。

模型请求遇到 HTTP 500/502/503/504 时最多重试两次，分别等待 2、4 秒；关闭 SDK 内层重试以避免重叠。重试只重发当前模型请求，不重复执行本地工具，失败尝试写入 Trace。持续失败仍返回 failed，不伪造最终回答。
