import json

from tradebot.indicators import rsi, sma
from tradebot.state import DailyState


def place(ex, **kw):
    args = {"symbol": "AAPL", "side": "buy", "order_type": "market", "rationale": "test", **kw}
    text, err = ex.run("place_order", args)
    return json.loads(text), err


def test_market_buy_fills_and_updates_account(env):
    out, err = place(env["ex"], notional_usd=1000)
    assert not err and out["status"] == "filled"
    acct, _ = env["ex"].run("get_account", {})
    acct = json.loads(acct)
    assert acct["cash"] == 9000
    assert acct["positions"][0]["symbol"] == "AAPL"
    assert acct["positions"][0]["quantity"] == 5
    assert acct["today"]["trades_today"] == 1


def test_blocks_oversize_order(env):
    out, err = place(env["ex"], notional_usd=1500)
    assert err and "max_order_usd" in out["error"]


def test_blocks_position_concentration(env):
    for _ in range(2):
        assert not place(env["ex"], notional_usd=1000)[1]
    out, err = place(env["ex"], notional_usd=500)  # would be $2,500 of $10,000 equity
    assert err and "20% of equity cap" in out["error"]


def test_no_shorting(env):
    out, err = place(env["ex"], side="sell", quantity=1)
    assert err and "no shorting" in out["error"]


def test_market_closed(env):
    env["market"].open_ = False
    out, err = place(env["ex"], notional_usd=100)
    assert err and "market is closed" in out["error"]


def test_daily_loss_limit_blocks_buys_but_not_sells(env):
    assert not place(env["ex"], notional_usd=1000)[1]
    env["market"].px["AAPL"] = 100.0  # position halves: equity 9500 -> -5% day
    out, err = place(env["ex"], symbol="MSFT", notional_usd=100)
    assert err and "daily loss limit" in out["error"]
    out, err = place(env["ex"], side="sell", quantity=5)
    assert not err and out["status"] == "filled"


def test_trade_count_limit(env):
    for _ in range(5):
        assert not place(env["ex"], symbol="SPY", notional_usd=50)[1]
    out, err = place(env["ex"], symbol="SPY", notional_usd=50)
    assert err and "daily trade limit" in out["error"]


def test_limit_order_rests_then_fills(env):
    out, err = place(env["ex"], order_type="limit", quantity=2, limit_price=195)
    assert not err and out["status"] == "open"
    env["market"].px["AAPL"] = 194.0
    acct = json.loads(env["ex"].run("get_account", {})[0])
    assert acct["positions"][0]["quantity"] == 2
    assert acct["cash"] == 10_000 - 390


def test_limit_band_and_whole_shares(env):
    out, err = place(env["ex"], order_type="limit", quantity=2, limit_price=150)
    assert err and "band" in out["error"]
    out, err = place(env["ex"], order_type="limit", quantity=1.5, limit_price=199)
    assert err and "whole shares" in out["error"]


def test_allowlist(env, tmp_path):
    from dataclasses import replace
    env["risk"].s = replace(env["settings"], symbol_allowlist=frozenset({"SPY"}))
    out, err = place(env["ex"], notional_usd=100)
    assert err and "allowlist" in out["error"]


def test_bad_inputs_return_errors_not_exceptions(env):
    out, err = place(env["ex"], symbol="not a ticker", notional_usd=100)
    assert err
    out, err = place(env["ex"], quantity="ten")
    assert err and "number" in out["error"]
    text, err = env["ex"].run("nope", {})
    assert err


def test_human_decline(env):
    env["ex"].confirm = lambda req, px: False
    out, err = place(env["ex"], notional_usd=100)
    assert err and "declined" in out["error"]
    assert env["daily"].trades == 0


def test_price_history_indicators(env):
    out = json.loads(env["ex"].run("get_price_history", {"symbol": "AAPL", "interval": "day", "span": "3month"})[0])
    assert out["indicators"]["sma_50"] is not None
    assert len(out["recent_bars"]) == 10


def test_daily_state_rolls_over(tmp_path):
    from datetime import date
    d = DailyState(tmp_path / "d.json", today=date(2026, 1, 2))
    d.ensure_start_equity(100)
    d.record_trade()
    d2 = DailyState(tmp_path / "d.json", today=date(2026, 1, 3))
    assert d2.new_day and d2.trades == 0 and d2.start_equity is None


def test_indicators():
    assert sma([1, 2, 3], 3) == 2
    assert rsi(list(range(1, 30))) == 100.0
