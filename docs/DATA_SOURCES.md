# Data sources and mapping

## Supported adapters

| 数据源 | Adapter / Query Tool | 适用范围 |
|---|---|---|
| Synthetic Mock | MockDatasetAdapter / MockQueryTool | 固定数据、离线开发、CI、演示 |
| Olist raw SQLite | SQLiteDatasetAdapter / SQLiteQueryTool | 真实历史数据、本地只读分析，取决于质量检查 |

代码位于 `business_performance_agent/data_contract/` 和 `business_performance_agent/tools/`。主 CLI 通过 `--database PATH` 选择 SQLite，不传则选择 Mock。数据库不随公开源码分发。

## Olist contract

`olist_raw.py` 导入 orders、order_items、order_payments、customers、products 五张原始表，保留来源 SHA-256 和行数。目标已存在时拒绝覆盖；原 CSV 不变，分析时只读。命令见 [QUICKSTART](../QUICKSTART.md#b-sqlite-mode)。

| Semantic ID | Olist 实现 |
|---|---|
| order_id | orders.order_id |
| order_item_id | order_id 与 order_item_id 的复合键 |
| customer_id | customers.customer_unique_id，跨订单稳定身份 |
| paid_at | order_approved_at 的支付审批日期，不用下单/配送日期替代 |
| payment_success | 审批时间非空；已审批的取消订单仍保留 |
| merchandise_amount | order_items.price，不含 freight_value |
| quantity | 每条商品明细为一件 |
| category / product | 商品品类 / 商品 ID，未知值保留 |

支付表不与明细做一对多展开，避免重复计数；payment_value 不被当作商品金额。指标公式仍来自 Knowledge，不在映射中重定义。

[olist_mapping.json](../business_performance_agent/data_contract/olist_mapping.json) 保存映射说明、能力与限制；实际 SQL/转换由 [sqlite_adapter.py](../business_performance_agent/data_contract/sqlite_adapter.py) 实现。没有运行时任意映射配置或 `--mapping` 参数。更换物理 Schema 需要适配数据层代码，不能只改 JSON 或让 LLM 猜字段。

## Availability and quality

Olist Adapter 不声明完整客户生命周期首购信息，因此禁用 customer_type、新老客指标及依赖它们的关系；渠道、Campaign、确认退款、Session 和实际配送地区也不可用。不用客户所在地冒充实际配送地区。

检查源主键、范围内必需值、重复关联、日期范围、unknown 与可选能力。缺少审批时间的商品订单无法可靠归属周期时会阻断；范围内已审批订单缺明细时不会补零。已审阅的真实数据存在这些问题，所以默认 Olist 周期请求可能被阻断；synthetic SQLite 测试通过不能替代真实数据验收。

当前比较范围要求处于已观察支付日期的内部，但这本身不证明生产级完整性。数据库指纹、只读策略和 Trace 用于追溯，不是生产权限或数据治理系统。

## Historical processed import

`olist_import.py` 是独立 processed CSV staging/审阅工具，不是主 CLI 的 Olist raw Adapter 输入。其来源只含已交付订单和下单时间；生成的旧 `data/olist.db` 不能当作这里的 `data/olist_raw.db` 使用。

## Public examples

[examples/README.md](../examples/README.md) 区分 synthetic 快照和仅含周期的 Olist 请求。真实 CSV、SQLite、Key 和本机 Trace 不作为公开示例提交；`.env.example` 不含真实 Key，也不会自动加载。
