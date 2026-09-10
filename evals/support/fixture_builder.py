"""Build synthetic records only; never reads cases, expected answers or prompts."""

import argparse
import json
import sqlite3
from contextlib import closing
from pathlib import Path

from business_performance_agent.data_contract.sql_utils import quote
from business_performance_agent.models.schemas import Period

MAPPING_PATH = Path(__file__).with_name("canonical_mapping.json")


def build_fixture(database, rows, complete_periods):
    """Write explicit semantic records to a new database and mapping sidecar.

    Rows may intentionally contain nulls for data-quality testing. No generated
    ground truth, case identifiers or instructions are accepted as columns.
    Customer type is derived at query time from first_valid_paid_at and period.
    """
    path = Path(database).resolve()
    sidecar = path.with_suffix(".mapping.json")
    if path.exists() or sidecar.exists():
        raise FileExistsError("Fixture destination already exists")
    mapping = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
    periods = [Period(**period) for period in complete_periods]
    mapping["complete_periods"] = [dict(start=p.start, end=p.end) for p in periods]
    columns = sorted(set(mapping["semantic_mapping"].values()))
    rows = list(rows)
    for row in rows:
        if set(row) - set(columns):
            raise ValueError(
                "Unknown fixture fields; only canonical records are allowed"
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with closing(sqlite3.connect(path)) as db, db:
            numeric = {"merchandise_amount", "quantity", "refunded_merchandise_amount"}
            types = {
                c: "REAL"
                if c in numeric
                else "INTEGER"
                if c == "payment_success"
                else "TEXT"
                for c in columns
            }
            db.execute(
                "CREATE TABLE order_items ("
                + ", ".join(quote(c) + " " + types[c] for c in columns)
                + ")"
            )
            db.executemany(
                "INSERT INTO order_items VALUES ("
                + ",".join("?" for _ in columns)
                + ")",
                [tuple(row.get(c) for c in columns) for row in rows],
            )
        sidecar.write_text(json.dumps(mapping, indent=2), encoding="utf-8")
    except Exception:
        path.unlink(missing_ok=True)
        sidecar.unlink(missing_ok=True)
        raise
    return sidecar


def smoke_records():
    """Small backend smoke data; not an implementation of any Golden Set case."""
    records = []
    for label, day, count in [("b", "2026-08-25", 10), ("c", "2026-09-01", 7)]:
        for i in range(count):
            records.append(
                dict(
                    order_id=f"{label}{i}",
                    order_item_id=f"{label}{i}-1",
                    customer_id=f"{label}-customer{i // 2}",
                    paid_at=day,
                    payment_success=True,
                    merchandise_amount=100,
                    quantity=2,
                    first_valid_paid_at=day,
                    refunded_merchandise_amount=0,
                    refund_status="confirmed",
                    channel="paid_search" if i % 2 else "organic",
                    campaign="campaign_a",
                    category="home",
                    product="sku_1",
                    region="north",
                )
            )
    return records


SMOKE_PERIODS = [
    dict(start="2026-08-24", end="2026-08-30"),
    dict(start="2026-08-31", end="2026-09-06"),
]


def main():
    parser = argparse.ArgumentParser(
        description="Generate a synthetic SQLite backend smoke fixture; no Eval is run"
    )
    parser.add_argument("--database", required=True, type=Path)
    args = parser.parse_args()
    mapping = build_fixture(args.database, smoke_records(), SMOKE_PERIODS)
    print(f"Synthetic database: {args.database}\nMapping: {mapping}")


if __name__ == "__main__":
    main()
