# Data Sources

## Runtime adapters

`MockDatasetAdapter` 使用固定内存 fixture，映射为 `mock_schema_mapping.json`。`SQLiteDatasetAdapter` 使用显式 `--mapping` JSON 读取单个规范化明细表。两者复用原有 `SemanticRecordAdapter` 的聚合、有效订单筛选、维度分类与质量检查，公式继续读取 Knowledge。

SQLite 不是自动 ETL 工具。外部多表数据应先转换成一致的订单明细粒度，金额为商品金额，排除运费、税费；时间按既有支付口径。适配不能改变冻结定义。

## Mapping contract

JSON 必须含 `dataset_id`、`table`、`semantic_mapping`、`capabilities`、`complete_periods`、`data_origin`。Semantic ID 指向单表列名，标识符严格校验，无 SQL 表达式或自动猜测。

- `complete_periods`: `[{"start":"YYYY-MM-DD","end":"YYYY-MM-DD"}]`，声明可完整比较的周期；不得为跑通随意声明。
- `data_origin`: synthetic / public_historical / user_supplied，由数据提供者明确声明，不由 SQLite 存在推断。
- `payment_success`: 0/1；支付日期与首购日期使用 ISO 日期；金额、数量使用有限数值。
- 订单明细 ID 唯一；跨明细重复订单 ID 允许，但订单属性须一致。
- `customer_type` 从稳定 customer_id、first_valid_paid_at 和分析周期派生；不要写入提示分类或覆盖规则。
- 可选能力只能在来源可靠时声明；缺失字段、unknown 和数据质量问题如实保留。

参考 [canonical mapping](../evals/support/canonical_mapping.json) 展示字段契约；其 `data_origin=synthetic` 仅适用于合成数据，不应照抄到真实数据声明。日期转换、复杂 JOIN 不在当前映射能力内。

SQLite 只读连接、query_only、authorizer、表列白名单、超时和 max_rows 限制保持有效。默认读取上限 250,000 行、15 秒；超限拒绝，不截断成完整结果。文件变更会停止运行。当前为本地快照适配，不是生产权限系统。

## Eval-only synthetic path

`evals/support/fixture_builder.py` 接收显式记录与周期，生成新 SQLite 和 mapping sidecar，不读取 Golden Set、Expected 或 case_id。`CanonicalEvalSQLiteAdapter` 仅用于 Eval support，要求 synthetic 契约；正式 Runtime 不导入该模块。

支持 order_id、order_item_id、customer_id、paid_at、merchandise_amount、quantity、channel、campaign、category、product、region，以及按冻结规则计算的 customer_type。可生成含 null 的数据质量 fixture。构建器不会补答案、注入提示或根据 Case 特判。

生成数据库与结果放入被忽略的 `evals/results/`。命令见 [Quick Start](../QUICKSTART.md#sqlite-smoke)。Offline Runner / Graders 见 [Eval 文档](../evals/README.md)。Case 构造器只支持已说明的限定语法，新增文字构造要求需验证。
