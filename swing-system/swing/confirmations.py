"""Dip-buy CONFIRMATIONS from the owner's TradingView indicators (D105) - same code as validation/indicator_lab.py.

Tested on 13 years of the dip-buy (D98) signals (validation/hp_tiers.py; development / untouched holdout):
  fear spike (CM Williams Vix Fix) + strong zone ....... 454 trades, 79% in profit, +2.7% avg (holdout 81%, +3.0%)
  fear spike, no strong zone ........................... 811 trades, 72%, +1.9%            (holdout 68%, +2.1%)
  NO fear spike, strong zone ...........................  49 trades, 74%, +1.3%            (small sample)
  NO fear spike, no strong zone ........................ 391 trades, 64%, +0.4%            -> NOT sent
  Squeeze ON (LazyBear compression) on the signal day .. 396 trades, 65%, +0.4% (holdout 51%) -> NOT sent
  strong zone = bullish order block (D103) / WaveTrend oversold (LazyBear) / Market Structure Break order block
  (EmreKb) / swing-low hold. Trend-following states (SuperTrend, BigBeluga bullish) made the dip-buy WORSE - unused.
"""
import numpy as np
import pandas as pd

TIERS = {"A": {"rank": 10, "win": 79, "avg": 2.7, "holdout": 81},
         "B": {"rank": 9, "win": 72, "avg": 1.9, "holdout": 68},
         "C": {"rank": 8, "win": 74, "avg": 1.3, "holdout": 67}}


def _ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False).mean().values


def _sma(x, n):
    return pd.Series(x).rolling(n).mean().values


def _tr(h, l, c):
    pc = np.r_[c[0], c[:-1]]
    return np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))


def _pivots(h, l, n):
    N = len(h)
    ph, pl, pha, pla = np.full(N, np.nan), np.full(N, np.nan), np.full(N, -1), np.full(N, -1)
    lh = ll = np.nan
    ah = al = -1
    for t in range(2 * n, N):
        p = t - n
        if h[p] == h[p - n:t + 1].max() and (h[p - n:p] < h[p]).all():
            lh, ah = h[p], p
        if l[p] == l[p - n:t + 1].min() and (l[p - n:p] > l[p]).all():
            ll, al = l[p], p
        ph[t], pl[t], pha[t], pla[t] = lh, ll, ah, al
    return ph, pl, pha, pla


def vix_fix_spike(h, l, c, within=3):
    """CM Williams Vix Fix (22, BB 20/2, 50 x 0.85): a 'fear' spike in the last `within` bars."""
    hc = pd.Series(c).rolling(22).max().values
    wvf = (hc - l) / hc * 100
    up = _sma(wvf, 20) + 2 * pd.Series(wvf).rolling(20).std(ddof=0).values
    green = (wvf >= up) | (wvf >= pd.Series(wvf).rolling(50).max().values * 0.85)
    return pd.Series(green).rolling(within, min_periods=1).max().fillna(0).astype(bool).values


def wavetrend_oversold(h, l, c, level=-53):
    ap = (h + l + c) / 3
    esa = _ema(ap, 10)
    d = _ema(np.abs(ap - esa), 10)
    wt1 = _ema(np.nan_to_num((ap - esa) / (0.015 * np.where(d == 0, np.nan, d))), 21)
    return wt1 < level


def squeeze_on(h, l, c):
    basis = _sma(c, 20)
    dev = 2 * pd.Series(c).rolling(20).std(ddof=0).values
    rng = _sma(_tr(h, l, c), 20)
    return (basis - dev > basis - 1.5 * rng) & (basis + dev < basis + 1.5 * rng)


def swing_low_hold(o, h, l, c, n=5, within=5):
    _, pl, _, _ = _pivots(h, l, n)
    pc = np.r_[c[0], c[:-1]]
    a = pd.Series(_tr(h, l, c)).ewm(alpha=1 / 14, adjust=False).mean().values
    hold = (l <= pl + 0.1 * a) & (c > pl) & (c > o)
    _ = pc
    return pd.Series(hold).rolling(within, min_periods=1).max().fillna(0).astype(bool).values


def msb_order_block(o, h, l, c, zz=9, fib=0.33, within=5):
    """EmreKb Market Structure Break & Order Block: price returns to the bullish order block after a bullish MSB."""
    ph, pl, pha, pla = _pivots(h, l, zz)
    N = len(c)
    le = np.zeros(N, bool)
    ob = None
    for t in range(1, N):
        if pha[t] >= 0 and pla[t] >= 0:
            rng = ph[t] - pl[t]
            if c[t] > ph[t] + fib * rng and c[t - 1] <= ph[t - 1] + fib * rng:
                k = pla[t]
                while k > 0 and not c[k] < o[k]:
                    k -= 1
                ob = (l[k], h[k], t)
        if ob and t > ob[2] and l[t] <= ob[1]:
            le[t] = c[t] >= ob[0]
            ob = None
    return pd.Series(le).rolling(within, min_periods=1).max().fillna(0).astype(bool).values


def assess(a, at_order_block=False):
    """a = ADJUSTED daily bars (open/high/low/close). -> (tier 'A'/'B'/'C' or None = do not send, reasons list)."""
    o, h, l, c = (a[k].values.astype(float) for k in ("open", "high", "low", "close"))
    fear = bool(vix_fix_spike(h, l, c)[-1])
    sqz = bool(squeeze_on(h, l, c)[-1])
    zones = []
    if at_order_block:
        zones.append("order block (demand zone)")
    if wavetrend_oversold(h, l, c)[-1]:
        zones.append("WaveTrend oversold")
    if msb_order_block(o, h, l, c)[-1]:
        zones.append("structure-break order block")
    if swing_low_hold(o, h, l, c)[-1]:
        zones.append("held its swing low")
    why = (["fear spike (Vix Fix) - sellers exhausted"] if fear else []) + zones
    if sqz:
        return None, why + ["Squeeze ON - price compressed, dip-buys fail here"]
    if fear and zones:
        return "A", why
    if fear:
        return "B", why
    if zones:
        return "C", why
    return None, why + ["no fear spike and no support zone - weak dip"]
