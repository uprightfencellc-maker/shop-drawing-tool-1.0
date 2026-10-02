from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

Side = Literal["buy", "sell"]
OrderType = Literal["market", "limit"]


@dataclass
class Position:
    symbol: str
    quantity: float
    avg_cost: float
    price: float

    @property
    def market_value(self) -> float:
        return self.quantity * self.price

    @property
    def unrealized_pl(self) -> float:
        return (self.price - self.avg_cost) * self.quantity

    def to_dict(self) -> dict:
        d = asdict(self)
        d["market_value"] = round(self.market_value, 2)
        d["unrealized_pl"] = round(self.unrealized_pl, 2)
        d["unrealized_pl_pct"] = round(self.price / self.avg_cost - 1, 4) if self.avg_cost else None
        return d


@dataclass
class Account:
    cash: float
    buying_power: float
    positions: dict[str, Position] = field(default_factory=dict)

    @property
    def equity(self) -> float:
        return self.cash + sum(p.market_value for p in self.positions.values())


@dataclass
class OrderRequest:
    symbol: str
    side: Side
    order_type: OrderType = "market"
    quantity: float | None = None  # shares
    notional_usd: float | None = None  # dollars (market orders only, fractional)
    limit_price: float | None = None
    rationale: str = ""

    def estimated_notional(self, price: float) -> float:
        if self.notional_usd is not None:
            return self.notional_usd
        px = self.limit_price if self.order_type == "limit" and self.limit_price else price
        return (self.quantity or 0) * px

    def estimated_quantity(self, price: float) -> float:
        if self.quantity is not None:
            return self.quantity
        return (self.notional_usd or 0) / price if price else 0


@dataclass
class OrderResult:
    id: str
    symbol: str
    side: str
    status: str  # filled | open | rejected | cancelled | submitted
    quantity: float | None = None
    notional_usd: float | None = None
    order_type: str = "market"
    limit_price: float | None = None
    filled_price: float | None = None
    message: str = ""

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v not in (None, "")}
