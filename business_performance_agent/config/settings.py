from dataclasses import dataclass, field
from pathlib import Path
import os
import math
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    root: Path = ROOT
    logs: Path = ROOT / "logs"

    @property
    def business(self):
        return self.root / "specs"

    @property
    def workflow(self):
        return self.root / "specs" / "workflows" / "gmv_diagnosis"


@dataclass(frozen=True)
class ReadOnlyPolicy:
    query_timeout: float = 5.0
    max_rows: int = 10000
    table_allowlist: tuple[str, ...] = ("mock_order_items",)
    column_allowlist: tuple[str, ...] = ()


@dataclass(frozen=True)
class GeminiSettings:
    model: str = field(
        default_factory=lambda: os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
    )
    timeout_ms: int = 60000


@dataclass(frozen=True)
class DeepSeekSettings:
    api_key: str = field(
        default_factory=lambda: os.environ.get("DEEPSEEK_API_KEY", ""), repr=False
    )
    base_url: str = field(
        default_factory=lambda: os.environ.get(
            "DEEPSEEK_BASE_URL", "https://api.deepseek.com"
        )
    )
    model: str = field(
        default_factory=lambda: os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash")
    )
    timeout: float = field(
        default_factory=lambda: float(os.environ.get("DEEPSEEK_TIMEOUT", "60"))
    )

    def __post_init__(self):
        url = urlsplit(self.base_url)
        if (
            url.scheme != "https"
            or not url.hostname
            or url.username
            or url.password
            or url.query
            or url.fragment
        ):
            raise ValueError(
                "DEEPSEEK_BASE_URL must be an HTTPS base URL without credentials, query or fragment"
            )
        if not self.model or not math.isfinite(self.timeout) or self.timeout <= 0:
            raise ValueError("DeepSeek model and positive finite timeout are required")
