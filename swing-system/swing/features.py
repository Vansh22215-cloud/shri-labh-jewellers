"""Indicator/feature calculators for the catalogue (ROADMAP M1 feature store groundwork).
TA-Lib canonical codes are computed with TA-Lib itself (exact parity); the non-TA-Lib items below are implemented
from their standard published formulas. All use only bars up to the current one."""
import numpy as np
import pandas as pd


def talib_feature(code, B, **params):
    """Run any TA-Lib function (by canonical code) per stock; returns the first output as a DataFrame."""
    from talib import abstract
    fn = abstract.Function(code)
    c = B["c"]
    out = pd.DataFrame(np.nan, index=c.index, columns=c.columns)
    for col in c.columns:
        d = pd.DataFrame({"open": B["o"][col], "high": B["h"][col], "low": B["l"][col], "close": c[col],
                          "volume": B["v"][col]}).dropna()
        if len(d) < 50:
            continue
        r = fn({k: d[k].values.astype(float) for k in d}, **params)
        r = r[0] if isinstance(r, list) else r
        out.loc[d.index, col] = r
    return out


def historical_volatility(B, n=20):
    return np.log(B["c"]).diff().rolling(n).std() * np.sqrt(252)


def parkinson_volatility(B, n=20):
    return np.sqrt((np.log(B["h"] / B["l"]) ** 2).rolling(n).mean() / (4 * np.log(2)) * 252)


def garman_klass_volatility(B, n=20):
    hl = 0.5 * np.log(B["h"] / B["l"]) ** 2
    co = (2 * np.log(2) - 1) * np.log(B["c"] / B["o"]) ** 2
    return np.sqrt((hl - co).rolling(n).mean() * 252)


def yang_zhang_volatility(B, n=20):
    o, h, l, c = B["o"], B["h"], B["l"], B["c"]
    on = np.log(o / c.shift(1))
    oc = np.log(c / o)
    rs = np.log(h / c) * np.log(h / o) + np.log(l / c) * np.log(l / o)
    k = 0.34 / (1.34 + (n + 1) / (n - 1))
    return np.sqrt((on.rolling(n).var() + k * oc.rolling(n).var() + (1 - k) * rs.rolling(n).mean()) * 252)


def atr_percentile(B, n=250):
    ap = B["atr"] / B["c"]
    return ap.rolling(n, min_periods=100).rank(pct=True)


def pivot_points_classic(B):
    """Next-day floor pivots from the previous day's high/low/close (known before the next session)."""
    h, l, c = B["h"], B["l"], B["c"]
    pp = (h + l + c) / 3
    return {"pp": pp, "r1": 2 * pp - l, "s1": 2 * pp - h, "r2": pp + (h - l), "s2": pp - (h - l)}


def pivot_points_fibonacci(B):
    h, l, c = B["h"], B["l"], B["c"]
    pp, r = (h + l + c) / 3, (h - l)
    return {"pp": pp, "r1": pp + 0.382 * r, "r2": pp + 0.618 * r, "s1": pp - 0.382 * r, "s2": pp - 0.618 * r}


def pivot_points_camarilla(B):
    h, l, c = B["h"], B["l"], B["c"]
    r = h - l
    return {"r3": c + r * 1.1 / 4, "s3": c - r * 1.1 / 4, "r4": c + r * 1.1 / 2, "s4": c - r * 1.1 / 2}


def elder_impulse(B):
    """+1 green (EMA13 rising and MACD histogram rising), -1 red, 0 blue."""
    from .patterns import _ema
    c = B["c"]
    e13 = _ema(c, 13)
    macd = _ema(c, 12) - _ema(c, 26)
    hist = macd - macd.ewm(span=9, adjust=False).mean()
    up, dn = (e13 > e13.shift(1)) & (hist > hist.shift(1)), (e13 < e13.shift(1)) & (hist < hist.shift(1))
    return up.astype(int) - dn.astype(int)


def market_structure(B):
    """+1 higher-high & higher-low structure, -1 lower-high & lower-low, 0 mixed (from CONFIRMED pivots)."""
    from .catalog import pivots
    PLv, _, PHv, _ = pivots(B)
    hh, hl = PHv[:, :, -1] > PHv[:, :, -2], PLv[:, :, -1] > PLv[:, :, -2]
    lh, ll = PHv[:, :, -1] < PHv[:, :, -2], PLv[:, :, -1] < PLv[:, :, -2]
    v = np.where(hh & hl, 1, np.where(lh & ll, -1, 0))
    return pd.DataFrame(v, index=B["c"].index, columns=B["c"].columns)


def relative_strength_line(B, nifty):
    return B["c"].div(nifty.reindex(B["c"].index).ffill(), axis=0)


def anchored_vwap_daily(B, anchor_days=50):
    """Approximation on DAILY bars: volume-weighted typical price since `anchor_days` ago (true AVWAP needs intraday)."""
    tp = (B["h"] + B["l"] + B["c"]) / 3
    return (tp * B["v"]).rolling(anchor_days).sum() / B["v"].rolling(anchor_days).sum()


NON_TALIB_IMPL = {
    "historical_volatility": "swing/features.py:historical_volatility",
    "parkinson_volatility": "swing/features.py:parkinson_volatility",
    "garman_klass_volatility": "swing/features.py:garman_klass_volatility",
    "yang_zhang_volatility": "swing/features.py:yang_zhang_volatility",
    "atr_percentile": "swing/features.py:atr_percentile",
    "pivot_points_classic": "swing/features.py:pivot_points_classic",
    "pivot_points_fibonacci": "swing/features.py:pivot_points_fibonacci",
    "pivot_points_camarilla": "swing/features.py:pivot_points_camarilla",
    "elder_impulse_system": "swing/features.py:elder_impulse",
    "market_structure_hh_hl": "swing/features.py:market_structure (confirmed pivots)",
    "relative_strength_line": "swing/features.py:relative_strength_line",
    "anchored_vwap": "swing/features.py:anchored_vwap_daily (daily-bar approximation)",
    "heikin_ashi_trend": "swing/patterns.py:heikin_ashi_turn",
    "supertrend_multi": "swing/patterns.py:_supertrend_up (single 10/3 setting; multi-setting not yet)",
    "volatility_squeeze": "swing/families.py:squeeze (Bollinger width percentile)",
}
BLOCKED = {"volume_profile": "needs intraday volume-at-price data",
           "cumulative_volume_delta": "needs tick/aggressor-side data (OHLCV cannot give true delta)",
           "volume_delta": "needs tick/aggressor-side data (OHLCV cannot give true delta)",
           "vwap_deviation_bands": "needs intraday bars (session VWAP)"}
