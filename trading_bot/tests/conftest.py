import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tradebot.broker import MarketData, PaperBroker
from tradebot.config import Settings
from tradebot.journal import Journal
from tradebot.risk import RiskManager
from tradebot.state import DailyState, Notes
from tradebot.tools import ToolExecutor


class FakeMarket(MarketData):
    def __init__(self, prices=None, open_=True):
        self.px = dict(prices or {"AAPL": 200.0, "MSFT": 400.0, "SPY": 500.0})
        self.open_ = open_

    def prices(self, symbols):
        return {s: self.px[s] for s in symbols if s in self.px}

    def history(self, symbol, interval, span):
        return [{"t": i, "o": 100 + i, "h": 101 + i, "l": 99 + i, "c": 100 + i, "v": 1000} for i in range(60)]

    def fundamentals(self, symbol):
        return {"pe_ratio": "30"}

    def news(self, symbol, limit=8):
        return [{"title": "headline"}]

    def market_open(self):
        return self.open_


@pytest.fixture
def env(tmp_path):
    settings = Settings(state_dir=tmp_path, paper_starting_cash=10_000, max_order_usd=1_000,
                        max_position_pct=0.2, min_cash_reserve_pct=0.1, max_trades_per_day=5)
    market = FakeMarket()
    broker = PaperBroker(market, tmp_path / "paper.json", settings.paper_starting_cash)
    daily = DailyState(tmp_path / "daily.json")
    risk = RiskManager(settings, daily)
    journal = Journal(tmp_path / "journal.jsonl")
    notes = Notes(tmp_path / "notes.json")
    ex = ToolExecutor(settings, broker, market, risk, daily, notes, journal)
    return {"settings": settings, "market": market, "broker": broker, "daily": daily,
            "risk": risk, "journal": journal, "notes": notes, "ex": ex}
