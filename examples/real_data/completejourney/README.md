[直接阅读三个 Portfolio Demo](portfolio.md)（无需下载数据或配置 API）。

# Complete Journey real-data demo

Real public historical retail receipts; not production or real-time data. The dataset-specific approved `gross_gmv` is retailer-received merchandise sales value, not customer out-of-pocket payment or shelf price.

## Prepare and run

From the repository root, with the two original files under `data/raw/completejourney/`:

```powershell
python -m pip install pandas pyreadr
python scripts/prepare_completejourney.py
python scripts/run_completejourney_demo.py
```

The first command installs preparation dependencies in your active Python environment. Preparation preserves source IDs and rows, left joins products and saves hashes/reconciliation in `data/processed/completejourney/preparation_manifest.json`. SQLite is local and ignored by Git; no raw data is bundled into the demo.

For the explicit paid four-scenario run, configure `DEEPSEEK_API_KEY` in your local environment, then:

```powershell
python scripts/run_completejourney_demo.py --live
```

No key belongs in the repository. Each run creates a new directory under `runs/` with the original questions, parsed intents, capability contract reference, structured results, evidence, Markdown reports and traces. This is not a 20-case Eval.

Scenarios: overall GMV change; Orders versus AOV contribution; category attribution; unsupported channel request. The January/December 2017 comparison uses two 31-day months, omits the incomplete January 2018 tail and makes no seasonal causal claim.

## Capability boundary

- Supported: GMV, Orders, AOV; product/category receipt analysis subject to existing contribution legality.
- Household is not an individual customer. Buyer/frequency results use households.
- Quantity-based metrics are unavailable due to unresolved units/scales; raw values are preserved without conversion.
- Refunds/net_gmv, channel, region and campaign attribution are unavailable.
- No lifecycle new/returning labels: dataset first purchase is left-censored.
- Unsupported explicit dimensions stop through the data-quality boundary with limitations. Unsupported deeper quantity paths retain the reliable root analysis and stop.

See the [approved contract](../../../data/contracts/completejourney.json), [dataset validation](../../../docs/COMPLETEJOURNEY.md) and [saved demos](portfolio.md) for interpretation, run IDs and evidence.

## Data source and attribution

Complete Journey is the historical retail dataset distributed by the completejourney project, originating from dunnhumby. Obtain transaction and product data by following the [official guide](https://bradleyboehmke.github.io/completejourney/articles/completejourney.html) and [transaction reference](https://bradleyboehmke.github.io/completejourney/reference/transactions.html). Place the original `transactions.rds` and `products.rda` locally under `data/raw/completejourney/`; they are not redistributed here. The source references are not a new license grant; check upstream terms before obtaining or redistributing data. No dataset license is invented by this repository.
