# GMV 诊断报告

- GMV 诊断状态：blocked
- 停止原因：data_quality_boundary

## 警告

- unknown_channel
- dataset_limitation

## 限制

- Required semantic mappings missing: channel
- channel unknown/unattributed share=1; values retained. No frozen high-share cutoff exists.
- Complete Journey public historical receipts; not a production real-time system.
- gross_gmv is retailer-received merchandise sales value, not customer out-of-pocket payment or shelf/list price.
- Transaction validity is approved at source-contract level; no physical payment_success column.
- household_id represents households, not individual customers; buyer/frequency counts use household entities.
- Refund lifecycle is unobserved; net_gmv and refund analysis unavailable.
- Quantity units/scales unresolved; units, UPO and realized unit price unavailable.
- channel, region, campaign and lifecycle customer_type unavailable; no proxy dimensions.
- Dataset first purchase is left-censored and not lifecycle first purchase.
- Calendar dates retain source clock with unknown timezone; 2018-01 is incomplete.
- Analysis stopped at terminate_blocked: data_quality_boundary.