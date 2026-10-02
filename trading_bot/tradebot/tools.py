"""Tool definitions exposed to Claude and the executor that runs them."""
from __future__ import annotations

import json
from typing import Callable

from .broker import Broker, MarketData
from .config import Settings
from .indicators import summarize
from .journal import Journal
from .models import OrderRequest
from .risk import RiskManager, SYMBOL_RE
from .state import DailyState, Notes

INTERVALS = ["5minute", "10minute", "hour", "day", "week"]
SPANS = ["day", "week", "month", "3month", "year", "5year"]

_symbol = {"type": "string", "description": "US stock/ETF ticker, e.g. AAPL"}

TOOLS: list[dict] = [
    {
        "name": "get_account",
        "description": "Current cash, buying power, equity, every position with unrealized P&L, "
                       "today's P&L versus start-of-day equity, trades remaining today, and the hard risk limits.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "get_quotes",
        "description": "Latest regular-session prices for up to 20 tickers.",
        "input_schema": {
            "type": "object",
            "properties": {"symbols": {"type": "array", "items": _symbol, "minItems": 1, "maxItems": 20}},
            "required": ["symbols"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_price_history",
        "description": "OHLCV history plus computed indicators (SMA 10/20/50, RSI 14, % changes, range). "
                       "Valid pairs: 5minute/10minute with day or week; hour with week or month; "
                       "day with month, 3month, year or 5year; week with year or 5year.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": _symbol,
                "interval": {"type": "string", "enum": INTERVALS},
                "span": {"type": "string", "enum": SPANS},
                "bars": {"type": "integer", "minimum": 0, "maximum": 60,
                         "description": "How many of the most recent raw bars to include (default 10)."},
            },
            "required": ["symbol", "interval", "span"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_fundamentals",
        "description": "Market cap, P/E, P/B, dividend yield, 52-week range, volume, sector, industry, description.",
        "input_schema": {"type": "object", "properties": {"symbol": _symbol},
                         "required": ["symbol"], "additionalProperties": False},
    },
    {
        "name": "get_news",
        "description": "Recent news headlines and summaries for a ticker.",
        "input_schema": {"type": "object", "properties": {"symbol": _symbol},
                         "required": ["symbol"], "additionalProperties": False},
    },
    {
        "name": "get_open_orders",
        "description": "Orders that are placed but not yet filled or cancelled.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "place_order",
        "description": (
            "Submit a buy or sell order. Long-only: you can sell only shares you hold. "
            "Market orders take either quantity (shares, fractional OK) or notional_usd (dollars). "
            "Limit orders take whole-share quantity and limit_price, and are good for the day. "
            "Every order is checked against the hard risk limits first; a violation returns an error "
            "listing what to change. Always give a concrete rationale."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": _symbol,
                "side": {"type": "string", "enum": ["buy", "sell"]},
                "order_type": {"type": "string", "enum": ["market", "limit"]},
                "quantity": {"type": "number", "exclusiveMinimum": 0},
                "notional_usd": {"type": "number", "exclusiveMinimum": 0},
                "limit_price": {"type": "number", "exclusiveMinimum": 0},
                "rationale": {"type": "string", "description": "Thesis, signal, and exit plan for this trade."},
            },
            "required": ["symbol", "side", "order_type", "rationale"],
            "additionalProperties": False,
        },
    },
    {
        "name": "cancel_order",
        "description": "Cancel an open order by id.",
        "input_schema": {
            "type": "object",
            "properties": {"order_id": {"type": "string"}, "reason": {"type": "string"}},
            "required": ["order_id", "reason"],
            "additionalProperties": False,
        },
    },
    {
        "name": "update_notes",
        "description": "Replace your persistent notes (watchlist, open theses with exit levels, lessons learned). "
                       "They are shown to you at the start of every future session. Max ~6000 characters.",
        "input_schema": {"type": "object", "properties": {"text": {"type": "string"}},
                         "required": ["text"], "additionalProperties": False},
    },
]

WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search", "max_uses": 5}


class ToolError(Exception):
    pass


def _sym(value) -> str:
    sym = str(value or "").strip().upper()
    if not SYMBOL_RE.match(sym):
        raise ToolError(f"invalid symbol {value!r}")
    return sym


def _num(value, name: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ToolError(f"{name} must be a number")
    return float(value)


ConfirmFn = Callable[[OrderRequest, float], bool]


class ToolExecutor:
    def __init__(self, settings: Settings, broker: Broker, market: MarketData, risk: RiskManager,
                 daily: DailyState, notes: Notes, journal: Journal, confirm: ConfirmFn | None = None):
        self.s, self.broker, self.market, self.risk = settings, broker, market, risk
        self.daily, self.notes, self.journal, self.confirm = daily, notes, journal, confirm
        self.orders_this_session: list[dict] = []

    def run(self, name: str, args: dict) -> tuple[str, bool]:
        """Returns (json_text, is_error)."""
        handler = getattr(self, f"_t_{name}", None)
        if handler is None:
            return json.dumps({"error": f"unknown tool {name}"}), True
        if not isinstance(args, dict):
            return json.dumps({"error": "tool input must be an object"}), True
        try:
            return json.dumps(handler(**args), default=str), False
        except ToolError as e:
            return json.dumps({"error": str(e)}), True
        except TypeError as e:  # unexpected/missing arguments
            return json.dumps({"error": f"bad arguments: {e}"}), True
        except Exception as e:  # broker/network failure: let the agent see it and adapt
            self.journal.log("tool_exception", tool=name, args=args, error=repr(e))
            return json.dumps({"error": f"{type(e).__name__}: {e}"}), True

    # ---- tools

    def _t_get_account(self) -> dict:
        acct = self.broker.account()
        return {
            "mode": self.broker.mode,
            "market_open": self.market.market_open(),
            "cash": round(acct.cash, 2),
            "buying_power": round(acct.buying_power, 2),
            "equity": round(acct.equity, 2),
            "positions": [p.to_dict() for p in sorted(acct.positions.values(), key=lambda p: -p.market_value)],
            "today": self.risk.status(acct),
            "risk_limits": self.s.risk_summary(),
        }

    def _t_get_quotes(self, symbols: list) -> dict:
        if not isinstance(symbols, list) or not 1 <= len(symbols) <= 20:
            raise ToolError("symbols must be a list of 1-20 tickers")
        syms = [_sym(s) for s in symbols]
        prices = self.market.prices(syms)
        return {"prices": prices, "missing": [s for s in syms if s not in prices]}

    def _t_get_price_history(self, symbol: str, interval: str, span: str, bars: int = 10) -> dict:
        sym = _sym(symbol)
        if interval not in INTERVALS or span not in SPANS:
            raise ToolError(f"interval must be one of {INTERVALS}, span one of {SPANS}")
        rows = self.market.history(sym, interval, span)
        if not rows:
            raise ToolError(f"no history for {sym} at {interval}/{span}; try another valid pair")
        bars = max(0, min(int(bars), 60))
        return {"symbol": sym, "interval": interval, "span": span, "count": len(rows),
                "indicators": summarize([r["c"] for r in rows]),
                "recent_bars": rows[-bars:] if bars else []}

    def _t_get_fundamentals(self, symbol: str) -> dict:
        return {"symbol": _sym(symbol), **self.market.fundamentals(_sym(symbol))}

    def _t_get_news(self, symbol: str) -> dict:
        return {"symbol": _sym(symbol), "items": self.market.news(_sym(symbol))}

    def _t_get_open_orders(self) -> dict:
        return {"orders": self.broker.open_orders()}

    def _t_place_order(self, symbol: str, side: str, order_type: str, rationale: str,
                       quantity=None, notional_usd=None, limit_price=None) -> dict:
        req = OrderRequest(
            symbol=_sym(symbol), side=side, order_type=order_type,
            quantity=_num(quantity, "quantity"), notional_usd=_num(notional_usd, "notional_usd"),
            limit_price=_num(limit_price, "limit_price"), rationale=str(rationale or "").strip(),
        )
        if not req.rationale:
            raise ToolError("rationale is required")
        price = self.market.prices([req.symbol]).get(req.symbol)
        acct = self.broker.account()
        violations = self.risk.check(req, acct, price, self.market.market_open())
        if violations:
            self.journal.log("order_blocked", order=req.__dict__, price=price, violations=violations)
            raise ToolError("order blocked by risk limits: " + "; ".join(violations))

        if self.confirm and not self.confirm(req, price):
            self.journal.log("order_declined_by_human", order=req.__dict__, price=price)
            raise ToolError("the human operator declined this order; do not resubmit it this session")

        result = self.broker.place_order(req, price)
        if result.status != "rejected":
            self.daily.record_trade()
        rec = {"order": req.__dict__, "price_at_submit": price, "result": result.to_dict()}
        self.journal.log("order", mode=self.broker.mode, **rec)
        self.orders_this_session.append(rec)
        if result.status == "rejected":
            raise ToolError(result.message)
        return result.to_dict()

    def _t_cancel_order(self, order_id: str, reason: str) -> dict:
        msg = self.broker.cancel_order(str(order_id))
        self.journal.log("cancel", order_id=order_id, reason=reason, result=msg)
        return {"order_id": order_id, "result": msg}

    def _t_update_notes(self, text: str) -> dict:
        self.notes.replace(str(text))
        return {"saved_chars": len(self.notes.text)}
