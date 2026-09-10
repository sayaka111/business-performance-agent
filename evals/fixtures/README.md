# Synthetic fixture contract

数据库由 support/fixture_builder.py 从显式记录确定性生成，不包含真实数据或 Expected。
固定契约见 ../support/canonical_mapping.json。不要将 case_id、评价重点、提示答案写入记录、映射、prompt 或 workflow state。
customer_type 从 first_valid_paid_at 与分析周期派生。Golden Set 数据由 case_fixture.py 编译 fixture_spec 后生成到本目录，数据库和 mapping sidecar 被 Git 忽略；独立 smoke 仍可生成到 results/。
