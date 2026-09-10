"""Compile the v1 fixture_spec text grammar, never Expected or evaluation_focus.

Unsupported or mathematically impossible specifications require review. There is
no case_id dispatch: IDs are used by the runner only for artifact filenames.
"""

import json
import re
import sqlite3
import tempfile
from contextlib import closing
from fractions import Fraction
from pathlib import Path

from .fixture_builder import build_fixture


class FixtureReviewRequired(ValueError):
    pass


def periods_for(case):
    return [
        dict(zip(("start", "end"), case["periods"][p].split("/")))
        for p in ("baseline", "current")
    ]


def workflow_input(case):
    """Literal task translation, not evaluation-guided intent/routing optimization."""
    question = case["user_query"]
    metric = (
        "aov"
        if "客单价" in question
        else "orders"
        if "订单量" in question
        else "gross_gmv"
    )
    dimension = (
        "category" if "品类" in question else "channel" if "渠道" in question else None
    )
    baseline, current = periods_for(case)
    return dict(
        metric_id=metric,
        current_period=current,
        baseline_period=baseline,
        filters={},
        context={"preferred_dimension": dimension} if dimension else {},
    )


def record(label, index, day, amount=100, quantity=1, customer=None, **dimensions):
    return (
        dict(
            order_id=f"{label}-o{index}",
            order_item_id=f"{label}-i{index}",
            customer_id=customer or f"{label}-u{index}",
            paid_at=day,
            payment_success=True,
            merchandise_amount=float(amount),
            quantity=float(quantity),
            first_valid_paid_at=day,
            refunded_merchandise_amount=0,
            refund_status="confirmed",
            channel="organic",
            campaign=None,
            category="general",
            product="sku_1",
            region="north",
            **{},
        )
        | dimensions
    )


def measurements(text, label):
    return [
        Fraction(value)
        for value in re.findall(re.escape(label) + r"\s*=\s*(\d+(?:\.\d+)?)", text)
    ]


def records_for_spec(spec, periods):
    text = spec["description"]
    days = [p["start"] for p in periods]
    rows = []
    if "created_at" in text and "delivered_at" in text:
        for i, day in enumerate(days):
            row = record(str(i), 0, day)
            row["paid_at"] = None
            row["first_valid_paid_at"] = None
            rows.append(row)
        return rows, {"unmapped_timestamp_decoys": True}
    orders = measurements(text, "Orders")
    buyers = measurements(text, "Buyers")
    if orders and buyers:
        if len(orders) != 2 or len(buyers) != 2:
            raise FixtureReviewRequired(
                "Expected two periods of Orders and Buyers constraints"
            )
        for n, b in zip(orders, buyers):
            if n.denominator != 1 or b.denominator != 1 or b > n or (n and b <= 0):
                raise FixtureReviewRequired(
                    f"Impossible active-buyer constraint: Orders={n}, distinct Buyers={b}; every buyer needs at least one valid order with one customer identity."
                )
        for label, day, n, b in zip(("b", "c"), days, orders, buyers):
            rows.extend(
                record(label, i, day, customer=f"{label}-u{i % int(b)}")
                for i in range(int(n))
            )
    elif orders:
        aov = measurements(text, "AOV")
        if len(orders) != 2 or len(aov) != 2 or any(n.denominator != 1 for n in orders):
            raise FixtureReviewRequired("Unsupported Orders/AOV construction")
        for label, day, n, amount in zip(("b", "c"), days, orders, aov):
            rows.extend(record(label, i, day, amount, 2) for i in range(int(n)))
    elif "Units per Order=" in text:
        units = measurements(text, "Units per Order")
        prices = measurements(text, "Average Realized Unit Price")
        if len(units) != 2 or len(prices) != 2:
            raise FixtureReviewRequired("Unsupported unit/price construction")
        count = max(u.denominator for u in units)
        for label, day, units_per_order, price in zip(("b", "c"), days, units, prices):
            total = units_per_order * count
            if total.denominator != 1:
                raise FixtureReviewRequired("Nonintegral item quantity")
            base, extra = divmod(int(total), count)
            for i in range(count):
                qty = base + (i < extra)
                rows.append(record(label, i, day, qty * price, qty))
    elif "相关订单" in text:
        groups = re.findall(r"Category ([A-Z])相关订单(\d+)→(\d+)", text)
        if len(groups) != 2:
            raise FixtureReviewRequired("Unsupported overlapping category counts")
        for p, (label, day) in enumerate(zip(("b", "c"), days)):
            # One shared order has two items; each category count includes it.
            for g, group in enumerate(groups):
                name = "category_" + group[0].lower()
                shared = record(label, "shared", day, 50, category=name)
                shared["order_item_id"] = f"{label}-shared-{g}"
                rows.append(shared)
                for i in range(int(group[p + 1]) - 1):
                    rows.append(record(label, f"{g}-{i}", day, category=name))
    elif "Category" in text:
        groups = re.findall(r"Category ([A-Z])(?: GMV)?\s*(\d+)→(\d+)", text)
        if len(groups) != 2:
            raise FixtureReviewRequired("Unsupported category totals")
        for label, day, p in zip(("b", "c"), days, (1, 2)):
            for name, *totals in groups:
                rows.append(
                    record(
                        label,
                        name,
                        day,
                        int(totals[p - 1]),
                        category="category_" + name.lower(),
                    )
                )
    elif "Paid Search" in text and "Organic" in text and "Direct" in text:
        groups = re.findall(r"(Paid Search|Organic|Direct)\s*(\d+)→(\d+)", text)
        if len(groups) != 3:
            raise FixtureReviewRequired("Unsupported channel totals")
        for label, day, p in zip(("b", "c"), days, (1, 2)):
            for name, *totals in groups:
                rows.append(
                    record(
                        label,
                        name.lower().replace(" ", "_"),
                        day,
                        int(totals[p - 1]),
                        channel=name.lower().replace(" ", "_"),
                    )
                )
    elif "基期GMV=0" in text:
        value = re.search(r"本期GMV=(\d+)", text)
        if not value:
            raise FixtureReviewRequired("Missing current GMV constraint")
        rows = [record("c", 0, days[1], int(value[1]), channel="paid_search")]
    elif "Paid Search Orders" in text and "不提供" in text:
        # Qualitative specification: constant price, falling paid-search orders.
        for label, day, counts in [("b", days[0], (8, 2)), ("c", days[1], (4, 2))]:
            for channel, count in zip(("paid_search", "organic"), counts):
                rows.extend(
                    record(label, f"{channel}-{i}", day, channel=channel)
                    for i in range(count)
                )
    else:
        raise FixtureReviewRequired(
            "fixture_spec is outside the documented v1 construction grammar"
        )
    return rows, {}


def prepare_fixture(case, directory):
    """Artifact ID stays outside records, mapping and Agent execution directory."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    identifier = case["case_id"]
    if not re.fullmatch(r"[a-z0-9_]+", identifier):
        raise ValueError("Unsafe case identifier")
    periods = periods_for(case)
    rows, options = records_for_spec(case["fixture_spec"], periods)
    with tempfile.TemporaryDirectory(prefix="build-", dir=directory) as temporary:
        source = Path(temporary) / "data.db"
        mapping = build_fixture(source, rows, periods)
        if options.get("unmapped_timestamp_decoys"):
            with closing(sqlite3.connect(source)) as db, db:
                db.execute("ALTER TABLE order_items ADD COLUMN created_at TEXT")
                db.execute("ALTER TABLE order_items ADD COLUMN delivered_at TEXT")
                db.execute(
                    "UPDATE order_items SET created_at='2026-06-01', delivered_at='2026-09-01'"
                )
        target = directory / (identifier + ".db")
        sidecar = target.with_suffix(".mapping.json")
        for src, dest in ((source, target), (mapping, sidecar)):
            if dest.exists():
                if dest.read_bytes() != src.read_bytes():
                    raise ValueError(
                        "Existing generated fixture differs; use a fresh fixture directory for revised Cases"
                    )
            else:
                dest.write_bytes(src.read_bytes())
    return (
        target,
        sidecar,
        {
            "row_count": len(rows),
            "data_origin": "synthetic",
            "construction_options": options,
        },
    )
