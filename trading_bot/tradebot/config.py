from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


def _csv(value: str | None) -> frozenset[str]:
    return frozenset(s.strip().upper() for s in (value or "").split(",") if s.strip())


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    model: str = "claude-opus-5-5"
    effort: str = "high"
    enable_web_search: bool = False

    rh_username: str = ""
    rh_password: str = ""
    rh_totp_secret: str = ""

    mode: str = "paper"  # "paper" | "live"
    paper_starting_cash: float = 10_000.0

    max_order_usd: float = 500.0
    max_position_pct: float = 0.20
    max_positions: int = 8
    min_cash_reserve_pct: float = 0.10
    daily_loss_limit_pct: float = 0.03
    max_trades_per_day: int = 10
    limit_price_band_pct: float = 0.05
    symbol_allowlist: frozenset[str] = field(default_factory=frozenset)
    symbol_blocklist: frozenset[str] = field(default_factory=frozenset)

    max_agent_steps: int = 30
    state_dir: Path = Path("state")

    @classmethod
    def from_env(cls, env_file: str | None = ".env") -> "Settings":
        if env_file:
            load_dotenv(env_file)
        e = os.environ.get
        mode = (e("TRADING_MODE") or "paper").strip().lower()
        if mode not in {"paper", "live"}:
            raise ValueError(f"TRADING_MODE must be 'paper' or 'live', got {mode!r}")
        return cls(
            model=e("CLAUDE_MODEL") or cls.model,
            effort=(e("CLAUDE_EFFORT") or cls.effort).split("#")[0].strip(),
            enable_web_search=_bool(e("ENABLE_WEB_SEARCH")),
            rh_username=e("RH_USERNAME", ""),
            rh_password=e("RH_PASSWORD", ""),
            rh_totp_secret=e("RH_TOTP_SECRET", ""),
            mode=mode,
            paper_starting_cash=float(e("PAPER_STARTING_CASH") or cls.paper_starting_cash),
            max_order_usd=float(e("MAX_ORDER_USD") or cls.max_order_usd),
            max_position_pct=float(e("MAX_POSITION_PCT") or cls.max_position_pct),
            max_positions=int(e("MAX_POSITIONS") or cls.max_positions),
            min_cash_reserve_pct=float(e("MIN_CASH_RESERVE_PCT") or cls.min_cash_reserve_pct),
            daily_loss_limit_pct=float(e("DAILY_LOSS_LIMIT_PCT") or cls.daily_loss_limit_pct),
            max_trades_per_day=int(e("MAX_TRADES_PER_DAY") or cls.max_trades_per_day),
            limit_price_band_pct=float(e("LIMIT_PRICE_BAND_PCT") or cls.limit_price_band_pct),
            symbol_allowlist=_csv(e("SYMBOL_ALLOWLIST")),
            symbol_blocklist=_csv(e("SYMBOL_BLOCKLIST")),
            max_agent_steps=int(e("MAX_AGENT_STEPS") or cls.max_agent_steps),
            state_dir=Path(e("STATE_DIR") or "state"),
        )

    def risk_summary(self) -> dict:
        return {
            "max_order_usd": self.max_order_usd,
            "max_position_pct_of_equity": self.max_position_pct,
            "max_positions": self.max_positions,
            "min_cash_reserve_pct_of_equity": self.min_cash_reserve_pct,
            "daily_loss_limit_pct": self.daily_loss_limit_pct,
            "max_trades_per_day": self.max_trades_per_day,
            "limit_price_band_pct": self.limit_price_band_pct,
            "symbol_allowlist": sorted(self.symbol_allowlist) or "any",
            "symbol_blocklist": sorted(self.symbol_blocklist),
            "shorting": False,
            "options_or_margin": False,
            "trading_hours": "regular session only",
        }
