# Complete Journey — Portfolio Demo

直接阅读既有 Phase 3 Live 记录；本页没有重新调用模型或计算业务结果。原始 batch：`77101cc3-974a-46fe-9608-6390362b9449`。金额展示保留来源，版面摘录不替代完整 Evidence。

2017 年 1 月与 12 月均 31 天；gross_gmv 为零售商商品销售所得，不是顾客自付或货架标价。历史非相邻月份比较不支持季节因果推断。

## Demo A — Root Driver

> GMV变化主要由订单还是客单价驱动？当前周期2017-12-01至2017-12-31，基期2017-01-01至2017-01-31。

### Parsed intent

```json
{
  "metric_id": "gross_gmv",
  "current_period": {
    "start": "2017-12-01",
    "end": "2017-12-31"
  },
  "baseline_period": {
    "start": "2017-01-01",
    "end": "2017-01-31"
  },
  "filters": {},
  "context": {}
}
```

AOV 是根层最大同向内部贡献项，Orders 是另一项。更深数量路径缺少可用语义映射，因此保留根结论并以 partial 停止。

状态：`partial`；停止：`data_unavailable`。

### Structured result / evidence

```json
{
  "target": {
    "metric_id": "gross_gmv",
    "current_value": 421882.29,
    "baseline_value": 370886.93,
    "absolute_change": 50995.359999999986,
    "relative_change": 0.13749570522746646
  },
  "primary_driver": {
    "metric_id": "aov",
    "effect": 39669.85647708267,
    "aligned_share": 0.7779110977367881
  },
  "secondary_drivers": [
    {
      "metric_id": "orders",
      "effect": 11325.503522917295,
      "aligned_share": 0.22208890226321185
    }
  ],
  "diagnostic_path": [
    {
      "metric_id": "gross_gmv",
      "relationship_id": "gross_gmv_orders_aov",
      "dimension_id": null,
      "segment_id": null
    }
  ],
  "key_findings": [
    {
      "claim_id": "C0001",
      "claim": "gross_gmv 从 370886.93 变为 421882.29，变化 50995.359999999986（13.75%）。",
      "evidence_level": "direct",
      "evidence_refs": [
        "E0001"
      ]
    },
    {
      "claim_id": "C0004",
      "claim": "在 gross_gmv 的本层分解中，aov 是最大同向内部贡献项：effect=39669.9，占本层同向贡献 77.79%。",
      "evidence_level": "derived",
      "evidence_refs": [
        "E0004"
      ]
    }
  ]
}
```

### Warnings / limitations

- dataset_limitation
- Complete Journey public historical receipts; not a production real-time system.
- gross_gmv is retailer-received merchandise sales value, not customer out-of-pocket payment or shelf/list price.
- Transaction validity is approved at source-contract level; no physical payment_success column.
- household_id represents households, not individual customers; buyer/frequency counts use household entities.
- Refund lifecycle is unobserved; net_gmv and refund analysis unavailable.
- Quantity units/scales unresolved; units, UPO and realized unit price unavailable.
- channel, region, campaign and lifecycle customer_type unavailable; no proxy dimensions.
- Dataset first purchase is left-censored and not lifecycle first purchase.
- Calendar dates retain source clock with unknown timezone; 2018-01 is incomplete.
- Analysis stopped at decompose_aov: data_unavailable.


[完整 Actual 与 Evidence](runs/77101cc3-974a-46fe-9608-6390362b9449/drivers.json) · [原始报告](runs/77101cc3-974a-46fe-9608-6390362b9449/drivers.md) · [Trace 目录](runs/77101cc3-974a-46fe-9608-6390362b9449/traces)

## Demo B — Category

> 按品类分析GMV，哪个品类贡献最大？当前周期2017-12-01至2017-12-31，基期2017-01-01至2017-01-31。

### Parsed intent

```json
{
  "metric_id": "gross_gmv",
  "current_period": {
    "start": "2017-12-01",
    "end": "2017-12-31"
  },
  "baseline_period": {
    "start": "2017-01-01",
    "end": "2017-01-31"
  },
  "filters": {},
  "context": {
    "preferred_dimension": "category"
  }
}
```

请求 category 被保留为 preferred_dimension；路径是合法 GMV × category，不是 Orders × category。下表是已有贡献排名，份额属于品类本层同向贡献。COUPON/MISC ITEMS 仅是源类别标签，不能据此证明优惠券造成变化。

状态：`completed`；停止：`below_min_contribution`。

### Structured result / evidence

```json
{
  "target": {
    "metric_id": "gross_gmv",
    "current_value": 421882.29,
    "baseline_value": 370886.93,
    "absolute_change": 50995.359999999986,
    "relative_change": 0.13749570522746646
  },
  "primary_driver": {
    "metric_id": "aov",
    "effect": 39669.85647708267,
    "aligned_share": 0.7779110977367881
  },
  "secondary_drivers": [
    {
      "metric_id": "orders",
      "effect": 11325.503522917295,
      "aligned_share": 0.22208890226321185
    }
  ],
  "diagnostic_path": [
    {
      "metric_id": "gross_gmv",
      "relationship_id": "gross_gmv_orders_aov",
      "dimension_id": null,
      "segment_id": null
    },
    {
      "metric_id": "gross_gmv",
      "relationship_id": null,
      "dimension_id": "category",
      "segment_id": null
    }
  ],
  "key_findings": [
    {
      "claim_id": "C0001",
      "claim": "gross_gmv 从 370886.93 变为 421882.29，变化 50995.359999999986（13.75%）。",
      "evidence_level": "direct",
      "evidence_refs": [
        "E0001"
      ]
    },
    {
      "claim_id": "C0004",
      "claim": "在 gross_gmv 的本层分解中，aov 是最大同向内部贡献项：effect=39669.9，占本层同向贡献 77.79%。",
      "evidence_level": "derived",
      "evidence_refs": [
        "E0004"
      ]
    },
    {
      "claim_id": "C0006",
      "claim": "在 gross_gmv，维度 category 的本层分解中，COUPON/MISC ITEMS 是最大同向内部贡献项：effect=5252.17，占本层同向贡献 8.23%。",
      "evidence_level": "derived",
      "evidence_refs": [
        "E0006"
      ]
    }
  ]
}
```

已有品类贡献 Evidence `E0006`（只摘录前五项，完整排名见 Actual）：

```json
{
  "target_metric": "gross_gmv",
  "target_change": 50995.359999999986,
  "relationship_id": null,
  "dimension_id": "category",
  "closure_error": 1.4551915228366852e-11,
  "closed": true,
  "effects": [
    {
      "id": "COUPON/MISC ITEMS",
      "effect": 5252.170000000002,
      "role": "aligned_driver",
      "aligned_share": 0.0823491579083364
    },
    {
      "id": "SMOKED MEATS",
      "effect": 2779.62,
      "role": "aligned_driver",
      "aligned_share": 0.0435818654585
    },
    {
      "id": "CANDY - PACKAGED",
      "effect": 2691.86,
      "role": "aligned_driver",
      "aligned_share": 0.042205869994142296
    },
    {
      "id": "CHRISTMAS  SEASONAL",
      "effect": 2636.88,
      "role": "aligned_driver",
      "aligned_share": 0.04134383454940225
    },
    {
      "id": "BAKING NEEDS",
      "effect": 2609.52,
      "role": "aligned_driver",
      "aligned_share": 0.04091485510654871
    }
  ]
}
```

### Warnings / limitations

- dataset_limitation
- unknown_category
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


[完整 Actual 与 Evidence](runs/77101cc3-974a-46fe-9608-6390362b9449/category.json) · [原始报告](runs/77101cc3-974a-46fe-9608-6390362b9449/category.md) · [Trace 目录](runs/77101cc3-974a-46fe-9608-6390362b9449/traces)

## Demo C — Unsupported Channel

> 按渠道分析GMV。当前周期2017-12-01至2017-12-31，基期2017-01-01至2017-01-31。

### Parsed intent

```json
{
  "metric_id": "gross_gmv",
  "current_period": {
    "start": "2017-12-01",
    "end": "2017-12-31"
  },
  "baseline_period": {
    "start": "2017-01-01",
    "end": "2017-01-31"
  },
  "filters": {},
  "context": {
    "preferred_dimension": "channel"
  }
}
```

意图理解成功不意味着数据能力存在。channel 映射不可用，数据质量入场节点以 blocked / data_quality_boundary 停止，核心 Claim 为空，没有编造归因。

状态：`blocked`；停止：`data_quality_boundary`。

### Structured result / evidence

```json
{
  "target": {
    "metric_id": "gross_gmv",
    "current_value": null,
    "baseline_value": null,
    "absolute_change": null,
    "relative_change": null
  },
  "primary_driver": {
    "metric_id": null,
    "effect": null,
    "aligned_share": null
  },
  "secondary_drivers": [],
  "diagnostic_path": [],
  "key_findings": []
}
```

### Warnings / limitations

- unknown_channel
- dataset_limitation
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


[完整 Actual 与 Evidence](runs/77101cc3-974a-46fe-9608-6390362b9449/unsupported_channel.json) · [原始报告](runs/77101cc3-974a-46fe-9608-6390362b9449/unsupported_channel.md) · [Trace 目录](runs/77101cc3-974a-46fe-9608-6390362b9449/traces)

## Provenance

[源契约](../../../data/contracts/completejourney.json) · [一致性与只读验证](validation.json) · [准备与来源说明](README.md) · [真实数据契约与验证](../../../docs/COMPLETEJOURNEY.md)

源数据未打包；未匹配/缺失 category 保留 unknown，数量单位与退款生命周期等限制保留。四场景通过的是预定行为检查，不是四个完整无限深分析或独立因果 Eval。
