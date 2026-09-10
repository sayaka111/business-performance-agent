"""Eval-only adapter: accepts data and mapping, never case IDs or Expected."""

import json
from pathlib import Path
from business_performance_agent.data_contract.sqlite_adapter import SQLiteDatasetAdapter


class CanonicalEvalSQLiteAdapter(SQLiteDatasetAdapter):
    def __init__(self, knowledge, database, policy=None):
        mapping = json.loads(
            Path(database).with_suffix(".mapping.json").read_text(encoding="utf-8")
        )
        if (
            mapping.get("data_origin") != "synthetic"
            or mapping.get("dataset_id") != "canonical_synthetic_v1"
        ):
            raise ValueError("Eval requires canonical synthetic data")
        canonical = json.loads(
            Path(__file__)
            .with_name("canonical_mapping.json")
            .read_text(encoding="utf-8")
        )
        if {k: v for k, v in mapping.items() if k != "complete_periods"} != {
            k: v for k, v in canonical.items() if k != "complete_periods"
        }:
            raise ValueError("Eval mapping must match the canonical data contract")
        super().__init__(knowledge, database, policy, mapping=mapping)
