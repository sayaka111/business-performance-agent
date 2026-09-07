from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

@dataclass(frozen=True)
class Settings:
    root: Path = ROOT
    logs: Path = ROOT / 'logs'

    @property
    def business(self):
        return self.root / 'specs'

    @property
    def workflow(self):
        return self.root / 'specs' / 'workflows' / 'gmv_diagnosis'

@dataclass(frozen=True)
class ReadOnlyPolicy:
    query_timeout: float = 5.0
    max_rows: int = 10000
    table_allowlist: tuple[str, ...] = ('mock_order_items',)
    column_allowlist: tuple[str, ...] = ()
