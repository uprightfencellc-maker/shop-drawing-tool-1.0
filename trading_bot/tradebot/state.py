"""Small JSON-backed state: per-day risk counters and the agent's persistent notes."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path


class JsonFile:
    def __init__(self, path: Path, default: dict):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data = json.loads(path.read_text()) if path.exists() else default

    def save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=2, default=str))
        tmp.replace(self.path)


class DailyState(JsonFile):
    """Tracks start-of-day equity and trade count so daily limits survive restarts."""

    def __init__(self, path: Path, today: date | None = None):
        super().__init__(path, {})
        self.today = (today or date.today()).isoformat()
        self.new_day = self.data.get("date") != self.today
        if self.new_day:
            self.data = {"date": self.today, "start_equity": None, "trades": 0}
            self.save()

    def ensure_start_equity(self, equity: float) -> float:
        if self.data["start_equity"] is None:
            self.data["start_equity"] = equity
            self.save()
        return self.data["start_equity"]

    @property
    def start_equity(self) -> float | None:
        return self.data["start_equity"]

    @property
    def trades(self) -> int:
        return self.data["trades"]

    def record_trade(self) -> None:
        self.data["trades"] += 1
        self.save()


class Notes(JsonFile):
    """Free-form memory the agent maintains between sessions (theses, watchlist, lessons)."""

    MAX_CHARS = 6000

    def __init__(self, path: Path):
        super().__init__(path, {"text": ""})

    @property
    def text(self) -> str:
        return self.data["text"]

    def replace(self, text: str) -> None:
        self.data["text"] = text[: self.MAX_CHARS]
        self.save()
