"""Market data and order execution.

Robinhood has no official stock-trading API; this uses the community `robin_stocks`
library, which talks to Robinhood's private app API. It can break when Robinhood
changes that API, and automated use may conflict with Robinhood's terms of service.
"""
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .models import Account, OrderRequest, OrderResult, Position
from .state import JsonFile

NY = ZoneInfo("America/New_York")


def clock_market_open(now: datetime | None = None) -> bool:
    """Fallback check: weekday regular session. Does not know about holidays."""
    now = (now or datetime.now(NY)).astimezone(NY)
    if now.weekday() >= 5:
        return False
    minutes = now.hour * 60 + now.minute
    return 9 * 60 + 30 <= minutes < 16 * 60


# --------------------------------------------------------------------------- market data


class MarketData(ABC):
    @abstractmethod
    def prices(self, symbols: list[str]) -> dict[str, float]: ...

    @abstractmethod
    def history(self, symbol: str, interval: str, span: str) -> list[dict]: ...

    @abstractmethod
    def fundamentals(self, symbol: str) -> dict: ...

    @abstractmethod
    def news(self, symbol: str, limit: int = 8) -> list[dict]: ...

    @abstractmethod
    def market_open(self) -> bool: ...


class RobinhoodSession:
    """Logs in once; shared by market data and the live broker."""

    def __init__(self, username: str, password: str, totp_secret: str = ""):
        import robin_stocks.robinhood as rh

        self.rh = rh
        mfa = None
        if totp_secret:
            import pyotp

            mfa = pyotp.TOTP(totp_secret).now()
        # store_session caches the token (~/.tokens) so later runs skip MFA/device prompts.
        rh.login(username or None, password or None, mfa_code=mfa, store_session=True)


class RobinhoodMarketData(MarketData):
    FUNDAMENTAL_KEYS = (
        "market_cap", "pe_ratio", "pb_ratio", "dividend_yield", "high_52_weeks",
        "low_52_weeks", "average_volume", "volume", "sector", "industry", "description",
    )

    def __init__(self, session: RobinhoodSession):
        self.rh = session.rh

    def prices(self, symbols: list[str]) -> dict[str, float]:
        if not symbols:
            return {}
        raw = self.rh.stocks.get_latest_price(symbols, includeExtendedHours=False)
        return {s: float(p) for s, p in zip(symbols, raw) if p not in (None, "")}

    def history(self, symbol: str, interval: str, span: str) -> list[dict]:
        rows = self.rh.stocks.get_stock_historicals(symbol, interval=interval, span=span) or []
        return [
            {
                "t": r["begins_at"],
                "o": float(r["open_price"]),
                "h": float(r["high_price"]),
                "l": float(r["low_price"]),
                "c": float(r["close_price"]),
                "v": int(r["volume"]),
            }
            for r in rows
            if r and r.get("close_price")
        ]

    def fundamentals(self, symbol: str) -> dict:
        data = (self.rh.stocks.get_fundamentals(symbol) or [None])[0] or {}
        out = {k: data.get(k) for k in self.FUNDAMENTAL_KEYS}
        if out.get("description"):
            out["description"] = out["description"][:500]
        return out

    def news(self, symbol: str, limit: int = 8) -> list[dict]:
        items = self.rh.stocks.get_news(symbol) or []
        return [
            {
                "title": i.get("title"),
                "source": i.get("source"),
                "published_at": i.get("published_at"),
                "summary": (i.get("summary") or "")[:300],
                "url": i.get("url"),
            }
            for i in items[:limit]
        ]

    def market_open(self) -> bool:
        try:
            hours = self.rh.markets.get_market_today_hours("XNYS")
            if not hours or not hours.get("is_open"):
                return False
            opens = datetime.fromisoformat(hours["opens_at"].replace("Z", "+00:00"))
            closes = datetime.fromisoformat(hours["closes_at"].replace("Z", "+00:00"))
            return opens <= datetime.now(opens.tzinfo) < closes
        except Exception:
            return clock_market_open()


# --------------------------------------------------------------------------- brokers


class Broker(ABC):
    mode: str

    @abstractmethod
    def account(self) -> Account: ...

    @abstractmethod
    def open_orders(self) -> list[dict]: ...

    @abstractmethod
    def place_order(self, req: OrderRequest, price: float) -> OrderResult: ...

    @abstractmethod
    def cancel_order(self, order_id: str) -> str: ...


class LiveRobinhoodBroker(Broker):
    mode = "live"

    def __init__(self, session: RobinhoodSession):
        self.rh = session.rh

    def account(self) -> Account:
        profile = self.rh.profiles.load_account_profile() or {}
        holdings = self.rh.account.build_holdings() or {}
        positions = {
            sym: Position(
                symbol=sym,
                quantity=float(h["quantity"]),
                avg_cost=float(h["average_buy_price"]),
                price=float(h["price"]),
            )
            for sym, h in holdings.items()
            if float(h.get("quantity") or 0) > 0
        }
        cash = float(profile.get("cash") or profile.get("portfolio_cash") or 0)
        bp = float(profile.get("buying_power") or cash)
        return Account(cash=cash, buying_power=bp, positions=positions)

    def open_orders(self) -> list[dict]:
        orders = self.rh.orders.get_all_open_stock_orders() or []
        out = []
        for o in orders:
            sym = None
            try:
                sym = self.rh.stocks.get_symbol_by_url(o["instrument"])
            except Exception:
                pass
            out.append({
                "id": o.get("id"), "symbol": sym, "side": o.get("side"), "type": o.get("type"),
                "quantity": o.get("quantity"), "price": o.get("price"), "state": o.get("state"),
                "created_at": o.get("created_at"),
            })
        return out

    def place_order(self, req: OrderRequest, price: float) -> OrderResult:
        o = self.rh.orders
        if req.order_type == "limit":
            fn = o.order_buy_limit if req.side == "buy" else o.order_sell_limit
            resp = fn(req.symbol, req.quantity, round(req.limit_price, 2), timeInForce="gfd")
        elif req.notional_usd is not None:
            fn = o.order_buy_fractional_by_price if req.side == "buy" else o.order_sell_fractional_by_price
            resp = fn(req.symbol, round(req.notional_usd, 2), timeInForce="gfd")
        elif req.quantity != int(req.quantity):
            # order_buy/sell_market only take whole shares; fractional quantities need these.
            fn = o.order_buy_fractional_by_quantity if req.side == "buy" else o.order_sell_fractional_by_quantity
            resp = fn(req.symbol, round(req.quantity, 6), timeInForce="gfd")
        else:
            fn = o.order_buy_market if req.side == "buy" else o.order_sell_market
            resp = fn(req.symbol, int(req.quantity), timeInForce="gfd")

        if not isinstance(resp, dict) or "id" not in resp:
            msg = resp.get("detail") or resp.get("non_field_errors") or resp if isinstance(resp, dict) else resp
            return OrderResult(id="", symbol=req.symbol, side=req.side, status="rejected",
                               quantity=req.quantity, notional_usd=req.notional_usd,
                               order_type=req.order_type, limit_price=req.limit_price,
                               message=f"Robinhood rejected order: {msg}")
        return OrderResult(
            id=resp["id"], symbol=req.symbol, side=req.side,
            status="submitted", quantity=req.quantity, notional_usd=req.notional_usd,
            order_type=req.order_type, limit_price=req.limit_price,
            message=f"Robinhood state: {resp.get('state')}",
        )

    def cancel_order(self, order_id: str) -> str:
        resp = self.rh.orders.cancel_stock_order(order_id)
        return f"cancel requested: {resp}"


class PaperBroker(Broker):
    """Simulated portfolio stored locally. Market orders fill at the last price;
    limit orders fill when the last price crosses the limit on a later refresh."""

    mode = "paper"

    def __init__(self, market: MarketData, path: Path, starting_cash: float):
        self.market = market
        self.store = JsonFile(path, {"cash": starting_cash, "positions": {}, "open_orders": []})

    # positions are stored as {symbol: {"quantity": q, "avg_cost": c}}
    def _fill(self, symbol: str, side: str, qty: float, px: float) -> None:
        d = self.store.data
        pos = d["positions"].get(symbol, {"quantity": 0.0, "avg_cost": 0.0})
        if side == "buy":
            new_qty = pos["quantity"] + qty
            pos["avg_cost"] = (pos["quantity"] * pos["avg_cost"] + qty * px) / new_qty
            pos["quantity"] = new_qty
            d["cash"] -= qty * px
        else:
            pos["quantity"] -= qty
            d["cash"] += qty * px
        if pos["quantity"] <= 1e-9:
            d["positions"].pop(symbol, None)
        else:
            d["positions"][symbol] = pos

    def _process_open_orders(self) -> None:
        d = self.store.data
        if not d["open_orders"]:
            return
        px = self.market.prices(sorted({o["symbol"] for o in d["open_orders"]}))
        remaining = []
        for o in d["open_orders"]:
            last = px.get(o["symbol"])
            crosses = last is not None and (
                (o["side"] == "buy" and last <= o["limit_price"])
                or (o["side"] == "sell" and last >= o["limit_price"])
            )
            held = d["positions"].get(o["symbol"], {}).get("quantity", 0)
            affordable = o["side"] == "sell" or d["cash"] >= o["quantity"] * o["limit_price"]
            if crosses and affordable and (o["side"] == "buy" or held >= o["quantity"]):
                self._fill(o["symbol"], o["side"], o["quantity"], o["limit_price"])
            else:
                remaining.append(o)
        d["open_orders"] = remaining
        self.store.save()

    def account(self) -> Account:
        self._process_open_orders()
        d = self.store.data
        syms = sorted(d["positions"])
        px = self.market.prices(syms)
        positions = {
            s: Position(s, p["quantity"], p["avg_cost"], px.get(s, p["avg_cost"]))
            for s, p in d["positions"].items()
        }
        reserved = sum(o["quantity"] * o["limit_price"] for o in d["open_orders"] if o["side"] == "buy")
        return Account(cash=d["cash"], buying_power=d["cash"] - reserved, positions=positions)

    def open_orders(self) -> list[dict]:
        self._process_open_orders()
        return list(self.store.data["open_orders"])

    def place_order(self, req: OrderRequest, price: float) -> OrderResult:
        oid = "paper-" + uuid.uuid4().hex[:10]
        qty = req.estimated_quantity(price)
        base = dict(id=oid, symbol=req.symbol, side=req.side, quantity=round(qty, 6),
                    notional_usd=req.notional_usd, order_type=req.order_type,
                    limit_price=req.limit_price)
        marketable = req.order_type == "market" or (
            (req.side == "buy" and price <= req.limit_price)
            or (req.side == "sell" and price >= req.limit_price)
        )
        if marketable:
            fill_px = price if req.order_type == "market" else req.limit_price
            self._fill(req.symbol, req.side, qty, fill_px)
            self.store.save()
            return OrderResult(**base, status="filled", filled_price=fill_px)
        self.store.data["open_orders"].append({
            "id": oid, "symbol": req.symbol, "side": req.side, "quantity": qty,
            "limit_price": req.limit_price, "created_at": datetime.now(NY).isoformat(),
        })
        self.store.save()
        return OrderResult(**base, status="open", message="limit order resting (good for day)")

    def cancel_order(self, order_id: str) -> str:
        d = self.store.data
        before = len(d["open_orders"])
        d["open_orders"] = [o for o in d["open_orders"] if o["id"] != order_id]
        self.store.save()
        return "cancelled" if len(d["open_orders"]) < before else "no such open order"

    def expire_day_orders(self) -> None:
        """Called at the start of a new trading day: good-for-day orders lapse."""
        self.store.data["open_orders"] = []
        self.store.save()
