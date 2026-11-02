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
    """Return a dict of wide DataFrames: score, eligible, setup, atr, plus regime Series.

    P            : dict of wide frames open/high/low/close/volume/raw_close (adjusted)
    nifty_close  : Series of Nifty 50 closes
    member_mask  : bool DataFrame - stock in point-in-time universe that day
    industry     : dict symbol -> industry name (unknown -> neutral sector score)
    results_soon : optional bool DataFrame - company results due within N days
    """
    p = params
    o, h, l, c, v, raw = P["open"], P["high"], P["low"], P["close"], P["volume"], P["raw_close"]
    nifty = nifty_close.reindex(c.index).ffill()

    sma_f, sma_s = sma(c, p["trend_fast_sma"]), sma(c, p["trend_slow_sma"])
    ema_p = ema(c, p["pullback_ema"])
    a = atr(h, l, c, p["atr_period"])
    bars = c.notna().cumsum()
    traded_value = (raw * v).rolling(p["liquidity_lookback"], min_periods=20).median()

    member = member_mask.reindex(index=c.index, columns=c.columns).fillna(False).astype(bool)
    member &= (bars >= p["min_history_days"]) & (raw >= p["min_price"]) & c.notna()

    # --- momentum and relative strength vs Nifty (skip the most recent few days) ---
    sk = p["mom_skip"]
    mom_l = c.shift(sk) / c.shift(p["mom_long"]) - 1
    mom_s = c.shift(sk) / c.shift(p["mom_short"]) - 1
    n_l = (nifty.shift(sk) / nifty.shift(p["mom_long"]) - 1)
    n_s = (nifty.shift(sk) / nifty.shift(p["mom_short"]) - 1)
    rs_l = mom_l.sub(n_l, axis=0)
    rs_s = mom_s.sub(n_s, axis=0)
    rank_rs_l = xs_rank(rs_l, member)
    rank_rs_s = xs_rank(rs_s, member)

    # --- sector relative strength: average RS of the stock's industry, ranked across industries ---
    sector_rank = pd.DataFrame(0.5, index=c.index, columns=c.columns)
    ind = pd.Series({s: industry.get(s) for s in c.columns}).dropna()
    if len(ind):
        groups = {g: list(cols) for g, cols in ind.groupby(ind).groups.items()}
        rs_m = rs_l.where(member)
        ind_mean = pd.DataFrame({g: rs_m[cols].mean(axis=1) for g, cols in groups.items()})
        ind_rank = ind_mean.rank(axis=1, pct=True)
        for g, cols in groups.items():
            sector_rank[cols] = np.repeat(ind_rank[[g]].values, len(cols), axis=1)
        sector_rank = sector_rank.fillna(0.5)

    # --- trend health ---
    up_trend = (c > sma_f) & (sma_f > sma_s) & (sma_s > sma_s.shift(p["slope_lookback"]))
    not_extended = (c / sma_f - 1) * 100 <= p["max_extension_above_50dma_pct"]
    pct_above = (c > sma_f).astype(float).where(sma_f.notna()).rolling(63, min_periods=40).mean()
    atr_pct = a / c
    trend_q = 0.5 * xs_rank(pct_above, member) + 0.5 * xs_rank(-atr_pct, member)
    liq = xs_rank(traded_value, member)

    # --- entry timing ---
    prior_high = c.shift(1).rolling(p["breakout_lookback"], min_periods=p["breakout_lookback"]).max()
    avg_vol = v.shift(1).rolling(50, min_periods=30).mean()
    rng = (h - l).replace(0, np.nan)
    breakout = (c > prior_high) & (v > p["breakout_volume_mult"] * avg_vol) & ((c - l) / rng >= 0.5)
    touched = l.rolling(5, min_periods=5).min() <= ema_p * (1 + p["pullback_band_pct"] / 100)
    pullback = touched & (c > ema_p) & (c > h.shift(1)) & ~breakout

    # --- market regime (weak-market filter): Nifty above its 200-day average AND breadth ok ---
    breadth = ((c > sma_f) & member).sum(axis=1) / member.sum(axis=1).replace(0, np.nan) * 100
    regime_ok = (nifty > nifty.rolling(p["regime_sma"], min_periods=p["regime_sma"]).mean()) & \
                (breadth >= p["breadth_min_pct_above_50dma"])

    w = p["score_weights"]
    score = (w["rs_long"] * rank_rs_l + w["rs_short"] * rank_rs_s + w["sector_rs"] * sector_rank
             + w["trend_quality"] * trend_q + w["liquidity"] * liq) * 100

    eligible = member & up_trend & not_extended & (rank_rs_l * 100 >= p["min_rs_percentile"]) \
        & (breakout | pullback) & a.notna()
    if results_soon is not None:
        rs_mask = results_soon.reindex(index=c.index, columns=c.columns).fillna(False).astype(bool)
        eligible &= ~rs_mask
    setup = pd.DataFrame(np.where(breakout, "breakout", np.where(pullback, "pullback", "")),
                         index=c.index, columns=c.columns)
    return {"score": score, "eligible": eligible, "setup": setup, "atr": a, "regime_ok": regime_ok,
            "breadth": breadth, "rs_rank": rank_rs_l, "sector_rank": sector_rank,
            "sma50": sma_f, "sma200": sma_s, "ema20": ema_p, "member": member}


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
