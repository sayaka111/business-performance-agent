"""Import Olist processed CSVs as source data, not as canonical Agent metrics."""
import argparse
import csv
import hashlib
import json
import re
import sqlite3
from contextlib import closing
from pathlib import Path

TABLES = {"fact_sales": ("order_id", "order_item_id"),
          "dim_customer": ("customer_unique_id",), "dim_product": ("product_id",), "dim_date": ("date",)}

def quote(identifier):
    if not re.fullmatch(r"[a-z][a-z0-9_]*", identifier):
        raise ValueError("Unexpected CSV identifier")
    return '"' + identifier + '"'

def inspect_database(path):
    with closing(sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)) as db:
        db.execute("PRAGMA query_only=ON")
        counts = {name: db.execute("SELECT COUNT(*) FROM " + quote(name)).fetchone()[0]
                  for name in ("orders", "order_items", "customers", "products")}
        period = db.execute("SELECT MIN(purchase_date), MAX(purchase_date) FROM fact_sales").fetchone()
        return {"backend": "sqlite", "dataset": "olist_processed_delivered_only", "counts": counts,
                "purchase_date_range": list(period), "gmv_workflow_ready": False,
                "limitations": ["Source uses purchase time, not paid_at.",
                                "Only delivered orders are present; payment/refund coverage is unavailable.",
                                "First purchase is observed within this filtered historical dataset.",
                                "Channel data is unavailable."]}

def import_database(source, destination):
    source, destination = Path(source), Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Refuse to overwrite an existing database.
    with destination.open("xb"):
        pass
    try:
        with closing(sqlite3.connect(destination)) as db, db:
            db.execute("CREATE TABLE source_manifest (filename TEXT PRIMARY KEY, sha256 TEXT, row_count INTEGER)")
            for table, keys in TABLES.items():
                path = source / (table + ".csv")
                with path.open(encoding="utf-8-sig", newline="") as stream:
                    reader = csv.DictReader(stream)
                    fields = reader.fieldnames
                    if not fields or len(set(fields)) != len(fields) or not set(keys) <= set(fields):
                        raise ValueError("Missing/duplicate columns in " + path.name)
                    db.execute("CREATE TABLE " + quote(table) + " (" +
                               ",".join(quote(f) + " TEXT" for f in fields) + ")")
                    insert = "INSERT INTO " + quote(table) + " VALUES (" + ",".join("?" for _ in fields) + ")"
                    count = 0
                    for row in reader:
                        if None in row or any(row[f] is None for f in fields) or any(not row[k] for k in keys):
                            raise ValueError("Malformed row/key in " + path.name)
                        db.execute(insert, [row[f] if row[f] != "" else None for f in fields])
                        count += 1
                    if not count:
                        raise ValueError("Empty source: " + path.name)
                    db.execute("CREATE UNIQUE INDEX " + quote(table + "_key") + " ON " + quote(table) +
                               " (" + ",".join(quote(k) for k in keys) + ")")
                db.execute("INSERT INTO source_manifest VALUES (?,?,?)",
                           (path.name, hashlib.sha256(path.read_bytes()).hexdigest(), count))
            # Reconstruct order grain only after checking order attributes agree.
            conflicts = db.execute("""SELECT COUNT(*) FROM (
                SELECT order_id FROM fact_sales GROUP BY order_id HAVING
                COUNT(DISTINCT customer_unique_id) != 1 OR COUNT(DISTINCT order_purchase_timestamp) != 1
                OR COUNT(DISTINCT order_status) != 1
                OR COUNT(customer_unique_id) != COUNT(*)
                OR COUNT(order_purchase_timestamp) != COUNT(*)
                OR COUNT(order_status) != COUNT(*))""").fetchone()[0]
            missing = db.execute("""SELECT COUNT(*) FROM fact_sales f
                LEFT JOIN dim_customer c ON f.customer_unique_id=c.customer_unique_id
                LEFT JOIN dim_product p ON f.product_id=p.product_id
                WHERE c.customer_unique_id IS NULL OR p.product_id IS NULL""").fetchone()[0]
            if conflicts or missing:
                raise ValueError("Order-grain conflict or missing dimension references")
            db.execute("""CREATE VIEW orders AS SELECT DISTINCT order_id, customer_unique_id,
                order_purchase_timestamp, order_status FROM fact_sales""")
            db.execute("""CREATE VIEW order_items AS SELECT order_id, order_item_id, product_id,
                seller_id, price, freight_value FROM fact_sales""")
            db.execute("CREATE VIEW customers AS SELECT * FROM dim_customer")
            db.execute("CREATE VIEW products AS SELECT * FROM dim_product")
        return inspect_database(destination)
    except Exception:
        destination.unlink(missing_ok=True)
        raise

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    operation = parser.add_mutually_exclusive_group(required=True)
    operation.add_argument("--source", type=Path)
    operation.add_argument("--inspect", action="store_true", help="Inspect an existing database read-only")
    parser.add_argument("--database", type=Path, default=Path("data/olist.db"))
    args = parser.parse_args()
    try:
        result = inspect_database(args.database) if args.inspect else import_database(args.source, args.database)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, ValueError, sqlite3.Error) as exc:
        parser.exit(1, "Import failed: " + str(exc) + "\n")

if __name__ == "__main__":
    main()
