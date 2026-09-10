# Complete Journey Dataset Contract v1

Approved dataset-specific contract. Machine-readable definition: [completejourney.json](../data/contracts/completejourney.json).

Frozen Knowledge is unchanged. The interpretation below is an explicit dataset contract, not a schema-name guess.

## Approved interpretation

- `basket_id` identifies an observed completed purchase/receipt and supplies `order_id`.
- `transaction_timestamp` supplies `paid_at` under the approved source contract. SQLite preserves the full original timestamp and derives a calendar date for the existing day-level adapter. Source timezone is unspecified; no timezone conversion is invented.
- `sales_value` supplies the merchandise amount used by `gross_gmv`: **retailer-received merchandise sales value**. It is not customer out-of-pocket payment or shelf/list price. No discount is added back or subtracted.
- Validity is a dataset-level assertion that the source universe consists of completed purchase receipts. The adapter evaluates the semantic validity predicate from this approved contract, not from a synthetic physical `payment_success` column. There is no such column in the prepared table or mapping.
- `basket_id × product_id` uniquely identifies an observed receipt row. This may represent a product aggregated within a basket rather than an individual scanner event.
- `household_id` is retained as the customer entity at household level. `buyers` and `orders_per_buyer`, where reached, count households, not individuals; they remain explicitly qualified partial capabilities.

Authoritative supporting descriptions: [Complete Journey user guide](https://bradleyboehmke.github.io/completejourney/articles/completejourney.html) and [transaction reference](https://bradleyboehmke.github.io/completejourney/reference/transactions.html). The dataset-specific equivalence and receipt-validity interpretation are user-approved, not inferred solely from field names.

## Capabilities and limitations

Core supported metrics: gross_gmv, orders, aov. Product/category describe receipt products. Their strict contribution support remains controlled by frozen Knowledge; no strict Orders×Category attribution is enabled.

Quantity is retained only as raw source information. Units, units_per_order and average_realized_unit_price have no metric mapping because mixed scales/units remain unresolved. No refunds or net_gmv are available; the refund lifecycle is unobserved, not assumed zero. Channel, campaign, region and lifecycle customer_type are unavailable. No store, coupon or category proxy is substituted.

Product metadata uses a many-to-one left join. Every transaction and raw product ID is preserved. Unmatched or null categories become `unknown` for analysis while original metadata and join status remain in SQLite. Outliers and zero values are not deleted.

The 2017 calendar months are the approved observed comparison periods within the supplied historical snapshot. This does not assert that every real-world purchase of these households is observed. All source rows remain stored, including the incomplete 2018-01 tail, which is not declared a complete month. Demo uses January and December 2017, both 31 days; nonadjacent seasonal comparison is descriptive, not causal.

Household first purchase within this snapshot is left-censored, so no `first_valid_paid_at` or formal new/returning customer mapping is created. Payment status, refunds, attribution dimensions and physical quantity conversions are not invented.

## Adapter expression

The existing SQLite mapping accepts optional `source_contract` and `read_limits` metadata. Legacy physical-payment mappings retain their existing behavior. Source-contract validity requires an explicit approval reference and cannot coexist with a physical payment mapping. Dataset limitations flow through the existing data-quality Skill into Workflow limitations and reports. An explicitly requested unavailable dimension is rejected through the existing data-quality boundary.

The 1,500,000-row read limit is an explicit local snapshot allowance, not an unlimited query. SQLite remains read-only. Period and dimension caches operate on that immutable snapshot; snapshot changes still fail safely. This MVP loads the mapped snapshot into memory and is not a production-scale database query engine.

## Verified snapshot and preparation

The supplied snapshot contains 1,469,307 transaction rows. Basket/product pairs are unique; each basket has one household, store and timestamp. Products join many-to-one, preserving all receipt rows. There are 4,836 unmatched transaction rows and 7,045 missing/unknown category rows in total, including matched products with null category. Both raw and prepared sales totals are 4,596,039.58.

Two completed builds produced identical SQLite SHA-256 hashes. Read-only verification rejected a write, confirmed no physical payment_success column, and matched the saved source and database hashes. The 2018-01 tail has 534 rows and is excluded from complete periods, not deleted. These are recorded snapshot checks, not a guarantee about all real-world household purchases.

Evidence: [validation.json](../examples/real_data/completejourney/validation.json), [preparation manifest](../data/processed/completejourney/preparation_manifest.json), [preparation script](../scripts/prepare_completejourney.py).

## End-to-end demonstration

The saved four-scenario offline and DeepSeek runs agree on targets and primary drivers; the Live batch recorded seven successful requests with no retries. Root diagnosis is partial when deeper quantity data is unavailable; explicit channel is blocked with no core claims. These are bounded application checks, not a new benchmark or proof of causality. [Read the three selected demos](../examples/real_data/completejourney/portfolio.md).
