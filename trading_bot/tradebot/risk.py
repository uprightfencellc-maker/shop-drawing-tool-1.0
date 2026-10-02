"""Hard risk limits. Every order the agent proposes passes through here before it can
reach the broker; the model cannot change or bypass these rules."""
from __future__ import annotations

import re

from .config import Settings
from .models import Account, OrderRequest
from .state import DailyState

SYMBOL_RE = re.compile(r"^[A-Z]{1,5}(\.[A-Z])?$")


class RiskManager:
    def __init__(self, settings: Settings, daily: DailyState):
        self.s = settings
        self.daily = daily

    def drawdown_today(self, account: Account) -> float:
        start = self.daily.ensure_start_equity(account.equity)
        return 0.0 if not start else (account.equity - start) / start

    def loss_limit_hit(self, account: Account) -> bool:
        return self.drawdown_today(account) <= -self.s.daily_loss_limit_pct

    def status(self, account: Account) -> dict:
        return {
            "start_of_day_equity": round(self.daily.ensure_start_equity(account.equity), 2),
            "pnl_today_pct": round(self.drawdown_today(account), 4),
            "loss_limit_hit_buys_disabled": self.loss_limit_hit(account),
            "trades_today": self.daily.trades,
            "trades_remaining_today": max(0, self.s.max_trades_per_day - self.daily.trades),
        }

    def check(self, req: OrderRequest, account: Account, price: float | None, market_open: bool) -> list[str]:
        s, errs = self.s, []

        if not market_open:
            errs.append("market is closed; orders are only allowed during the regular session")
        if not SYMBOL_RE.match(req.symbol):
            errs.append(f"invalid symbol {req.symbol!r}")
        if s.symbol_allowlist and req.symbol not in s.symbol_allowlist:
            errs.append(f"{req.symbol} is not in the symbol allowlist")
        if req.symbol in s.symbol_blocklist:
            errs.append(f"{req.symbol} is blocklisted")
        if req.side not in ("buy", "sell"):
            errs.append("side must be 'buy' or 'sell'")
        if req.order_type not in ("market", "limit"):
            errs.append("order_type must be 'market' or 'limit'")
        if (req.quantity is None) == (req.notional_usd is None):
            errs.append("provide exactly one of quantity or notional_usd")
        if req.quantity is not None and req.quantity <= 0:
            errs.append("quantity must be positive")
        if req.notional_usd is not None and req.notional_usd < 1:
            errs.append("notional_usd must be at least $1")
        if req.order_type == "limit":
            if req.limit_price is None or req.limit_price <= 0:
                errs.append("limit orders need a positive limit_price")
            if req.notional_usd is not None:
                errs.append("limit orders must use quantity, not notional_usd")
            if req.quantity is not None and req.quantity != int(req.quantity):
                errs.append("limit orders must be whole shares")
        if self.daily.trades >= s.max_trades_per_day:
            errs.append(f"daily trade limit reached ({s.max_trades_per_day})")
        if price is None or price <= 0:
            errs.append(f"no current price available for {req.symbol}")
        if errs:
            return errs

        if req.order_type == "limit":
            band = abs(req.limit_price / price - 1)
            if band > s.limit_price_band_pct:
                errs.append(f"limit_price {req.limit_price} is {band:.1%} from last price {price}; "
                            f"max band is {s.limit_price_band_pct:.0%}")

        notional = req.estimated_notional(price)
        qty = req.estimated_quantity(price)
        if notional > s.max_order_usd + 1e-6:
            errs.append(f"order value ${notional:,.2f} exceeds max_order_usd ${s.max_order_usd:,.2f}")

        equity = account.equity
        held = account.positions.get(req.symbol)
        if req.side == "buy":
            if self.loss_limit_hit(account):
                errs.append("daily loss limit hit: new buys are disabled for the rest of the day (sells allowed)")
            if notional > account.buying_power + 1e-6:
                errs.append(f"insufficient buying power (${account.buying_power:,.2f})")
            if account.cash - notional < s.min_cash_reserve_pct * equity - 1e-6:
                errs.append(f"would breach the {s.min_cash_reserve_pct:.0%} cash reserve")
            new_value = (held.market_value if held else 0) + notional
            if new_value > s.max_position_pct * equity + 1e-6:
                errs.append(f"{req.symbol} position would be ${new_value:,.2f}, over the "
                            f"{s.max_position_pct:.0%} of equity cap (${s.max_position_pct * equity:,.2f})")
            if not held and len(account.positions) >= s.max_positions:
                errs.append(f"already at max_positions ({s.max_positions})")
        else:
            have = held.quantity if held else 0
            if qty > have + 1e-6:
                errs.append(f"cannot sell {qty:.4f} {req.symbol}; holding {have:.4f} (no shorting)")
        return errs
