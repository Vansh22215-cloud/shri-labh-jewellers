"""INDICATOR LAB (D105) - the owner's TradingView indicators rebuilt and backtested on NSE data, one by one.

Rebuilt from each script's published rules and standard default inputs (sources were not downloadable; where a
page gives no numbers the well-known defaults of that script are used). Each indicator yields long (and short)
entries and, where it has one, its own exit. Three test modes, all with next-bar-open entry:
  SWING    daily bars, 13 years, point-in-time top-300, LONG only, 0.35% costs, max 30 bars, 4 ATR safety stop
  INTRADAY hourly bars (147 liquid stocks, ~3 years), long AND short, squared off at the day's last bar,
           0.12% costs (MIS: STT, charges, slippage)
  FNO      hourly bars, long AND short (calls / puts), held up to 14 bars (~2 days), 0.30% costs on the underlying
           move (rough allowance for option spread + decay); a fast, large move is what an option buyer needs
Signals with no exit of their own ('events': breaks, sweeps, holds) use a common plan: stop 1.5 ATR, target 3 ATR.
'edge' = average return minus what the market drift alone gave over the same holding time (random entry).
Development / holdout: daily 2023-11, hourly 2025-06.
Usage: python validation/indicator_lab.py swing|intraday|fno [name ...]
"""
import glob
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd

ROOT = "/home/user/shri-labh-jewellers/swing-system"
sys.path.insert(0, ROOT)


# ============================================================ helpers
def rma(x, n):
    return pd.Series(x).ewm(alpha=1 / n, adjust=False).mean().values


def ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False).mean().values


def sma(x, n):
    return pd.Series(x).rolling(n).mean().values


def true_range(h, l, c):
    pc = np.r_[c[0], c[:-1]]
    return np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))


def atr(h, l, c, n=14):
    return rma(true_range(h, l, c), n)


def cross_up(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float) if np.ndim(b) else np.full(len(a), b)
    return np.r_[False, (a[1:] > b[1:]) & (a[:-1] <= b[:-1])]


def cross_dn(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float) if np.ndim(b) else np.full(len(a), b)
    return np.r_[False, (a[1:] < b[1:]) & (a[:-1] >= b[:-1])]


def pivots(h, l, left, right):
    """Pivot highs / lows CONFIRMED `right` bars later: arrays of the level known at each bar (nan before any)."""
    n = len(h)
    ph, pl = np.full(n, np.nan), np.full(n, np.nan)
    ph_at, pl_at = np.full(n, -1), np.full(n, -1)
    last_h = last_l = np.nan
    lh = ll = -1
    for t in range(left + right, n):
        p = t - right
        wh, wl = h[p - left:t + 1], l[p - left:t + 1]
        if h[p] == wh.max() and (h[p - left:p] < h[p]).all():
            last_h, lh = h[p], p
        if l[p] == wl.min() and (l[p - left:p] > l[p]).all():
            last_l, ll = l[p], p
        ph[t], pl[t], ph_at[t], pl_at[t] = last_h, last_l, lh, ll
    return ph, pl, ph_at, pl_at


def linreg_last(y, n):
    """ta.linreg(y, n, 0): value of the least-squares line at the last point of each window."""
    y = pd.Series(y)
    x = np.arange(n)
    xm = x.mean()
    den = ((x - xm) ** 2).sum()
    out = y.rolling(n).apply(lambda w: w.mean() + ((x - xm) * (w - w.mean())).sum() / den * (n - 1 - xm), raw=True)
    return out.values


# ============================================================ the indicators
# each: f(o,h,l,c,v,idx) -> dict(le=long entry, lx=long exit or None, se=short entry, sx=short exit or None,
#                               lstop=optional long stop level array, sstop=...)
IND = {}


def ind(name, kind):
    def deco(f):
        IND[name] = (f, kind)
        return f
    return deco


@ind("SuperTrend (10,3) - KivancOzbilgic", "trend")
def supertrend(o, h, l, c, v, idx, n=10, m=3.0):
    a = atr(h, l, c, n)
    src = (h + l) / 2
    up, dn = src - m * a, src + m * a
    T = np.ones(len(c))
    for t in range(1, len(c)):
        up[t] = max(up[t], up[t - 1]) if c[t - 1] > up[t - 1] else up[t]
        dn[t] = min(dn[t], dn[t - 1]) if c[t - 1] < dn[t - 1] else dn[t]
        T[t] = 1 if (T[t - 1] == -1 and c[t] > dn[t - 1]) else -1 if (T[t - 1] == 1 and c[t] < up[t - 1]) else T[t - 1]
    buy, sell = np.r_[False, (T[1:] == 1) & (T[:-1] == -1)], np.r_[False, (T[1:] == -1) & (T[:-1] == 1)]
    return dict(le=buy, lx=sell, se=sell, sx=buy)


@ind("UT Bot Alerts (key 1, ATR 10)", "trend")
def utbot(o, h, l, c, v, idx, key=1.0, n=10):
    nl = key * atr(h, l, c, n)
    s = np.zeros(len(c))
    for t in range(1, len(c)):
        p = s[t - 1]
        if c[t] > p and c[t - 1] > p:
            s[t] = max(p, c[t] - nl[t])
        elif c[t] < p and c[t - 1] < p:
            s[t] = min(p, c[t] + nl[t])
        else:
            s[t] = c[t] - nl[t] if c[t] > p else c[t] + nl[t]
    buy, sell = cross_up(c, s) & (c > s), cross_dn(c, s) & (c < s)
    return dict(le=buy, lx=sell, se=sell, sx=buy)


@ind("Squeeze Momentum - LazyBear", "momentum")
def squeeze(o, h, l, c, v, idx, n=20, bbm=2.0, kcm=1.5):
    basis = sma(c, n)
    dev = bbm * pd.Series(c).rolling(n).std(ddof=0).values
    rng = sma(true_range(h, l, c), n)
    sqz_on = (basis - dev > basis - kcm * rng) & (basis + dev < basis + kcm * rng)
    sqz_off = (basis - dev < basis - kcm * rng) & (basis + dev > basis + kcm * rng)
    hh, ll = pd.Series(h).rolling(n).max().values, pd.Series(l).rolling(n).min().values
    val = linreg_last(c - ((hh + ll) / 2 + basis) / 2, n)
    fired = sqz_off & np.r_[False, sqz_on[:-1]]
    rising, falling = val > np.r_[np.nan, val[:-1]], val < np.r_[np.nan, val[:-1]]
    return dict(le=fired & (val > 0) & rising, lx=falling, se=fired & (val < 0) & falling, sx=rising)


@ind("CM Williams Vix Fix - market bottoms", "reversal")
def vixfix(o, h, l, c, v, idx, pd_=22, bbl=20, mult=2.0, lb=50, ph=0.85):
    hc = pd.Series(c).rolling(pd_).max().values
    wvf = (hc - l) / hc * 100
    mid = sma(wvf, bbl)
    upper = mid + mult * pd.Series(wvf).rolling(bbl).std(ddof=0).values
    rh = pd.Series(wvf).rolling(lb).max().values * ph
    green = (wvf >= upper) | (wvf >= rh)
    entry = np.r_[False, green[:-1] & ~green[1:]]                # buy when the spike ends (first non-green bar)
    lx = c > sma(c, 5)
    return dict(le=entry, lx=lx, se=None, sx=None)


@ind("WaveTrend Oscillator - LazyBear", "reversal")
def wavetrend(o, h, l, c, v, idx, n1=10, n2=21, os_=-53, ob=53):
    ap = (h + l + c) / 3
    esa = ema(ap, n1)
    d = ema(np.abs(ap - esa), n1)
    ci = (ap - esa) / (0.015 * np.where(d == 0, np.nan, d))
    wt1 = ema(np.nan_to_num(ci), n2)
    wt2 = sma(wt1, 4)
    up, dn = cross_up(wt1, wt2), cross_dn(wt1, wt2)
    return dict(le=up & (wt1 < os_), lx=dn, se=dn & (wt1 > ob), sx=up)


@ind("Trend Magic (CCI 20, ATR 5)", "trend")
def trend_magic(o, h, l, c, v, idx, cn=20, an=5, coeff=1.0):
    tp = (h + l + c) / 3
    m = sma(tp, cn)
    md = pd.Series(tp).rolling(cn).apply(lambda w: np.abs(w - w.mean()).mean(), raw=True).values
    cci = (tp - m) / (0.015 * md)
    a = sma(true_range(h, l, c), an) * coeff
    mt = np.zeros(len(c))
    for t in range(1, len(c)):
        if cci[t] >= 0:
            mt[t] = max(l[t] - a[t], mt[t - 1]) if np.isfinite(a[t]) else l[t]
        else:
            mt[t] = min(h[t] + a[t], mt[t - 1]) if np.isfinite(a[t]) and mt[t - 1] > 0 else h[t] + np.nan_to_num(a[t])
    up, dn = cross_up(cci, 0.0), cross_dn(cci, 0.0)
    return dict(le=up, lx=dn, se=dn, sx=up)


@ind("MACD (12,26,9) cross - ChrisMoody MTF", "trend")
def macd(o, h, l, c, v, idx):
    m = ema(c, 12) - ema(c, 26)
    s = ema(m, 9)
    up, dn = cross_up(m, s), cross_dn(m, s)
    return dict(le=up, lx=dn, se=dn, sx=up)


@ind("S/R Levels with Breaks - LuxAlgo (15/15, vol 20%)", "event")
def lux_sr_breaks(o, h, l, c, v, idx, left=15, right=15, thr=20):
    ph, pl, _, _ = pivots(h, l, left, right)
    e5, e10 = ema(v, 5), ema(v, 10)
    osc = 100 * (e5 - e10) / np.where(e10 == 0, np.nan, e10)
    bull_wick = (o - l) > (c - o)              # LuxAlgo: break candle with a bigger lower wick = 'Bull Wick' (weak)
    bear_wick = (h - o) > (o - c)
    up = cross_up(c, ph) & (osc > thr) & ~bull_wick
    dn = cross_dn(c, pl) & (osc > thr) & ~bear_wick
    return dict(le=up, lx=None, se=dn, sx=None)


@ind("Trendlines with Breaks - LuxAlgo (14, ATR slope)", "event")
def lux_trendlines(o, h, l, c, v, idx, n=14, mult=1.0):
    a = atr(h, l, c, n)
    ph, pl, pha, pla = pivots(h, l, n, n)
    t_ = np.arange(len(c))
    slope = a / n * mult
    # slope is frozen at the pivot: approximate with the slope at the bar the pivot was confirmed
    upper = np.full(len(c), np.nan)
    lower = np.full(len(c), np.nan)
    sl_h = sl_l = np.nan
    last_ph = last_pl = -1
    for t in range(len(c)):
        if pha[t] != last_ph and pha[t] >= 0:
            last_ph, sl_h = pha[t], slope[t]
        if pla[t] != last_pl and pla[t] >= 0:
            last_pl, sl_l = pla[t], slope[t]
        if last_ph >= 0:
            upper[t] = h[last_ph] - sl_h * (t - last_ph)
        if last_pl >= 0:
            lower[t] = l[last_pl] + sl_l * (t - last_pl)
    return dict(le=cross_up(c, upper), lx=None, se=cross_dn(c, lower), sx=None)


@ind("Support Resistance Channels - LonesomeTheBlue", "event")
def sr_channels(o, h, l, c, v, idx, prd=10, width_pct=5, loop=290, min_pivots=2):
    ph, pl, pha, pla = pivots(h, l, prd, prd)
    n = len(c)
    hi300, lo300 = pd.Series(h).rolling(300, min_periods=50).max().values, pd.Series(l).rolling(300, min_periods=50).min().values
    piv = []                      # (bar, price)
    le, se = np.zeros(n, bool), np.zeros(n, bool)
    last_a, last_b = -1, -1
    tops, bots = [], []
    for t in range(n):
        new = False
        if pha[t] >= 0 and pha[t] != last_a:
            piv.append((pha[t], h[pha[t]])); last_a = pha[t]; new = True
        if pla[t] >= 0 and pla[t] != last_b:
            piv.append((pla[t], l[pla[t]])); last_b = pla[t]; new = True
        piv = [p for p in piv if t - p[0] <= loop]
        if new and np.isfinite(hi300[t]):
            w = (hi300[t] - lo300[t]) * width_pct / 100
            chans = []
            for _, p0 in piv:
                members = [p for _, p in piv if abs(p - p0) <= w]
                lo_, hi_ = min(members), max(members)
                if hi_ - lo_ <= w and len(members) >= min_pivots:
                    chans.append((len(members), lo_, hi_))
            chans.sort(reverse=True)
            tops = [x[2] for x in chans[:6]]
            bots = [x[1] for x in chans[:6]]
        if t and tops:
            le[t] = any(c[t] > top >= c[t - 1] for top in tops)
            se[t] = any(c[t] < bot <= c[t - 1] for bot in bots)
    return dict(le=le, lx=None, se=se, sx=None)


@ind("Swing high/low support-resistance (5) - hold", "event")
def swing_hl(o, h, l, c, v, idx, n=5):
    ph, pl, _, _ = pivots(h, l, n, n)
    a = atr(h, l, c, 14)
    hold_s = (l <= pl + 0.1 * a) & (c > pl) & (c > o)          # tested the swing low and closed back above, green
    hold_r = (h >= ph - 0.1 * a) & (c < ph) & (c < o)
    return dict(le=hold_s, lx=None, se=hold_r, sx=None)


@ind("S/R High Volume Boxes - ChartPrime (hold)", "event")
def chartprime_boxes(o, h, l, c, v, idx, look=20, vlen=2):
    ph, pl, pha, pla = pivots(h, l, look, look)
    up_v = np.where(c > o, v, 0.0)
    dn_v = np.where(c < o, v, 0.0)
    delta = pd.Series(up_v - dn_v).rolling(vlen).sum().values      # delta volume around the pivot
    thr = 0.5 * pd.Series(np.abs(delta)).rolling(look * 5, min_periods=look).mean().values
    a = atr(h, l, c, 200 if len(c) > 400 else 50)
    n = len(c)
    sup_lo = sup_hi = res_lo = res_hi = np.nan
    le, se = np.zeros(n, bool), np.zeros(n, bool)
    lb = la = -1
    for t in range(n):
        if pla[t] >= 0 and pla[t] != lb:
            lb = pla[t]
            if delta[lb] > thr[lb]:           # high positive volume at the pivot low -> support box
                sup_lo, sup_hi = l[lb] - 0.5 * a[t], l[lb]
        if pha[t] >= 0 and pha[t] != la:
            la = pha[t]
            if delta[la] < -thr[la]:
                res_lo, res_hi = h[la], h[la] + 0.5 * a[t]
        if t:
            le[t] = np.isfinite(sup_hi) and l[t] <= sup_hi and c[t] > sup_hi and c[t - 1] > sup_lo
            se[t] = np.isfinite(res_lo) and h[t] >= res_lo and c[t] < res_lo and c[t - 1] < res_hi
            if np.isfinite(sup_lo) and c[t] < sup_lo:
                sup_lo = sup_hi = np.nan       # broken support
            if np.isfinite(res_hi) and c[t] > res_hi:
                res_lo = res_hi = np.nan
    return dict(le=le, lx=None, se=se, sx=None)


@ind("RedK VA-CCI dual timeframe (20, HTF x4)", "trend")
def redk_vacci(o, h, l, c, v, idx, n=20, mult=4):
    tp = (h + l + c) / 3

    def vcci(tp_, v_, n_):
        w = pd.Series(v_).replace(0, np.nan).fillna(1.0)
        vm = (pd.Series(tp_) * w).rolling(n_).sum() / w.rolling(n_).sum()
        md = (np.abs(pd.Series(tp_) - vm) * w).rolling(n_).sum() / w.rolling(n_).sum()
        return ((pd.Series(tp_) - vm) / (0.015 * md)).values

    ctf = vcci(tp, v, n)
    htf = vcci(tp, v, n * mult)              # higher-timeframe context approximated by a x4 window
    both_up, both_dn = (ctf > 0) & (htf > 0), (ctf < 0) & (htf < 0)
    le = both_up & ~np.r_[False, both_up[:-1]]
    se = both_dn & ~np.r_[False, both_dn[:-1]]
    return dict(le=le, lx=ctf < 0, se=se, sx=ctf > 0)


def _structure(h, l, c, n):
    """LuxAlgo-style market structure on pivots of length n: BOS / CHoCH events (bull, bear) per bar."""
    ph, pl, pha, pla = pivots(h, l, n, n)
    N = len(c)
    trend = 0
    bull_choch, bull_bos = np.zeros(N, bool), np.zeros(N, bool)
    bear_choch, bear_bos = np.zeros(N, bool), np.zeros(N, bool)
    used_h = used_l = -1
    for t in range(1, N):
        if pha[t] >= 0 and pha[t] != used_h and c[t] > ph[t] and c[t - 1] <= ph[t]:
            used_h = pha[t]
            (bull_choch if trend <= 0 else bull_bos)[t] = True
            trend = 1
        if pla[t] >= 0 and pla[t] != used_l and c[t] < pl[t] and c[t - 1] >= pl[t]:
            used_l = pla[t]
            (bear_choch if trend >= 0 else bear_bos)[t] = True
            trend = -1
    return bull_choch, bull_bos, bear_choch, bear_bos


@ind("Smart Money Concepts - LuxAlgo: internal CHoCH (5)", "event")
def smc_internal_choch(o, h, l, c, v, idx):
    bc, bb, sc, sb = _structure(h, l, c, 5)
    return dict(le=bc, lx=None, se=sc, sx=None)


@ind("Smart Money Concepts - LuxAlgo: internal BOS (5)", "event")
def smc_internal_bos(o, h, l, c, v, idx):
    bc, bb, sc, sb = _structure(h, l, c, 5)
    return dict(le=bb, lx=None, se=sb, sx=None)


@ind("Smart Money Concepts - LuxAlgo: swing CHoCH (50)", "event")
def smc_swing_choch(o, h, l, c, v, idx):
    bc, bb, sc, sb = _structure(h, l, c, 50 if len(c) > 2000 else 20)
    return dict(le=bc, lx=None, se=sc, sx=None)


@ind("Smart Money Concepts - LuxAlgo: FVG retest", "event")
def smc_fvg(o, h, l, c, v, idx):
    n = len(c)
    le, se = np.zeros(n, bool), np.zeros(n, bool)
    bull, bear = [], []                         # open gaps (top, bottom, born)
    for t in range(2, n):
        if l[t] > h[t - 2] and c[t - 1] > o[t - 1]:
            bull.append((l[t], h[t - 2], t))
        if h[t] < l[t - 2] and c[t - 1] < o[t - 1]:
            bear.append((l[t - 2], h[t], t))
        nb = []
        for top, bot, b in bull:
            if t > b and l[t] <= top:
                if c[t] >= bot:
                    le[t] = True                # first return into the gap, closed above its bottom
                continue                        # gap used (or filled)
            if t - b < 50:
                nb.append((top, bot, b))
        bull = nb
        ns = []
        for top, bot, b in bear:
            if t > b and h[t] >= bot:
                if c[t] <= top:
                    se[t] = True
                continue
            if t - b < 50:
                ns.append((top, bot, b))
        bear = ns
    return dict(le=le, lx=None, se=se, sx=None)


@ind("Market Structure Break & Order Block - EmreKb", "event")
def msb_ob(o, h, l, c, v, idx, zz=9, fib=0.33):
    ph, pl, pha, pla = pivots(h, l, zz, zz)
    n = len(c)
    le, se = np.zeros(n, bool), np.zeros(n, bool)
    ob = None
    sob = None
    for t in range(1, n):
        if pha[t] >= 0 and pla[t] >= 0:
            rng = ph[t] - pl[t]
            if c[t] > ph[t] + fib * rng and c[t - 1] <= ph[t - 1] + fib * rng and pla[t] < t:   # bullish MSB
                k = pla[t]
                while k > 0 and not c[k] < o[k]:
                    k -= 1                      # last bearish candle at / before the low = bullish order block
                ob = (l[k], h[k], t)
            if c[t] < pl[t] - fib * rng and c[t - 1] >= pl[t - 1] - fib * rng:
                k = pha[t]
                while k > 0 and not c[k] > o[k]:
                    k -= 1
                sob = (l[k], h[k], t)
        if ob and t > ob[2] and l[t] <= ob[1]:
            if c[t] >= ob[0]:
                le[t] = True
            ob = None
        if sob and t > sob[2] and h[t] >= sob[0]:
            if c[t] <= sob[1]:
                se[t] = True
            sob = None
    return dict(le=le, lx=None, se=se, sx=None)


@ind("HTF Sweep + CISD - WillyAlgoTrader", "event")
def sweep_cisd(o, h, l, c, v, idx):
    """HTF = the day (on hourly bars) / the week (on daily bars). Long: price sweeps the previous HTF low, then a
    candle closes above the open of the first bearish candle of the down-run that made the low, body >= 0.5 ATR.
    Stop = the swept extreme (passed as lstop)."""
    n = len(c)
    key = idx.normalize() if (idx[1] - idx[0]) < pd.Timedelta(days=1) else idx.to_period("W").start_time
    g = pd.Series(np.arange(n), index=idx).groupby(key)
    phl = pd.Series(l).groupby(key.values).transform("min").values
    phh = pd.Series(h).groupby(key.values).transform("max").values
    first = g.transform("min").values
    prev_low, prev_high = np.full(n, np.nan), np.full(n, np.nan)
    keys = pd.Index(key)
    uk = keys.unique()
    lows = pd.Series(l, index=keys).groupby(level=0).min()
    highs = pd.Series(h, index=keys).groupby(level=0).max()
    pos = {k: i for i, k in enumerate(uk)}
    for t in range(n):
        i = pos[keys[t]]
        if i:
            prev_low[t], prev_high[t] = lows.iloc[i - 1], highs.iloc[i - 1]
    a = atr(h, l, c, 14)
    le, se = np.zeros(n, bool), np.zeros(n, bool)
    lstop, sstop = np.full(n, np.nan), np.full(n, np.nan)
    ctx_l = ctx_s = None
    for t in range(1, n):
        if np.isfinite(prev_low[t]) and l[t] < prev_low[t]:
            k = t
            while k > 0 and c[k - 1] < o[k - 1] and t - k < 10:
                k -= 1
            j = k if c[k] < o[k] else t
            ctx_l = {"open": o[j], "low": l[t], "t": t}
        if np.isfinite(prev_high[t]) and h[t] > prev_high[t]:
            k = t
            while k > 0 and c[k - 1] > o[k - 1] and t - k < 10:
                k -= 1
            j = k if c[k] > o[k] else t
            ctx_s = {"open": o[j], "high": h[t], "t": t}
        if ctx_l:
            ctx_l["low"] = min(ctx_l["low"], l[t])
            if c[t] < ctx_l["low"] or t - ctx_l["t"] > 36:
                ctx_l = None
            elif c[t] > ctx_l["open"] and c[t] - o[t] >= 0.5 * a[t]:
                le[t], lstop[t] = True, ctx_l["low"]
                ctx_l = None
        if ctx_s:
            ctx_s["high"] = max(ctx_s["high"], h[t])
            if c[t] > ctx_s["high"] or t - ctx_s["t"] > 36:
                ctx_s = None
            elif c[t] < ctx_s["open"] and o[t] - c[t] >= 0.5 * a[t]:
                se[t], sstop[t] = True, ctx_s["high"]
                ctx_s = None
    return dict(le=le, lx=None, se=se, sx=None, lstop=lstop, sstop=sstop)


@ind("ICT Killzones & Pivots (TFO) - NSE first-hour high/low sweep", "event")
def killzone_sweep(o, h, l, c, v, idx):
    """No ICT killzones exist for NSE; the closest use of 'session high/low pivots' here: the first hour's
    high / low as the session pivot; long when a later bar sweeps the first-hour low and closes back above it."""
    n = len(c)
    le, se = np.zeros(n, bool), np.zeros(n, bool)
    if (idx[1] - idx[0]) >= pd.Timedelta(days=1):
        return dict(le=le, lx=None, se=se, sx=None)      # intraday only
    day = idx.normalize()
    fh = fl = np.nan
    for t in range(n):
        if t == 0 or day[t] != day[t - 1]:
            fh, fl = h[t], l[t]
            continue
        le[t] = l[t] < fl and c[t] > fl
        se[t] = h[t] > fh and c[t] < fh
    return dict(le=le, lx=None, se=se, sx=None)


@ind("Trend Volume Profile & Rolling POC - BigBeluga (trend flip)", "trend")
def beluga_trend(o, h, l, c, v, idx, n=20, an=14, m=1.5):
    mid = ema(c, n)
    a = atr(h, l, c, an)
    T = np.zeros(len(c))
    for t in range(1, len(c)):
        T[t] = 1 if c[t] > mid[t] + m * a[t] else -1 if c[t] < mid[t] - m * a[t] else T[t - 1]
    up = np.r_[False, (T[1:] == 1) & (T[:-1] != 1)]
    dn = np.r_[False, (T[1:] == -1) & (T[:-1] != -1)]
    return dict(le=up, lx=dn, se=dn, sx=up)


@ind("Rolling Candle Profile - Zeiierman (exact port)", "trend")
def rcp(o, h, l, c, v, idx):
    from swing.rolling_profile import signals
    s = signals(pd.DataFrame({"open": o, "high": h, "low": l, "close": c, "volume": v}, index=idx), "price")
    return dict(le=s["buy"].values, lx=s["sell"].values, se=s["sell"].values, sx=s["buy"].values)


# ============================================================ simulation
MODES = {"swing": dict(cost=0.0035, max_bars=30, safety=4.0, short=False, eod=False, split="2023-11-01"),
         "intraday": dict(cost=0.0012, max_bars=7, safety=None, short=True, eod=True, split="2025-06-01"),
         "fno": dict(cost=0.0030, max_bars=14, safety=None, short=True, eod=False, split="2025-06-01")}


def simulate(o, h, l, c, idx, sig, kind, mode, mask=None):
    P = MODES[mode]
    a = atr(h, l, c, 14)
    n = len(c)
    eod = np.r_[idx.normalize()[1:] != idx.normalize()[:-1], True] if P["eod"] else np.zeros(n, bool)
    out = []
    for side in ([1, -1] if P["short"] else [1]):
        ent = sig["le"] if side == 1 else sig["se"]
        ex = sig["lx"] if side == 1 else sig["sx"]
        lvl = sig.get("lstop") if side == 1 else sig.get("sstop")
        if ent is None:
            continue
        ent = np.asarray(ent, bool) & (mask if mask is not None else True)
        i = 0
        while i < n - 2:
            if not ent[i] or not np.isfinite(a[i]) or eod[i]:
                i += 1
                continue
            e = o[i + 1]
            use_plan = ex is None
            if lvl is not None and np.isfinite(lvl[i]):
                risk = abs(e - lvl[i]) + 0.05 * a[i]
            else:
                risk = 1.5 * a[i]
            stop = e - side * risk if use_plan else (e - side * P["safety"] * a[i] if P["safety"] else None)
            tgt = e + side * 2 * risk if use_plan else None
            if use_plan and not 0.25 * a[i] <= risk <= 3 * a[i]:
                i += 1
                continue
            j, px = i + 1, None
            while j < n:
                if stop is not None and (l[j] <= stop if side == 1 else h[j] >= stop):
                    px = min(stop, o[j]) if side == 1 else max(stop, o[j]); break
                if tgt is not None and (h[j] >= tgt if side == 1 else l[j] <= tgt):
                    px = max(tgt, o[j]) if side == 1 else min(tgt, o[j]); break
                if eod[j]:
                    px = c[j]; break
                if j + 1 < n and ((ex is not None and ex[j]) or j - (i + 1) >= P["max_bars"] - 1):
                    px = o[j + 1]; break
                j += 1
            if px is None:
                break
            out.append((idx[i + 1], side, side * (px / e - 1) - P["cost"], j - i))
            i = j + 1
    return out


def drift_per_bar(o, idx, mask=None):
    r = o[2:] / o[1:-1] - 1
    if mask is not None:
        r = r[mask[:-2]]
    return np.nanmean(r) if len(r) else 0.0


# ============================================================ data
def daily_universe():
    from swing import data_prices
    u = pd.read_csv(f"{ROOT}/data/universe_history.csv")
    u["asof"] = pd.to_datetime(u["asof"])
    u = u[u["rank"] <= 300]
    members = {a: set(g["symbol"]) for a, g in u.groupby("asof")}
    months = sorted(members)
    for sym in sorted(set(u["symbol"])):
        d0 = data_prices.load(sym)
        if d0 is None or len(d0) < 300:
            continue
        f = (d0["adj_close"] / d0["close"]).fillna(1.0)
        d = pd.DataFrame({"open": d0.open * f, "high": d0.high * f, "low": d0.low * f, "close": d0.adj_close,
                          "volume": d0.volume}).dropna()
        d = d[d.index >= "2012-01-01"]
        if len(d) < 300:
            continue
        m = np.zeros(len(d), bool)
        for i, a in enumerate(months):
            b = months[i + 1] if i + 1 < len(months) else pd.Timestamp("2100-01-01")
            if sym in members[a]:
                m |= (d.index >= a) & (d.index < b)
        yield sym, d, m


def hourly_universe():
    for fp in sorted(glob.glob(f"{ROOT}/data/intraday/*.csv")):
        d = pd.read_csv(fp, parse_dates=["Datetime"], index_col="Datetime").dropna()
        d = d[(d.high > 0) & (d.low > 0)]
        if len(d) >= 500:
            yield fp.rsplit("/", 1)[-1][:-4], d, None


def _one(args):
    name, mode, sym, d, m = args
    f, kind = IND[name]
    o, h, l, c, v = (d[k].values.astype(float) for k in ("open", "high", "low", "close", "volume"))
    try:
        sig = f(o, h, l, c, v, d.index)
    except Exception as e:
        return name, [], 0.0, 0, repr(e)[:80]
    tr = simulate(o, h, l, c, d.index, sig, kind, mode, m)
    return name, tr, drift_per_bar(o, d.index, m), len(d), None


def run(mode, names):
    data = list(daily_universe() if mode == "swing" else hourly_universe())
    jobs = [(nm, mode, s, d, m) for nm in names for s, d, m in data]
    R, D, errs = {nm: [] for nm in names}, {nm: [] for nm in names}, {}
    with Pool(4) as p:
        for nm, tr, dr, nb, err in p.imap_unordered(_one, jobs, chunksize=4):
            R[nm].extend(tr)
            D[nm].append((dr, nb))
            if err:
                errs[nm] = err
    split = MODES[mode]["split"]
    rows = []
    for nm in names:
        df = pd.DataFrame(R[nm], columns=["date", "side", "ret", "bars"])
        if not len(df):
            rows.append({"indicator": nm, "trades": 0, "note": errs.get(nm, "no trades")})
            continue
        dr = np.average([x for x, _ in D[nm]], weights=[w for _, w in D[nm]])
        df["edge"] = df.ret - df.side * dr * df.bars
        dev, ho = df[df.date < split], df[df.date >= split]
        r = lambda x, k: round(x[k].mean() * 100, 2) if len(x) else None
        rows.append({"indicator": nm, "trades": len(df), "win%": round((df.ret > 0).mean() * 100, 1),
                     "avg%": r(df, "ret"), "edge%": r(df, "edge"), "dev_avg%": r(dev, "ret"),
                     "HOLD_win%": round((ho.ret > 0).mean() * 100, 1) if len(ho) else None, "HOLD_avg%": r(ho, "ret"),
                     "HOLD_edge%": r(ho, "edge"), "long_avg%": r(df[df.side == 1], "ret"),
                     "short_avg%": r(df[df.side == -1], "ret") if (df.side == -1).any() else None,
                     "bars": round(df.bars.mean(), 1), "note": errs.get(nm, "")})
    out = pd.DataFrame(rows)
    out.to_csv(f"{ROOT}/validation/indicator_lab_{mode}.csv", index=False)
    return out


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "swing"
    names = [n for n in IND if len(sys.argv) <= 2 or any(a.lower() in n.lower() for a in sys.argv[2:])]
    pd.set_option("display.width", 250)
    print(f"== {mode} ==")
    print(run(mode, names).to_string(index=False))
