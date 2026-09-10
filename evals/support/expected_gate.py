"""Expected files cannot be opened by this loader before Actual checkpoints exist."""

import json
from pathlib import Path


class ExpectedGate:
    def __init__(self):
        self.execution_closed = False
        self.events = []

    def close_execution(self, checkpoints):
        for checkpoint in checkpoints:
            record = json.loads(Path(checkpoint).read_text(encoding="utf-8"))
            if record["execution_status"] not in (
                "completed",
                "review_required",
                "framework_error",
            ):
                raise RuntimeError("Expected gate: execution still pending")
        self.execution_closed = True

    def load(self, path, checkpoint):
        if not self.execution_closed:
            raise PermissionError("Expected gate is closed during Agent execution")
        actual = json.loads(Path(checkpoint).read_text(encoding="utf-8"))
        if actual.get(
            "execution_status"
        ) != "completed" or "actual_saved" not in actual.get("lifecycle", []):
            raise PermissionError("Expected requires a completed, persisted Actual")
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        self.events.append(
            {"event": "expected_loaded_after_actual", "checkpoint": str(checkpoint)}
        )
        return value
