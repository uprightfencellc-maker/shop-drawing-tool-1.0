# Agentic Stock Trading Bot (Claude + Robinhood)

Claude runs as an autonomous portfolio manager. Each session it reviews the account, researches
tickers through tools (prices, indicators, fundamentals, news, optional web search), places orders,
and writes notes it reads back in the next session. The code enforces every risk limit before an
order reaches the broker. Claude can't change or get around them.

```
 python -m tradebot run ──► TradingAgent (Claude, tool-use loop)
                               │  get_account / get_quotes / get_price_history /
                               │  get_fundamentals / get_news / get_open_orders /
                               │  place_order / cancel_order / update_notes [/ web_search]
                               ▼
                           ToolExecutor ──► RiskManager (hard limits) ──► Broker
                                                                          ├─ PaperBroker (local ledger, real quotes)
                                                                          └─ LiveRobinhoodBroker (real orders)
```

## Important caveats

- **Robinhood has no official stock-trading API.** This uses the community
  [`robin_stocks`](https://github.com/jmfernandes/robin_stocks) library, which calls Robinhood's
  private app API. It can break without notice, and automated trading may violate Robinhood's
  terms of service. You use it at your own risk.
- **Robinhood has no paper-trading mode.** `paper` mode here uses real Robinhood market data with
  simulated fills in `state/paper_portfolio.json`. Run it in paper mode for a while before going live.
- This is not financial advice, and an LLM can be confidently wrong. Keep the risk limits tight.

## Setup

```bash
cd trading_bot
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # then fill in ANTHROPIC_API_KEY and RH_USERNAME / RH_PASSWORD
```

The first login may ask for an SMS code or approval in the Robinhood app. The session token is
cached in `~/.tokens/`, so later runs skip that step. For unattended runs, turn on authenticator-app
2FA in Robinhood and put the base32 secret in `RH_TOTP_SECRET`.

## Usage

```bash
python -m tradebot status                 # account snapshot as JSON
python -m tradebot run                    # one agent session (paper)
python -m tradebot run --confirm          # ask y/N before every order
python -m tradebot loop --interval 30     # a session every 30 min while the market is open
python -m tradebot run --strategy my_strategy.txt --instructions "Only trade ETFs today"
```

### Live trading

Two switches are both required: `TRADING_MODE=live` in `.env` **and** the `--live` flag.
In live mode the bot asks you to confirm each order in the terminal unless you also pass `--no-confirm`.

```bash
python -m tradebot run --live             # real orders, confirm each one
```

## Risk limits (`.env`)

| Setting | Default | Effect |
|---|---|---|
| `MAX_ORDER_USD` | 500 | Max value of any single order |
| `MAX_POSITION_PCT` | 0.20 | Max size of one position as a fraction of equity |
| `MAX_POSITIONS` | 8 | Max number of distinct holdings |
| `MIN_CASH_RESERVE_PCT` | 0.10 | Buys can't take cash below this fraction of equity |
| `DAILY_LOSS_LIMIT_PCT` | 0.03 | After this drawdown from start-of-day equity, buys are disabled; sells still allowed |
| `MAX_TRADES_PER_DAY` | 10 | Orders per day (counter survives restarts) |
| `LIMIT_PRICE_BAND_PCT` | 0.05 | Limit prices must be within this band of the last price |
| `SYMBOL_ALLOWLIST` / `SYMBOL_BLOCKLIST` | empty | Restrict which tickers can be traded |

The bot is always long-only: no shorting, options, margin, or extended-hours orders.

## Strategy

The default strategy is a swing-trading approach (trend plus pullback, written stops and targets)
in `tradebot/agent.py`. Pass `--strategy file.txt` to replace it with your own plain-English rules.

## Files and state

- `state/journal.jsonl`: audit log of every session, tool call, blocked order and placed order
- `state/notes.json`: the agent's memory (watchlist, theses, stops and targets)
- `state/daily_<mode>.json`: start-of-day equity and trade count
- `state/paper_portfolio.json`: the simulated portfolio (paper mode)

## Model

Uses `claude-opus-5-5` with adaptive thinking (`CLAUDE_EFFORT` sets the effort level) and
server-side refusal fallbacks (`fallbacks: "default"`). Set `CLAUDE_MODEL` to use another model.
Each session costs Anthropic API tokens. Check `usage` in the session output.

## Tests

```bash
python -m pytest -q
```

The tests run offline with a fake market and a fake Claude client. They cover the risk limits,
paper fills and limit orders, daily rollover, and the agent loop.
