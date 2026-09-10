# GMV 诊断报告

- GMV 诊断状态：completed
- 停止原因：below_min_contribution

## 分析发现

- gross_gmv 从 370886.93 变为 421882.29，变化 50995.359999999986（13.75%）。
- 在 gross_gmv 的本层分解中，aov 是最大同向内部贡献项：effect=39669.9，占本层同向贡献 77.79%。
- 在 gross_gmv，维度 category 的本层分解中，COUPON/MISC ITEMS 是最大同向内部贡献项：effect=5252.17，占本层同向贡献 8.23%。

## 警告

- dataset_limitation
- unknown_category

## 限制

- Complete Journey public historical receipts; not a production real-time system.
- gross_gmv is retailer-received merchandise sales value, not customer out-of-pocket payment or shelf/list price.
- Transaction validity is approved at source-contract level; no physical payment_success column.
- household_id represents households, not individual customers; buyer/frequency counts use household entities.
- Refund lifecycle is unobserved; net_gmv and refund analysis unavailable.
- Quantity units/scales unresolved; units, UPO and realized unit price unavailable.
- channel, region, campaign and lifecycle customer_type unavailable; no proxy dimensions.
- Dataset first purchase is left-censored and not lifecycle first purchase.
- Calendar dates retain source clock with unknown timezone; 2018-01 is incomplete.
- category unknown/unattributed share=0.00479478; values retained. No frozen high-share cutoff exists.
- 当前证据仅定位到 gross_gmv 在 category 的 COUPON/MISC ITEMS 内部贡献；无法据此判断其变化的进一步外部原因，贡献归因不证明因果关系。