"""Reproducible RDS/RDA -> SQLite preparation under the approved source contract.

Install pandas and pyreadr in the preparation environment. Raw files are read-only.
Run from any directory: python scripts/prepare_completejourney.py
"""

import calendar
import hashlib
import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(root=ROOT):
    import pyreadr
    import pandas as pd

    contract = json.loads(
        (root / "data/contracts/completejourney.json").read_text(encoding="utf-8")
    )
    if contract["gate_a"] != "PASSED":
        raise ValueError("Semantic approval required")
    raw = root / "data/raw/completejourney"
    hashes = {name: digest(raw / name) for name in ("transactions.rds", "products.rda")}
    t = next(iter(pyreadr.read_r(str(raw / "transactions.rds")).values()))
    products = next(iter(pyreadr.read_r(str(raw / "products.rda")).values()))
    assert not t.duplicated(["basket_id", "product_id"]).any()
    assert not products.product_id.duplicated().any()
    joined = t.merge(
        products, on="product_id", how="left", validate="many_to_one", indicator=True
    )
    assert len(joined) == len(t)
    for field in ("household_id", "store_id", "transaction_timestamp"):
        assert t.groupby("basket_id")[field].nunique(dropna=False).max() == 1
    joined["order_item_id"] = joined.basket_id + ":" + joined.product_id
    joined["paid_date"] = joined.transaction_timestamp.dt.strftime("%Y-%m-%d")
    joined["category"] = joined.product_category.fillna("unknown")
    joined["transaction_timestamp"] = joined.transaction_timestamp.astype(str)
    joined["product_join_status"] = joined["_merge"].astype(str)
    joined = joined.drop(columns="_merge")
    destination = root / "data/processed/completejourney"
    destination.mkdir(parents=True, exist_ok=True)
    database = destination / "completejourney.sqlite"
    temp = database.with_suffix(".building.sqlite")
    if temp.exists():
        raise FileExistsError(
            "Previous incomplete build exists; inspect before replacing"
        )
    with closing(sqlite3.connect(temp)) as db:
        joined.to_sql("order_items", db, index=False, chunksize=10000)
        db.execute("CREATE UNIQUE INDEX item_key ON order_items(order_item_id)")
        db.execute("CREATE INDEX paid_date_index ON order_items(paid_date)")
        count, amount = db.execute(
            "SELECT COUNT(*), SUM(sales_value) FROM order_items"
        ).fetchone()
        assert count == len(t)
        assert abs(amount - float(t.sales_value.sum())) < 0.0001
        months = db.execute(
            "SELECT substr(paid_date,1,7), SUM(sales_value), COUNT(DISTINCT basket_id) FROM order_items GROUP BY 1 ORDER BY 1"
        ).fetchall()
        db.commit()
    assert all(digest(raw / name) == h for name, h in hashes.items())
    os.replace(temp, database)
    mapping = dict(
        dataset_id="completejourney_v1",
        table="order_items",
        data_origin="public_historical",
        semantic_mapping={
            "order_item_id": "order_item_id",
            "order_id": "basket_id",
            "paid_at": "paid_date",
            "customer_id": "household_id",
            "product": "product_id",
            "category": "category",
            "merchandise_amount": "sales_value",
            "valid_order_item_merchandise_amount": "sales_value",
        },
        capabilities={"sessions": False},
        complete_periods=[
            dict(
                start=f"2017-{m:02d}-01",
                end=f"2017-{m:02d}-{calendar.monthrange(2017, m)[1]}",
            )
            for m in range(1, 13)
        ],
        source_contract=dict(
            transaction_validity=contract["transaction_validity"],
            approval_reference=contract["approval"],
            contract_id=contract["contract_id"],
            limitations=contract["limitations"],
        ),
        read_limits=dict(max_rows=1500000, query_timeout=60),
    )
    mapping_dir = root / "data/mappings"
    mapping_dir.mkdir(parents=True, exist_ok=True)
    (mapping_dir / "completejourney.json").write_text(
        json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    manifest = dict(
        input_hashes=hashes,
        output_rows=count,
        raw_sales_value_sum=float(t.sales_value.sum()),
        sqlite_sales_value_sum=amount,
        product_join_matched=int((joined.product_join_status == "both").sum()),
        unknown_category=int((joined.category == "unknown").sum()),
        time_min=str(t.transaction_timestamp.min()),
        time_max=str(t.transaction_timestamp.max()),
        monthly_observations=months,
        output_sha256=digest(database),
        contract_sha256=digest(root / "data/contracts/completejourney.json"),
    )
    (destination / "preparation_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest), flush=True)
    return manifest


if __name__ == "__main__":
    prepare()
