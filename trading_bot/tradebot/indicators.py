from __future__ import annotations


def sma(values: list[float], n: int) -> float | None:
    return sum(values[-n:]) / n if len(values) >= n else None


def rsi(values: list[float], n: int = 14) -> float | None:
    if len(values) <= n:
        return None
    gains = losses = 0.0
    for prev, cur in zip(values[-n - 1 : -1], values[-n:]):
        delta = cur - prev
        gains += max(delta, 0)
        losses += max(-delta, 0)
    if losses == 0:
        return 100.0
    rs = gains / losses
    return 100 - 100 / (1 + rs)


def pct_change(values: list[float], lookback: int) -> float | None:
    if len(values) <= lookback or values[-lookback - 1] == 0:
        return None
    return values[-1] / values[-lookback - 1] - 1


def summarize(closes: list[float]) -> dict:
    def r(x, d=4):
        return None if x is None else round(x, d)

    return {
        "last": r(closes[-1], 2) if closes else None,
        "sma_10": r(sma(closes, 10), 2),
        "sma_20": r(sma(closes, 20), 2),
        "sma_50": r(sma(closes, 50), 2),
        "rsi_14": r(rsi(closes, 14), 1),
        "change_1_bar": r(pct_change(closes, 1)),
        "change_5_bars": r(pct_change(closes, 5)),
        "change_20_bars": r(pct_change(closes, 20)),
        "period_high": r(max(closes), 2) if closes else None,
        "period_low": r(min(closes), 2) if closes else None,
    }
