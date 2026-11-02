"""Signal generation and scoring (vectorised over a date x symbol panel).

The SAME function is used by the backtest and by the nightly live run, so what
you see in the report is exactly what was tested. All calculations at date t use
only data up to and including the close of date t (no look-ahead); trades are
entered at the NEXT day's open. tests/test_lookahead.py checks this.
"""
import numpy as np
import pandas as pd


def sma(df, n):
    return df.rolling(n, min_periods=n).mean()


def ema(df, n):
    return df.ewm(span=n, adjust=False, min_periods=n).mean()


def atr(high, low, close, n):
    prev = close.shift(1)
    tr = np.maximum(high - low, np.maximum((high - prev).abs(), (low - prev).abs()))
    tr = tr.where(~(high.isna() | low.isna()))
    return tr.rolling(n, min_periods=n).mean()


def xs_rank(df, mask):
    """Cross-sectional percentile rank (0..1) among stocks in the universe that day."""
    return df.where(mask).rank(axis=1, pct=True)


def compute_signals(P, nifty_close, member_mask, industry, params, results_soon=None):
    """Signals for one strategy config (family + parameters). See swing/families.py.
    If results_soon is given, it is applied only when params['results_rule'] == 'exclude'."""
    from .families import base_indicators, family_signals
    B = base_indicators(P, nifty_close, member_mask, industry, params, results_soon)
    return family_signals(B, params)


def trade_plan(close, atr_val, p):
    """Levels for a signal at `close`. Live plans use the signal close as the reference entry."""
    stop = close - p["stop_atr_mult"] * atr_val
    r = close - stop
    return {
        "entry_low": round(close - p["do_not_buy_gap_atr"] * atr_val, 2),
        "entry_high": round(close + p["do_not_buy_gap_atr"] * atr_val, 2),   # do-not-buy-above level
        "stop": round(stop, 2),
        "target1": round(close + p["target1_r"] * r, 2),
        "target2": round(close + p["target2_r"] * r, 2),
    }


def position_size(equity, cash, entry, stop, p):
    """Shares to buy: risk 1% of equity, capped by position cap and available cash."""
    risk_per_share = entry - stop
    if risk_per_share <= 0 or entry <= 0:
        return 0
    by_risk = (equity * p["risk_per_trade_pct"] / 100) / risk_per_share
    by_cap = (equity * p["max_position_pct"] / 100) / entry
    by_cash = cash / (entry * 1.003)   # leave room for charges
    return int(max(0, np.floor(min(by_risk, by_cap, by_cash))))
