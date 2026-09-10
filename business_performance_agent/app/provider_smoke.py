"""Explicit, single-attempt provider connectivity and structured-intent check."""

import argparse
import json

from ..config.settings import Settings
from ..tools.knowledge_loader import KnowledgeLoader
from ..workflows.definition import load_workflow
from ..llm.providers import PROVIDER_KEYS, create_client
from ..llm.intent_parser import IntentParser


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", required=True, choices=list(PROVIDER_KEYS))
    parser.add_argument("--model")
    args = parser.parse_args()
    client = None
    try:
        client = create_client(args.provider, args.model, max_attempts=1)
        settings = Settings()
        raw = IntentParser(
            KnowledgeLoader(settings.business / "knowledge"),
            load_workflow(settings.workflow),
            client,
        ).parse(
            "Diagnose gross_gmv. Current period 2026-08-01 to 2026-08-31. Baseline period 2026-07-01 to 2026-07-31. No filters."
        )
        if (
            raw["metric_id"] != "gross_gmv"
            or raw["filters"]
            or raw["current_period"] != {"start": "2026-08-01", "end": "2026-08-31"}
            or raw["baseline_period"] != {"start": "2026-07-01", "end": "2026-07-31"}
        ):
            raise ValueError("Intent mismatch")
        print(
            json.dumps(
                dict(
                    status="API_OK",
                    provider=args.provider,
                    model=client.model,
                    attempts=len(client.events),
                )
            )
        )
        return 0
    except Exception as exc:
        print(
            json.dumps(
                dict(
                    status="FAILED",
                    provider=args.provider,
                    error_type=type(exc).__name__,
                    events=client.events if client else [],
                )
            )
        )
        return 1
    finally:
        if client:
            client.close()


if __name__ == "__main__":
    raise SystemExit(main())
