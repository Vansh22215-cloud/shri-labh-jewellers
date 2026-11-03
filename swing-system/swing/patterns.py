"""PATTERN LIBRARY: the widely known chart patterns, candlestick patterns and indicator signals
(added 2026-11-03). Every rule uses only bars up to and including the signal day (no look-ahead); the backtest
buys at the next open. Each is an approximation on daily bars of the textbook definition; all are tested the same
honest way (walk-forward, costs, variant counting) by the idea factory before anything is used.

Indicators: MACD, RSI-50 cross, Stochastic, ADX/DMI, Supertrend, Ichimoku, MFI, Chaikin Money Flow, OBV,
CCI, Williams %R, rate of change, golden cross, Keltner channel, Heikin-Ashi.
Volume: pocket pivot, volume dry-up breakout. Volatility: Larry Williams volatility breakout.
Candlesticks: bullish engulfing, hammer, morning star, three white soldiers.
Chart patterns: double bottom, ascending triangle, bull flag, cup and handle.
Events: pre-results run-up.
"""
import numpy as np
import pandas as pd

PATTERN_FAMILIES = ["macd_cross", "rsi50_cross", "stoch_cross", "adx_dmi", "supertrend_flip", "ichimoku_breakout",
                    "mfi_reversal", "cmf_breakout", "obv_breakout", "cci_breakout", "williams_r", "roc_leaders",
                    "golden_cross", "keltner_breakout", "heikin_ashi_turn", "pocket_pivot", "volume_dryup_breakout",
                    "volatility_breakout", "bullish_engulfing", "hammer", "morning_star", "three_white_soldiers",
                    "double_bottom", "ascending_triangle", "bull_flag", "cup_handle", "pre_results_runup"]

DESCRIPTIONS = {
    "macd_cross": "MACD line crosses above its signal line while above zero, above the 200-day average",
    "rsi50_cross": "14-day RSI crosses up through 50 (momentum turning positive) in a long-term uptrend",
    "stoch_cross": "Stochastic %K crosses above %D from below 20 (oversold turn) in a long-term uptrend",
    "adx_dmi": "ADX above 25 (strong trend) and +DI crosses above -DI",
    "supertrend_flip": "Supertrend (10, 3) flips from down to up",
    "ichimoku_breakout": "close breaks above the Ichimoku cloud with Tenkan above Kijun",
    "mfi_reversal": "Money Flow Index crosses up through 20 (selling exhausted) in a long-term uptrend",
    "cmf_breakout": "Chaikin Money Flow above 0.15 (accumulation) with a new 20-day closing high",
    "obv_breakout": "On-Balance Volume at a 50-day high while price is above its 50-day average",
    "cci_breakout": "Commodity Channel Index crosses above +100 (new strength)",
    "williams_r": "Williams %R crosses up through -80 (oversold turn) in a long-term uptrend",
    "roc_leaders": "weekly: top 10% by 20-day rate of change, above the 50-day average",
    "golden_cross": "50-day average crosses above the 200-day average",
    "keltner_breakout": "close above the upper Keltner channel (20-day EMA + 2 ATR)",
    "heikin_ashi_turn": "Heikin-Ashi candle turns green after 3+ red ones, in a long-term uptrend",
    "pocket_pivot": "O'Neil/Kacher pocket pivot: up-day volume above every down-day volume of the prior 10 days, rising 50-day average",
    "volume_dryup_breakout": "volume dried up (5-day average < 60% of normal) then a 20-day breakout on 1.5x volume",
    "volatility_breakout": "Larry Williams volatility breakout: close above open + 0.6 x ATR at a 20-day high",
    "bullish_engulfing": "bullish engulfing candle after a pullback near the 20-day EMA in an uptrend",
    "hammer": "hammer candle (long lower shadow) after a 3-day decline in a long-term uptrend",
    "morning_star": "morning-star three-candle reversal in a long-term uptrend",
    "three_white_soldiers": "three strong up candles in a row closing near their highs",
    "double_bottom": "two similar lows 2-8 weeks apart, then a close above the high between them",
    "ascending_triangle": "flat highs with rising lows over ~6 weeks, then a close above the flat top",
    "bull_flag": "15%+ rise (pole), tight 5-day pause on lighter volume (flag), then a close above the flag",
    "cup_handle": "cup and handle: older high, 15%+ dip and recovery, then a close above that high",
    "pre_results_runup": "strong stock in an uptrend 5-10 days before its results date (pre-results run-up)",
}


def _cross_up(a, b):
    return (a > b) & (a.shift(1) <= b.shift(1))


def _ema(df, n):
    return df.ewm(span=n, adjust=False, min_periods=n).mean()


def _rsi(c, n):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def _supertrend_up(h, l, c, atr, mult=3.0):
    """True when the Supertrend is in 'up' mode (recursive bands, looped over time, vectorised over stocks)."""
    hl2 = ((h + l) / 2).values
    up_b, dn_b = hl2 - mult * atr.values, hl2 + mult * atr.values
    cc = c.values
    T, N = cc.shape
    fu, fd = np.full((T, N), np.nan), np.full((T, N), np.nan)
    trend = np.zeros((T, N), bool)
    for t in range(T):
        if t == 0:
            fu[t], fd[t] = up_b[t], dn_b[t]
            trend[t] = True
            continue
        pu, pd_ = fu[t - 1], fd[t - 1]
        fu[t] = np.where(np.isnan(pu) | (cc[t - 1] < pu) | (up_b[t] > pu), up_b[t], pu)
        fd[t] = np.where(np.isnan(pd_) | (cc[t - 1] > pd_) | (dn_b[t] < pd_), dn_b[t], pd_)
        trend[t] = np.where(cc[t] > fd[t - 1], True, np.where(cc[t] < fu[t - 1], False, trend[t - 1]))
    out = pd.DataFrame(trend, index=c.index, columns=c.columns)
    return out.where(atr.notna(), False)


def signals(fam, B, p):
    """Return (entry DataFrame of bools, setup text) for a pattern family."""
    c, h, l, o, v = B["c"], B["h"], B["l"], B["o"], B["v"]
    a = B["atr"]
    up200 = B["above200"]
    avg_vol = B["avg_vol"]
    if fam == "macd_cross":
        macd = _ema(c, 12) - _ema(c, 26)
        sig = macd.ewm(span=9, adjust=False, min_periods=9).mean()
        e = _cross_up(macd, sig) & (macd > 0) & up200
    elif fam == "rsi50_cross":
        r = _rsi(c, 14)
        e = (r > 50) & (r.shift(1) <= 50) & up200
    elif fam == "stoch_cross":
        lo, hi = l.rolling(14, min_periods=14).min(), h.rolling(14, min_periods=14).max()
        k = 100 * (c - lo) / (hi - lo).replace(0, np.nan)
        d = k.rolling(3).mean()
        e = _cross_up(k, d) & (k.shift(1) < 20) & up200
    elif fam == "adx_dmi":
        upm, dnm = h.diff(), -l.diff()
        pdm = upm.where((upm > dnm) & (upm > 0), 0.0)
        ndm = dnm.where((dnm > upm) & (dnm > 0), 0.0)
        tr = np.maximum(h - l, np.maximum((h - c.shift()).abs(), (l - c.shift()).abs()))
        atr14 = tr.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
        pdi = 100 * pdm.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean() / atr14
        ndi = 100 * ndm.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean() / atr14
        dx = 100 * (pdi - ndi).abs() / (pdi + ndi).replace(0, np.nan)
        adx = dx.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
        e = _cross_up(pdi, ndi) & (adx > 25)
    elif fam == "supertrend_flip":
        st = B.get("_supertrend")
        if st is None:
            st = B["_supertrend"] = _supertrend_up(h, l, c, a)
        e = st & ~st.shift(1, fill_value=False)
    elif fam == "ichimoku_breakout":
        ten = (h.rolling(9).max() + l.rolling(9).min()) / 2
        kij = (h.rolling(26).max() + l.rolling(26).min()) / 2
        sa = ((ten + kij) / 2).shift(26)
        sb = ((h.rolling(52).max() + l.rolling(52).min()) / 2).shift(26)
        top = np.maximum(sa, sb)
        e = (c > top) & (c.shift(1) <= top.shift(1)) & (ten > kij)
    elif fam == "mfi_reversal":
        tp = (h + l + c) / 3
        mf = tp * v
        pos = mf.where(tp > tp.shift(1), 0.0).rolling(14).sum()
        neg = mf.where(tp < tp.shift(1), 0.0).rolling(14).sum()
        mfi = 100 - 100 / (1 + pos / neg.replace(0, np.nan))
        e = (mfi > 20) & (mfi.shift(1) <= 20) & up200
    elif fam == "cmf_breakout":
        mfm = ((c - l) - (h - c)) / (h - l).replace(0, np.nan)
        cmf = (mfm * v).rolling(20).sum() / v.rolling(20).sum()
        e = (cmf > 0.15) & (c > B["hi20"])
    elif fam == "obv_breakout":
        obv = (np.sign(c.diff()).fillna(0) * v.fillna(0)).cumsum()
        e = (obv >= obv.rolling(50, min_periods=50).max()) & (c > B["sma50"])
    elif fam == "cci_breakout":
        tp = (h + l + c) / 3
        cci = (tp - tp.rolling(20).mean()) / (0.015 * 0.8 * tp.rolling(20).std())   # MAD ~ 0.8 x std (approx.)
        e = (cci > 100) & (cci.shift(1) <= 100)
    elif fam == "williams_r":
        wr = -100 * (h.rolling(14).max() - c) / (h.rolling(14).max() - l.rolling(14).min()).replace(0, np.nan)
        e = (wr > -80) & (wr.shift(1) <= -80) & up200
    elif fam == "roc_leaders":
        roc = c / c.shift(20) - 1
        rk = roc.where(B["member"]).rank(axis=1, pct=True)
        ws = pd.DataFrame(np.repeat(B["week_start"].to_numpy(dtype=bool)[:, None], c.shape[1], axis=1),
                          index=c.index, columns=c.columns)
        e = ws & (rk >= 0.9) & (c > B["sma50"])
    elif fam == "golden_cross":
        e = _cross_up(B["sma50"], B["sma200"])
    elif fam == "keltner_breakout":
        e = (c > B["ema20"] + 2 * a) & (c.shift(1) <= B["ema20"].shift(1) + 2 * a.shift(1))
    elif fam == "heikin_ashi_turn":
        hac = (o + h + l + c) / 4
        hao = (o.shift(1) + c.shift(1)) / 2          # common non-recursive approximation
        green = hac > hao
        red3 = (~green.shift(1, fill_value=True)) & (~green.shift(2, fill_value=True)) & (~green.shift(3, fill_value=True))
        e = green & red3 & up200
    elif fam == "pocket_pivot":
        down_vol = v.where(c < c.shift(1))
        e = (c > c.shift(1)) & (v > down_vol.shift(1).rolling(10, min_periods=1).max()) & \
            (c > B["sma50"]) & (B["sma50"] > B["sma50"].shift(10))
    elif fam == "volume_dryup_breakout":
        dry = v.shift(1).rolling(5).mean() < 0.6 * avg_vol
        e = dry.shift(1).fillna(False).astype(bool) & (c > B["hi20"]) & (v > 1.5 * avg_vol)
    elif fam == "volatility_breakout":
        e = (c > o + 0.6 * a.shift(1)) & (c > B["hi20"])
    elif fam == "bullish_engulfing":
        e = (c.shift(1) < o.shift(1)) & (c > o) & (o <= c.shift(1)) & (c >= o.shift(1)) & \
            (l <= B["ema20"] * 1.02) & B["up_trend"]
    elif fam == "hammer":
        body = (c - o).abs()
        lower = np.minimum(o, c) - l
        upper = h - np.maximum(o, c)
        e = (lower >= 2 * body) & (upper <= body) & (body > 0) & B["down3"].shift(1, fill_value=False) & up200
    elif fam == "morning_star":
        b2 = (o.shift(2) - c.shift(2))
        small = (c.shift(1) - o.shift(1)).abs() < 0.3 * b2
        e = (b2 > a.shift(2) * 0.8) & small & (c > o) & (c > (o.shift(2) + c.shift(2)) / 2) & up200
    elif fam == "three_white_soldiers":
        g = lambda k: (c.shift(k) > o.shift(k)) & ((h.shift(k) - c.shift(k)) <= 0.25 * (h.shift(k) - l.shift(k)))
        e = g(0) & g(1) & g(2) & (c > c.shift(1)) & (c.shift(1) > c.shift(2)) & up200
    elif fam == "double_bottom":
        low1 = l.shift(20).rolling(20, min_periods=20).min()       # 20-40 days ago
        low2 = l.rolling(15, min_periods=15).min()                  # last 15 days
        neck = h.shift(1).rolling(25, min_periods=25).max()
        e = ((low2 / low1 - 1).abs() < 0.03) & (c > neck) & (c.shift(1) <= neck.shift(1)) & (neck < low1 * 1.25)
    elif fam == "ascending_triangle":
        top_recent, top_old = h.shift(1).rolling(15).max(), h.shift(16).rolling(15).max()
        flat = (top_recent / top_old - 1).abs() < 0.02
        rising = l.rolling(10).min() > l.shift(20).rolling(10).min() * 1.03
        e = flat & rising & (c > np.maximum(top_recent, top_old))
    elif fam == "bull_flag":
        pole = c.shift(5) / c.shift(15) - 1
        rng = (c.shift(1).rolling(5).max() - c.shift(1).rolling(5).min()) / c.shift(5)
        quiet = v.shift(1).rolling(5).mean() < avg_vol
        e = (pole >= 0.15) & (rng <= 0.07) & quiet & (c > h.shift(1).rolling(5).max())
    elif fam == "cup_handle":
        hi = h.shift(5).rolling(115, min_periods=115).max()
        old_hi = h.shift(40).rolling(80, min_periods=80).max()          # the high sits in the older part
        dip = l.shift(5).rolling(100, min_periods=100).min()
        e = (old_hi >= hi * 0.999) & (dip <= hi * 0.85) & (c > hi) & (c.shift(1) <= hi.shift(1)) & up200
    elif fam == "pre_results_runup":
        rs = B.get("results_soon")
        if rs is None:
            raise ValueError("results dates not available")
        e = rs & B["up_trend"] & (B["rs_rank"] >= 0.6) & (c > B["hi20"] * 0.98)
    else:
        raise ValueError(f"unknown pattern family {fam}")
    return e.fillna(False).astype(bool), DESCRIPTIONS[fam]
