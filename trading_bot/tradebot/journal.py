"""Append-only JSONL audit log of every session, tool call and order."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


class Journal:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, event: str, **data) -> None:
        rec = {"ts": datetime.now(timezone.utc).isoformat(), "event": event, **data}
        with self.path.open("a") as f:
            f.write(json.dumps(rec, default=str) + "\n")

    def recent(self, event: str, n: int) -> list[dict]:
        if not self.path.exists():
            return []
        out = []
        for line in reversed(self.path.read_text().splitlines()):
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("event") == event:
                out.append(rec)
                if len(out) >= n:
                    break
        return list(reversed(out))
