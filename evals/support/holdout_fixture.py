"""Holdout construction grammar. Reads fixture_spec only, never Expected or ID.

Qualitative recipes use disclosed small concrete values; these choices are part
of fixture construction, not assertions passed to the Agent.
"""

import json
import re
import sqlite3
from contextlib import closing
from pathlib import Path

from .case_fixture import record, records_for_spec, periods_for, FixtureReviewRequired
from .fixture_builder import build_fixture


def construct(spec, periods):
    text = spec["description"]
    requirements = " ".join(spec.get("construction_requirements", []))
    days = [p["start"] for p in periods]
    options = {}

    def groups(dimension, values):
        return [
            record(label, i, day, amounts[p], **{dimension: name})
            for p, (label, day) in enumerate(zip(("b", "c"), days))
            for i, (name, *amounts) in enumerate(values)
        ]

    if re.search(r"Orders\s*=", text):
        return records_for_spec(spec, periods)[0], options
    units = re.findall(r"UPO=(\d+(?:\.\d+)?) price=(\d+(?:\.\d+)?)", requirements)
    if len(units) == 2:
        canonical = "；".join(
            f"Units per Order={u}、Average Realized Unit Price={p}" for u, p in units
        )
        return records_for_spec({"description": canonical}, periods)[0], options
    if "Channel GMV:" in text:
        before, after = text.split("；current ")
        values = re.findall(r"([A-Z][A-Za-z ]*)=(\d+)", before.split("baseline ")[1])
        currents = re.findall(r"\d+", after.split("。")[0])
        if len(values) != len(currents):
            raise FixtureReviewRequired("Unmatched channel totals")
        return groups(
            "channel",
            [
                (n.lower().replace(" ", "_"), int(b), int(c))
                for (n, b), c in zip(values, currents)
            ],
        ), options
    if text.startswith(("Category ", "Region ")):
        dimension = "category" if text.startswith("Category ") else "region"
        values = re.findall(r"([A-Za-z]+) (\d+)→(\d+)", text)
        return groups(
            dimension,
            [
                (
                    ("category_" if dimension == "category" else "") + n.lower(),
                    int(b),
                    int(c),
                )
                for n, b, c in values
            ],
        ), options
    if "Unknown/Unattributed" in text:
        options["construction_choice"] = (
            "GMV 10000→8000; unknown+unattributed=3600/8000=45%; known Paid Search declines most."
        )
        return groups(
            "channel",
            [
                ("unknown", 1000, 1800),
                ("unattributed", 1000, 1800),
                ("paid_search", 5000, 2000),
                ("organic", 3000, 2400),
            ],
        ), options
    if "New Partner" in text:
        options["construction_choice"] = (
            "Other channel 10000→6000; New Partner 0→1500; total 10000→7500."
        )
        return groups(
            "channel", [("organic", 10000, 6000), ("new_partner", 0, 1500)]
        ), options
    if "Category D" in text or "Channel X" in text:
        dimension = "category" if "Category D" in text else "channel"
        name = "category_d" if dimension == "category" else "channel_x"
        other = "category_a" if dimension == "category" else "organic"
        options["construction_choice"] = (
            "Requested largest negative segment 6000→3000; another segment 4000→4500."
        )
        return groups(dimension, [(name, 6000, 3000), (other, 4000, 4500)]), options
    if "跨品类订单" in text:
        options["construction_choice"] = (
            "Category related order counts 70/50→45/45; one overlapping order each period, AOV=100."
        )
        return records_for_spec(
            {"description": "Category A相关订单70→45、Category B相关订单50→45"}, periods
        )[0], options
    if "Paid Search" in text and "不提供" in text:
        options["construction_choice"] = (
            "Paid Search orders 8→4; organic 2→2; fixed order amount100; no advertising fields."
        )
        return records_for_spec(
            {"description": "Paid Search Orders 不提供外部原因字段"}, periods
        )[0], options
    if "缺失channel" in text:
        options.update(
            omit_dimension="channel",
            construction_choice="Orders100→75, AOV100; channel physically and semantically absent.",
        )
        return records_for_spec(
            {"description": "Orders=100 AOV=100；Orders=75 AOV=100"}, periods
        )[0], options
    values = re.findall(r"(?:基期|本期)GMV=(\d+)", text)
    if len(values) == 2:
        return groups("channel", [("organic", *map(int, values))]), options
    raise FixtureReviewRequired(
        "Unsupported Holdout fixture grammar; no data fabricated"
    )


def prepare(case, directory):
    rows, options = construct(case["fixture_spec"], periods_for(case))
    destination = Path(directory) / (case["case_id"] + ".db")
    mapping = build_fixture(destination, rows, periods_for(case))
    if dimension := options.get("omit_dimension"):
        data = json.loads(mapping.read_text(encoding="utf-8"))
        physical = data["semantic_mapping"].pop(dimension)
        # Identifier comes exclusively from the fixed canonical fixture mapping.
        if not re.fullmatch(r"[a-z_]+", physical):
            raise ValueError("Unsafe physical fixture column")
        with closing(sqlite3.connect(destination)) as db, db:
            db.execute(f'ALTER TABLE order_items DROP COLUMN "{physical}"')
        mapping.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return (
        destination,
        mapping,
        dict(
            row_count=len(rows), data_origin="synthetic", construction_options=options
        ),
    )
