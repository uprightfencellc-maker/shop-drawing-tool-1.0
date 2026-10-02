"""CLI entry point: python -m tradebot [run|loop|status] ..."""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from .agent import TradingAgent
from .broker import LiveRobinhoodBroker, PaperBroker, RobinhoodMarketData, RobinhoodSession
from .config import Settings
from .journal import Journal
from .models import OrderRequest
from .risk import RiskManager
from .state import DailyState, Notes
from .tools import ToolExecutor


def confirm_in_terminal(req: OrderRequest, price: float) -> bool:
    size = f"{req.quantity} sh" if req.quantity is not None else f"${req.notional_usd:,.2f}"
    limit = f" @ limit {req.limit_price}" if req.order_type == "limit" else ""
    print(f"\n*** CONFIRM {req.side.upper()} {size} {req.symbol} ({req.order_type}{limit}), last {price}")
    print(f"    rationale: {req.rationale}")
    return input("    place this order? [y/N] ").strip().lower() == "y"


def build(args, settings: Settings):
    live = settings.mode == "live"
    if live and not args.live:
        sys.exit("TRADING_MODE=live requires the --live flag as well. Refusing to start.")
    if args.live and not live:
        sys.exit("--live given but TRADING_MODE is not 'live'. Refusing to start.")

    sd = settings.state_dir
    session = RobinhoodSession(settings.rh_username, settings.rh_password, settings.rh_totp_secret)
    market = RobinhoodMarketData(session)
    if live:
        broker = LiveRobinhoodBroker(session)
    else:
        broker = PaperBroker(market, sd / "paper_portfolio.json", settings.paper_starting_cash)
    daily = DailyState(sd / f"daily_{settings.mode}.json")
    if daily.new_day and isinstance(broker, PaperBroker):
        broker.expire_day_orders()
    notes, journal = Notes(sd / "notes.json"), Journal(sd / "journal.jsonl")
    risk = RiskManager(settings, daily)
    confirm = confirm_in_terminal if (args.confirm or (live and not args.no_confirm)) else None
    executor = ToolExecutor(settings, broker, market, risk, daily, notes, journal, confirm=confirm)
    strategy = Path(args.strategy).read_text() if args.strategy else None
    return TradingAgent(settings, executor, notes, journal, strategy=strategy), executor, market


def run_once(agent: TradingAgent, instructions: str | None) -> None:
    result = agent.run_session(instructions)
    print("\n" + "=" * 70)
    print(result.summary or f"(no summary; stop_reason={result.stop_reason})")
    print(f"\nsteps={result.steps} orders={len(result.orders)} stop={result.stop_reason} usage={result.usage}")


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="tradebot", description="Agentic stock trading bot (Claude + Robinhood)")
    p.add_argument("command", choices=["run", "loop", "status"], help="run one session, loop on a schedule, or print account")
    p.add_argument("--live", action="store_true", help="required together with TRADING_MODE=live to trade real money")
    p.add_argument("--confirm", action="store_true", help="ask before each order (always on in live mode)")
    p.add_argument("--no-confirm", action="store_true", help="live mode only: place orders without asking")
    p.add_argument("--interval", type=int, default=30, help="loop: minutes between sessions (default 30)")
    p.add_argument("--strategy", help="path to a text file that replaces the default strategy")
    p.add_argument("--instructions", help="extra operator instructions for this run")
    p.add_argument("--env", default=".env", help="env file to load (default .env)")
    args = p.parse_args(argv)

    settings = Settings.from_env(args.env)
    agent, executor, market = build(args, settings)

    if args.command == "status":
        text, _ = executor.run("get_account", {})
        print(text)
        return
    if args.command == "run":
        run_once(agent, args.instructions)
        return

    print(f"Looping every {args.interval} min during market hours. Ctrl-C to stop.")
    while True:
        try:
            if market.market_open():
                # Fresh daily counters each session in case the date rolled over.
                agent, executor, market = build(args, settings)
                run_once(agent, args.instructions)
            else:
                print(time.strftime("%H:%M"), "market closed; waiting")
        except KeyboardInterrupt:
            raise
        except Exception as e:  # keep the loop alive across transient API/network errors
            print(f"session failed: {type(e).__name__}: {e}", file=sys.stderr)
        time.sleep(args.interval * 60)


if __name__ == "__main__":
    main()
