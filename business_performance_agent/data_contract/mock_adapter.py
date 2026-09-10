import json
import re
from pathlib import Path
from ..models.schemas import BoundaryError, Period
from ..tools.calculations import evaluate_formula
from .record_adapter import SemanticRecordAdapter


class MockDatasetAdapter(SemanticRecordAdapter):
    def __init__(self, knowledge, rows=None, mapping=None):
        self.knowledge = knowledge
        self.mapping = mapping or json.loads(
            Path(__file__)
            .with_name("mock_schema_mapping.json")
            .read_text(encoding="utf-8")
        )
        self.capabilities = self.mapping["capabilities"]
        self.complete_periods = {
            ("2026-08-24", "2026-08-30"),
            ("2026-08-31", "2026-09-06"),
        }
        self.semantic_consistent = True
        self.rows = rows if rows is not None else self._fixture()

    def _fixture(self):
        rows = []
        # Synthetic records, not metric values or replacement formulas.
        for label, day, count, amount in [
            ("b", "2026-08-25", 100, 100.0),
            ("c", "2026-09-01", 75, 98.0),
        ]:
            for i in range(count):
                values = dict(
                    order_id=f"{label}-o{i}",
                    order_item_id=f"{label}-i{i}",
                    customer_id=f"{label}-u{i // 2}",
                    paid_at=day,
                    payment_success=True,
                    merchandise_amount=amount,
                    quantity=2,
                    first_valid_paid_at=day if i < count // 2 else "2025-01-01",
                    refund_status="confirmed",
                    refunded_merchandise_amount=0,
                    channel="paid_search"
                    if i % 3 == 0
                    else "organic"
                    if i % 3 == 1
                    else None,
                    campaign=None,
                    region="north" if i % 2 == 0 else "south",
                    category="home",
                    product="sku_1",
                )
                rows.append(
                    {
                        self.mapping["semantic_mapping"][key]: value
                        for key, value in values.items()
                    }
                )
        # Stable first purchase per customer, including multiple orders in one period.
        first = {}
        for row in rows:
            customer = row[self.mapping["semantic_mapping"]["customer_id"]]
            date = row[self.mapping["semantic_mapping"]["first_valid_paid_at"]]
            first[customer] = min(first.get(customer, date), date)
        for row in rows:
            row[self.mapping["semantic_mapping"]["first_valid_paid_at"]] = first[
                row[self.mapping["semantic_mapping"]["customer_id"]]
            ]
        return rows
