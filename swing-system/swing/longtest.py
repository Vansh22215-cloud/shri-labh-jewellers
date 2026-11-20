"""LONG TEST of the practice trader's rules on years of Kite 5-minute history (owner 20 Nov: "go ahead with the
weekend tests"; goal ₹10,000+ a day on ₹50,800).

1. STOCKS - the opening-range breakout exactly as live (autotrader.py), for every NSE stock on every day:
   the day's 100 most-traded stocks by value 9:15-9:30; a 5-minute close beyond the 9:15-9:30 range, on the VWAP
   side, with N x the day's average 5-minute volume; entry at the next candle's open (+0.05% slippage); stop,
   target, stop-to-entry after +1 stop distance, sold by 3:15 pm; at most 3 a day and 2 at a time; ~₹1,500 risk;
   Zerodha intraday charges. Settings tried: stop 0.75/1/1.5%, target 1.5/2/3%, volume 1.2/1.5/2x, last entry
   10:30/11:30/13:00, long+short or long only.
2. NIFTY OPTIONS - Kite keeps NO candles of expired options, so the option rule is tested as an ESTIMATE: the same
   signal on NIFTY 50's 5-minute candles, the at-the-money option assumed to cost 0.35% of NIFTY and to move half
   as much as NIFTY (delta 0.5, time decay ignored = flattering). Settings tried: stop 20/30/40%, target
   40/60/100%, last entry 12:30/14:30.
Fair check: settings are chosen on the years BEFORE 2024 and then shown on 2024 onwards ("recent", not used for the
choice). Only the recent result says whether a setting is worth using.
Results: results/long_test.md (no prices) + a Telegram summary. Data: Kite 5-minute candles only."""
import itertools
import json
import os

import numpy as np
import pandas as pd

from . import candles, costs
from .config import DATA, RESULTS, get_logger, load_settings

log = get_logger()
REPORT = RESULTS / "long_test.md"
CUT = pd.Timestamp("2024-01-01")
STK_GRID = dict(vol=[1.5, 2.0], last=["11:30", "13:00"], sides=["both", "long"], stop=[0.0075, 0.01, 0.015],
                target=[0.015, 0.02, 0.03])
SIG = list(itertools.product(STK_GRID["vol"], STK_GRID["last"], STK_GRID["sides"]))
EXI = list(itertools.product(STK_GRID["stop"], STK_GRID["target"]))
OPT_GRID = dict(stop=[0.2, 0.3, 0.4], target=[0.4, 0.6, 1.0], last=["12:30", "14:30"])
# extra factors (owner 20 Nov: "support, resistance, high, low, open, close, volume and so many things matter"),
# each tested on its own and together, INSIDE the signal (it waits for the first breakout that passes them):
FILTERS = {1: "beyond yesterday's high/low", 2: "NIFTY moving the same way", 4: "stronger than NIFTY today",
           8: "India VIX below 20", 16: "no resistance within 1%"}
MASKS = [0, 1, 2, 4, 8, 16, 1 | 2, 2 | 4, 1 | 4, 2 | 8, 1 | 2 | 4, 2 | 4 | 16, 1 | 2 | 4 | 8, 31]
LIVE_SIG = SIG.index((1.5, "11:30", "both"))
# SCALING OUT (owner 21 Nov: "big traders book part at 1:1 or 1:2 and run the rest at cost"): book `frac` of the
# position at 1R (R = the stop distance), move the stop on the rest to the entry, let the rest run to t2 R.
SCALE = list(itertools.product([0.0075, 0.01, 0.015], [0.5, 2 / 3], [2.0, 3.0]))      # (stop, frac, t2 in R)
OPT_SCALE = list(itertools.product([0.2, 0.3, 0.4], [0.5, 2 / 3], [2.0, 3.0]))
_CTX = {}


def _ctx():
    """NIFTY 5-minute (day open + close at each candle end) and India VIX daily, once per worker."""
    if not _CTX:
        n = candles.load("NIFTY50", "5minute", adjusted=False)
        nd = {}
        if n is not None:
            for day, g in _days(n):
                nd[day] = (float(g["open"].iloc[0]), dict(zip([t.hour * 60 + t.minute + 5 for t in g.index], g["close"].values)))
        vix = candles.load("INDIAVIX", "day", adjusted=False)
        vs = vix["close"] if vix is not None else pd.Series(dtype=float, index=pd.DatetimeIndex([]))
        _CTX.update(nifty=nd, vix=vs, vixprev=dict(zip(vs.index[1:], vs.values[:-1])) if len(vs) > 1 else {})
    return _CTX


def vix_before(day):
    """India VIX at the close of the trading day before `day` (known before the day starts)."""
    ctx = _ctx()
    if day in ctx["vixprev"]:
        return float(ctx["vixprev"][day])
    v = ctx["vix"]
    v = v[v.index < day]
    return float(v.iloc[-1]) if len(v) else None


def factor_flags(day, lng, c_i, open0, end_i, px, prev_hi, prev_lo):
    ctx = _ctx()
    f = 0
    if prev_hi is not None and ((lng and c_i > prev_hi) or (not lng and c_i < prev_lo)):
        f |= 1
    nopen, ncl = ctx["nifty"].get(day, (None, {}))
    nc = ncl.get(end_i)
    if nopen and nc is not None:
        if (lng and nc > nopen) or (not lng and nc < nopen):
            f |= 2
        if (lng and c_i / open0 - 1 > nc / nopen - 1) or (not lng and c_i / open0 - 1 < nc / nopen - 1):
            f |= 4
    vx = vix_before(day)
    if vx is not None and vx < 20:
        f |= 8
    if prev_hi is not None:
        res = prev_hi if lng else prev_lo
        if not ((lng and px < res < px * 1.01) or (not lng and px * 0.99 < res < px)):
            f |= 16
    return f
LIVE_STK = dict(stop=0.01, target=0.02, vol=1.5, last="11:30", sides="both")
LIVE_OPT = dict(stop=0.3, target=0.6, last="14:30", factors=0)
MAX_SCALE = {"stocks": 1.6, "nifty": 4.8}    # how much bigger the risk per trade can get with ₹50,800 (margin/premium)


def _days(d):
    d = d[(d.index.time >= pd.Timestamp("09:15").time()) & (d.index.time < pd.Timestamp("15:30").time())]
    return d.groupby(d.index.normalize())


def _simulate(o, h, l, c, ends, i0, px, side, stop_f, tgt_f):
    """One trade from bar i0 (entry at its open = px). -> (exit price, why, exit index)."""
    lng = side == "LONG"
    stop = px * (1 - stop_f) if lng else px * (1 + stop_f)
    tgt = px * (1 + tgt_f) if lng else px * (1 - tgt_f)
    be = px * (1 + stop_f) if lng else px * (1 - stop_f)
    for j in range(i0, len(o)):
        if (l[j] <= stop) if lng else (h[j] >= stop):
            return (min(o[j], stop) if lng else max(o[j], stop)), "stop", j
        if (h[j] >= tgt) if lng else (l[j] <= tgt):
            return (max(o[j], tgt) if lng else min(o[j], tgt)), "target", j
        if ends[j] >= "15:15":
            return c[j], "square-off", j
        if ((h[j] >= be) if lng else (l[j] <= be)) and ((stop < px) if lng else (stop > px)):
            stop = px
    return c[-1], "square-off", len(o) - 1


def _hm(x):
    return int(x[:2]) * 60 + int(x[3:])


def fast_trade(o, h, l, c, end_m, i0, px, lng, stop_f, tgt_f):
    """The same exit rules as _simulate, with array maths: stop, target, stop-to-entry after +1 stop distance
    (from the next candle on), square-off at 3:15 pm. -> (exit price, exit index)."""
    n = len(o)
    sq = np.flatnonzero(end_m[i0:] >= 915)            # 3:15 pm
    j_end = i0 + (sq[0] if len(sq) else n - 1 - i0)
    seg = slice(i0, j_end + 1)
    stop = px * (1 - stop_f) if lng else px * (1 + stop_f)
    tgt = px * (1 + tgt_f) if lng else px * (1 - tgt_f)
    be = px * (1 + stop_f) if lng else px * (1 - stop_f)
    hs = (l[seg] <= stop) if lng else (h[seg] >= stop)
    ht = (h[seg] >= tgt) if lng else (l[seg] <= tgt)
    hb = (h[seg] >= be) if lng else (l[seg] <= be)
    BIG = 10 ** 6
    first = lambda a: int(np.argmax(a)) if a.any() else BIG
    js, jt, jb = first(hs), first(ht), first(hb)
    m = j_end - i0
    if min(js, jt) <= jb or jb >= m:
        j = min(js, jt, m)
        if j == js:
            return (min(o[i0 + j], stop) if lng else max(o[i0 + j], stop)), i0 + j
        if j == jt:
            return (max(o[i0 + j], tgt) if lng else min(o[i0 + j], tgt)), i0 + j
        return c[j_end], j_end
    hs2 = (l[seg] <= px) if lng else (h[seg] >= px)
    hs2[: jb + 1] = False
    js2 = first(hs2)
    j = min(js2, jt, m)
    if j == js2:
        return (min(o[i0 + j], px) if lng else max(o[i0 + j], px)), i0 + j
    if j == jt:
        return (max(o[i0 + j], tgt) if lng else min(o[i0 + j], tgt)), i0 + j
    return c[j_end], j_end


def scale_trade(o, h, l, c, end_m, i0, px, lng, stop_f, frac, t2_r):
    """Book `frac` at 1R, stop to entry, rest to t2_r R (stop first if both in one candle). -> (exit1, exit2, frac
    actually booked at 1R (0 if 1R never came), index of the last exit)."""
    n = len(o)
    sq = np.flatnonzero(end_m[i0:] >= 915)
    j_end = i0 + (sq[0] if len(sq) else n - 1 - i0)
    stop = px * (1 - stop_f) if lng else px * (1 + stop_f)
    t1 = px * (1 + stop_f) if lng else px * (1 - stop_f)
    t2 = px * (1 + t2_r * stop_f) if lng else px * (1 - t2_r * stop_f)
    seg = slice(i0, j_end + 1)
    BIG = 10 ** 6
    first = lambda a: int(np.argmax(a)) if a.any() else BIG
    js = first((l[seg] <= stop) if lng else (h[seg] >= stop))
    j1 = first((h[seg] >= t1) if lng else (l[seg] <= t1))
    m = j_end - i0
    if js <= j1 or j1 > m:                                   # stopped (or day over) before 1R: everything out
        if js <= m and js <= j1:
            e = min(o[i0 + js], stop) if lng else max(o[i0 + js], stop)
            return e, e, 0.0, i0 + js
        return c[j_end], c[j_end], 0.0, j_end
    e1 = max(o[i0 + j1], t1) if lng else min(o[i0 + j1], t1)
    k0 = i0 + j1 + 1                                         # the rest: from the next candle, stop at the entry
    if k0 > j_end:
        return e1, c[j_end], frac, j_end
    seg2 = slice(k0, j_end + 1)
    js2 = first((l[seg2] <= px) if lng else (h[seg2] >= px))
    jt2 = first((h[seg2] >= t2) if lng else (l[seg2] <= t2))
    m2 = j_end - k0
    j = min(js2, jt2, m2)
    if j == js2 and js2 <= m2:
        e2 = min(o[k0 + j], px) if lng else max(o[k0 + j], px)
    elif j == jt2 and jt2 <= m2:
        e2 = max(o[k0 + j], t2) if lng else min(o[k0 + j], t2)
    else:
        e2, j = c[j_end], m2
    return e1, e2, frac, k0 + j


def stock_values(sym):
    """Pass 1: traded value 9:15-9:30 of every day (to find each day's 100 most-traded stocks)."""
    d = candles.load(sym, "5minute", adjusted=False)
    if d is None or len(d) < 50:
        return []
    x = d[(d.index.time >= pd.Timestamp("09:15").time()) & (d.index.time < pd.Timestamp("09:30").time())]
    v = (x["close"] * x["volume"]).groupby(x.index.normalize()).sum()
    return [(day, sym, float(val)) for day, val in v.items()]


def stock_trades(args):
    """Pass 2: for each day the stock was in the top 100, the first signal of every setting and its net result
    in rupees with the live sizing, charges and slippage."""
    sym, days = args
    d = candles.load(sym, "5minute")
    out = []
    if d is None or not days:
        return out
    days = set(days)
    prev_close = prev_hi = prev_lo = None
    for day, g in _days(d):
        last_close = float(g["close"].iloc[-1]) if len(g) else prev_close
        p_hi, p_lo = prev_hi, prev_lo
        if len(g):
            prev_hi, prev_lo = float(g["high"].max()), float(g["low"].min())
        if day not in days or len(g) < 10:
            prev_close = last_close
            continue
        o, h, l, c, v = (g[k].values.astype(float) for k in ("open", "high", "low", "close", "volume"))
        starts = np.array([t.hour * 60 + t.minute for t in g.index]) - 555
        end_m = starts + 555 + 5                       # minutes after midnight at each candle's END (9:20 = 560)
        first = starts < 15
        gap_ok = prev_close is None or abs(o[0] / prev_close - 1) <= 0.03
        prev_close = last_close
        if first.sum() < 3 or not gap_ok:
            continue
        hi, lo = h[first].max(), l[first].min()
        cvol = np.cumsum(v)
        vwap = np.where(cvol > 0, np.cumsum(c * v) / np.maximum(cvol, 1e-9), c)
        idx = np.arange(len(v))
        prior = np.where(idx > 0, (cvol - v) / np.maximum(idx, 1), np.nan)
        strength = np.where(prior > 0, v / prior, 0)
        jobs = [(si, 0) for si in range(len(SIG))] + [(LIVE_SIG, m) for m in MASKS if m]
        flag_cache = {}
        for si, mask in jobs:
            vol_m, last, sides = SIG[si]
            ok = (end_m >= 575) & (end_m <= _hm(last)) & (strength >= vol_m)
            up = ok & (c > hi) & (c > vwap)
            dn = ok & (c < lo) & (c < vwap) if sides == "both" else np.zeros(len(c), bool)
            cand = np.flatnonzero(up | dn)
            i = None
            for k in cand:
                if k + 1 >= len(o):
                    break
                if mask:
                    if k not in flag_cache:
                        flag_cache[k] = factor_flags(day, bool(up[k]), c[k], o[0], int(end_m[k]), o[k + 1], p_hi, p_lo)
                    if flag_cache[k] & mask != mask:
                        continue
                i = k
                break
            if i is None:
                continue
            lng = bool(up[i])
            px = o[i + 1]
            for ei, (stop_f, tgt_f) in enumerate(EXI):
                ex, j = fast_trade(o, h, l, c, end_m, i + 1, px, lng, stop_f, tgt_f)
                slp = 0.0005 * px
                buy, sell = ((px + slp), (ex - slp)) if lng else ((ex + slp), (px - slp))
                qty = int(min(1500 / (px * stop_f), 50800 * 4 * 0.45 / px))      # 4x intraday margin (cautious)
                if qty < 1:
                    continue
                net = qty * (sell - buy) - costs.intraday_cost(qty * buy, qty * sell)
                combo = si * len(EXI) + ei if not mask else 1000 + mask * 16 + ei
                out.append((day, sym, int(end_m[i]), int(end_m[j]), combo, float(net), float(strength[i])))
            if si == LIVE_SIG and not mask:                  # scaling out, on the live signal
                for ki, (stop_f, frac, t2_r) in enumerate(SCALE):
                    qty = int(min(1500 / (px * stop_f), 50800 * 4 * 0.45 / px))
                    if qty < 2:
                        continue
                    e1, e2, fb, j = scale_trade(o, h, l, c, end_m, i + 1, px, lng, stop_f, frac, t2_r)
                    q1 = int(round(qty * fb)) if fb else 0
                    q1 = min(max(q1, 1), qty - 1) if fb else 0
                    slp = 0.0005 * px
                    net = 0.0
                    for q, ex in ((q1, e1), (qty - q1, e2)):
                        if q < 1:
                            continue
                        buy, sell = ((px + slp), (ex - slp)) if lng else ((ex + slp), (px - slp))
                        net += q * (sell - buy) - costs.intraday_cost(q * buy, q * sell)
                    out.append((day, sym, int(end_m[i]), int(end_m[j]), 3000 + ki, float(net), float(strength[i])))
    return out


def stock_portfolio(T, combo_id):
    """Daily results of one setting with the live limits (3 a day, 2 at a time, strongest first)."""
    X = T[T["combo"] == combo_id].sort_values(["day", "t_in", "strength"], ascending=[True, True, False])
    out = []
    for day, g in X.groupby("day", sort=False):
        taken, net = [], 0.0
        for t_in, t_out, nt in zip(g["t_in"].values, g["t_out"].values, g["net"].values):
            if len(taken) >= 3 or sum(1 for t in taken if t > t_in) >= 2:
                continue
            net += nt
            taken.append(t_out)
        out.append((day, net, len(taken)))
    return pd.DataFrame(out, columns=["day", "net", "trades"])


NMASKS = {0: "none", 1: "beyond yesterday's high/low", 8: "India VIX below 20", 9: "both"}


def nifty_test():
    """The NIFTY option rule as an estimate on NIFTY 50 5-minute candles. -> {(stop, target, last, mask): daily}."""
    d = candles.load("NIFTY50", "5minute")
    res = {}
    if d is None or len(d) < 1000:
        return res
    days, prev = [], None
    for day, g in _days(d):
        if len(g) >= 20:
            days.append((day, g, prev, vix_before(day)))
        prev = (float(g["high"].max()), float(g["low"].min())) if len(g) else prev
    for stop_f, tgt_f, last, mask in itertools.product(OPT_GRID["stop"], OPT_GRID["target"], OPT_GRID["last"], NMASKS):
        rows = []
        for day, g, pd_hl, vx in days:
            if mask & 8 and (vx is None or vx >= 20):
                rows.append((day, 0.0, 0))
                continue
            o, h, l, c = (g[k].values.astype(float) for k in ("open", "high", "low", "close"))
            starts = g.index.strftime("%H:%M").values
            ends = (g.index + pd.Timedelta(minutes=5)).strftime("%H:%M").values
            first = starts < "09:30"
            hi, lo, dopen = h[first].max(), l[first].min(), o[0]
            if mask & 1 and pd_hl:
                hi, lo = max(hi, pd_hl[0]), min(lo, pd_hl[1])      # must also clear yesterday's high / low
            ema = pd.Series(c).ewm(span=20, adjust=False).mean().values
            net, n, i = 0.0, 0, 0
            while n < 2:
                ok = (ends >= "09:35") & (ends <= last) & (np.arange(len(c)) >= i)
                up = ok & (c > hi) & (c > ema) & (c > dopen)
                dn = ok & (c < lo) & (c < ema) & (c < dopen)
                sig = np.flatnonzero(up | dn)
                if not len(sig) or sig[0] + 1 >= len(c):
                    break
                k = sig[0]
                s0 = o[k + 1]
                p0 = 0.0035 * s0
                sgn = 1 if up[k] else -1
                po = p0 + 0.5 * sgn * (o - s0)
                ph = p0 + 0.5 * np.where(sgn > 0, h - s0, s0 - l)
                pl = p0 + 0.5 * np.where(sgn > 0, l - s0, s0 - h)
                pc = p0 + 0.5 * sgn * (c - s0)
                ex, why, j = _simulate(po, ph, pl, pc, ends, k + 1, p0, "LONG", stop_f, tgt_f)
                ex = max(ex, 0.05)
                lots = int(min(3000 / (stop_f * p0 * 65), 50800 * 0.95 / (p0 * 65)))
                if lots >= 1:
                    q = lots * 65
                    b, s_ = p0 + max(0.05, 0.003 * p0), ex - max(0.05, 0.003 * ex)
                    net += q * (s_ - b) - costs.option_cost(q * b, q * s_)
                n += 1
                i = j + 1
            rows.append((day, net, n))
        res[(stop_f, tgt_f, last, mask)] = pd.DataFrame(rows, columns=["day", "net", "trades"])
    for stop_f, frac, t2_r in OPT_SCALE:                     # scaling out, live signal (last entry 2:30 pm)
        rows = []
        for day, g, pd_hl, vx in days:
            o, h, l, c = (g[k].values.astype(float) for k in ("open", "high", "low", "close"))
            starts = g.index.strftime("%H:%M").values
            end_m = np.array([t.hour * 60 + t.minute + 5 for t in g.index])
            ends = (g.index + pd.Timedelta(minutes=5)).strftime("%H:%M").values
            first = starts < "09:30"
            hi, lo, dopen = h[first].max(), l[first].min(), o[0]
            ema = pd.Series(c).ewm(span=20, adjust=False).mean().values
            net, n, i = 0.0, 0, 0
            while n < 2:
                ok = (ends >= "09:35") & (ends <= "14:30") & (np.arange(len(c)) >= i)
                up = ok & (c > hi) & (c > ema) & (c > dopen)
                dn = ok & (c < lo) & (c < ema) & (c < dopen)
                sig = np.flatnonzero(up | dn)
                if not len(sig) or sig[0] + 1 >= len(c):
                    break
                k = sig[0]
                s0 = o[k + 1]
                p0 = 0.0035 * s0
                sgn = 1 if up[k] else -1
                po = p0 + 0.5 * sgn * (o - s0)
                ph = p0 + 0.5 * np.where(sgn > 0, h - s0, s0 - l)
                pl = p0 + 0.5 * np.where(sgn > 0, l - s0, s0 - h)
                pc = p0 + 0.5 * sgn * (c - s0)
                e1, e2, fb, j = scale_trade(po, ph, pl, pc, end_m, k + 1, p0, True, stop_f, frac, t2_r)
                lots = int(min(3000 / (stop_f * p0 * 65), 50800 * 0.95 / (p0 * 65)))
                if lots >= 1:
                    l1 = (min(max(int(round(lots * fb)), 1), lots - 1) if lots >= 2 else lots) if fb else 0
                    b = p0 + max(0.05, 0.003 * p0)
                    for lq, ex in ((l1, e1), (lots - l1, e2)):
                        if lq < 1:
                            continue
                        q = lq * 65
                        s_ = max(ex, 0.05) - max(0.05, 0.003 * max(ex, 0.05))
                        net += q * (s_ - b) - costs.option_cost(q * b, q * s_)
                n += 1
                i = j + 1
            rows.append((day, net, n))
        res[(stop_f, "scale", frac, t2_r)] = pd.DataFrame(rows, columns=["day", "net", "trades"])
    return res


def summary(D):
    if D is None or not len(D):
        return None
    act = D[D["trades"] > 0]
    eq = D["net"].cumsum()
    return {"days": int(len(D)), "trade_days": int(len(act)), "avg_day": round(float(D["net"].mean()), 0),
            "win_days_pct": round(float((act["net"] > 0).mean() * 100), 1) if len(act) else 0,
            "days_10k_pct": round(float((D["net"] >= 10000).mean() * 100), 1),
            "worst_day": round(float(D["net"].min()), 0), "best_day": round(float(D["net"].max()), 0),
            "max_fall": round(float((eq - eq.cummax()).min()), 0), "total": round(float(D["net"].sum()), 0)}


def run(send=True, workers=None):
    from multiprocessing import get_context
    syms = [x for x in candles.symbols("5minute") if x not in candles.INDICES]
    workers = workers or max(1, min(4, os.cpu_count() or 1))
    pool = get_context("spawn").Pool(workers) if workers > 1 else None
    mp = (lambda f, it: pool.imap_unordered(f, it, chunksize=16)) if pool else map
    V = [r for rows in mp(stock_values, syms) for r in rows]
    V = pd.DataFrame(V, columns=["day", "sym", "value15"])
    V["rank"] = V.groupby("day")["value15"].rank(ascending=False, method="first")
    top = V[V["rank"] <= 100].groupby("sym")["day"].apply(list).to_dict()
    T = [r for rows in mp(stock_trades, [(s_, top.get(s_, [])) for s_ in syms if s_ in top]) for r in rows]
    if pool:
        pool.close()
    T = pd.DataFrame(T, columns=["day", "sym", "t_in", "t_out", "combo", "net", "strength"])
    rows = []
    for si, (vol_m, last, sides) in enumerate(SIG):
        for ei, (stop_f, tgt_f) in enumerate(EXI):
            D = stock_portfolio(T, si * len(EXI) + ei)
            rows.append({"vol": vol_m, "last": last, "sides": sides, "stop": stop_f, "target": tgt_f,
                         "dev": summary(D[D["day"] < CUT]), "recent": summary(D[D["day"] >= CUT])})
    frows = []
    for m in MASKS:
        if not m:
            continue
        for ei, (stop_f, tgt_f) in enumerate(EXI):
            D = stock_portfolio(T, 1000 + m * 16 + ei)
            frows.append({"factors": m, "stop": stop_f, "target": tgt_f, "dev": summary(D[D["day"] < CUT]),
                          "recent": summary(D[D["day"] >= CUT])})
    srows = []
    for ki, (stop_f, frac, t2_r) in enumerate(SCALE):
        D = stock_portfolio(T, 3000 + ki)
        srows.append({"vol": 1.5, "last": "11:30", "sides": "both", "stop": stop_f, "target": round(stop_f * t2_r, 4),
                      "scale": round(frac, 2), "t2_r": t2_r, "dev": summary(D[D["day"] < CUT]),
                      "recent": summary(D[D["day"] >= CUT])})
    O = nifty_test()
    orow = []
    for k, D in O.items():
        r = {"dev": summary(D[D["day"] < CUT]), "recent": summary(D[D["day"] >= CUT])}
        if k[1] == "scale":
            r.update(stop=k[0], target=round(k[0] * k[3], 2), last="14:30", factors=0, scale=round(k[2], 2), t2_r=k[3])
        else:
            r.update(stop=k[0], target=k[1], last=k[2], factors=k[3])
        orow.append(r)
    data = {"stocks": int(V["sym"].nunique()) if len(V) else 0, "days": int(V["day"].nunique()) if len(V) else 0,
            "first": str(V["day"].min().date()) if len(V) else None, "last": str(V["day"].max().date()) if len(V) else None}
    rec = recommend(rows + srows, frows, orow)
    json.dump({"data": data, "stocks": rows, "scale": srows, "factors": frows, "nifty": orow, "recommended": rec},
              open(DATA / "long_test.json", "w"), default=str)
    L = report(rows, orow, data, frows, rec, srows)
    if send:
        from . import telegram
        telegram.send(load_settings(), "\n".join(L[:40]), label="test result")
    return rows, orow, data


def _better(cand, cur):
    """A setting replaces the live one only if it wins BEFORE 2024 (where it was chosen) AND in the recent years,
    and its worst fall in the recent years is not much deeper."""
    if not (cand and cur and cand["dev"] and cand["recent"] and cur["recent"]):
        return False
    return (cand["dev"]["avg_day"] > cur["dev"]["avg_day"] and cand["recent"]["avg_day"] > cur["recent"]["avg_day"]
            and cand["recent"]["avg_day"] > 0 and cand["recent"]["max_fall"] >= 1.5 * min(cur["recent"]["max_fall"], -1))


def recommend(rows, frows, orow):
    cur_s = next((r for r in rows if all(r[k] == v for k, v in LIVE_STK.items())), None)
    cands = [r for r in rows + [dict(f, vol=1.5, last="11:30", sides="both") for f in frows] if r["dev"] and r["recent"]]
    best_s = max(cands, key=lambda r: r["dev"]["avg_day"]) if cands else None
    cur_s = next((r for r in rows if all(r.get(k) == v for k, v in LIVE_STK.items()) and not r.get("scale")), None)
    cur_o = next((r for r in orow if all(r.get(k) == v for k, v in LIVE_OPT.items()) and not r.get("scale")), None)
    oc = [r for r in orow if r["dev"] and r["recent"]]
    best_o = max(oc, key=lambda r: r["dev"]["avg_day"]) if oc else None
    out = {"params": {}, "changes": [], "stocks_now": cur_s, "stocks_best": best_s, "nifty_now": cur_o, "nifty_best": best_o}
    if _better(best_s, cur_s):
        out["params"].update(stk_stop=best_s["stop"], stk_target=best_s["target"], stk_vol_mult=best_s["vol"],
                             stk_last_entry=best_s["last"], stk_sides=best_s["sides"], stk_factors=best_s.get("factors", 0),
                             stk_scale=best_s.get("scale", 0))
        out["changes"].append("stocks")
    if _better(best_o, cur_o):
        out["params"].update(opt_stop=best_o["stop"], opt_target=best_o["target"], opt_last_entry=best_o["last"],
                             opt_factors=best_o.get("factors", 0), opt_scale=best_o.get("scale", 0))
        out["changes"].append("NIFTY options")
    for part, r in (("stocks", best_s if "stocks" in out["changes"] else cur_s),
                    ("nifty", best_o if "NIFTY options" in out["changes"] else cur_o)):
        if r and r["recent"] and r["recent"]["avg_day"] > 0:
            k = 10000 / r["recent"]["avg_day"]
            out[f"{part}_scale_for_10k"] = round(k, 1)
            out[f"{part}_max_scale"] = MAX_SCALE[part]
    size_up(out)
    if out["params"]:
        (DATA / "practice_params.json").write_text(json.dumps(out["params"]))
    return out


DAY_LOSS_CAP = 12500.0        # hard limit: a day's worst case (every trade stopped) stays within ~25% of ₹50,800


def size_up(out):
    """Owner 21 Nov ("₹10,000 a day is the target; you have freedom"): scale the risk per trade towards an average
    of ₹10,000 a day (from the recent years' result of the rules chosen), but never beyond what ₹50,800 allows
    (margin / premium) and never so far that a day with every trade stopped loses more than DAY_LOSS_CAP."""
    avg = {}
    for part, key in (("stocks", "stocks"), ("nifty", "nifty")):
        r = out[f"{part}_best"] if (("stocks" if part == "stocks" else "NIFTY options") in out["changes"]) else out[f"{part}_now"]
        avg[part] = r["recent"]["avg_day"] if r and r.get("recent") and r["recent"]["avg_day"] > 0 else 0.0
    total = avg["stocks"] + avg["nifty"]
    if total <= 0:
        out["size"] = "no rule earned in the recent years - risk not raised"
        return
    k = 10000.0 / total
    caps = {"stocks": min(MAX_SCALE["stocks"], DAY_LOSS_CAP / (3 * 1500)),
            "nifty": min(MAX_SCALE["nifty"], DAY_LOSS_CAP / (2 * 3000))}
    ks = {p: (round(min(max(k, 1.0), caps[p]), 2) if avg[p] > 0 else 1.0) for p in avg}
    out["params"].update(stk_risk=round(1500 * ks["stocks"]), opt_risk=round(3000 * ks["nifty"]), day_max_loss=DAY_LOSS_CAP)
    exp = avg["stocks"] * ks["stocks"] + avg["nifty"] * ks["nifty"]
    out["size"] = (f"risk per trade x{ks['stocks']} stocks (₹{1500 * ks['stocks']:,.0f}), x{ks['nifty']} NIFTY options "
                   f"(₹{3000 * ks['nifty']:,.0f}); expected average ≈ ₹{exp:,.0f} a day from the recent years "
                   f"(goal ₹10,000); day loss limit ₹{DAY_LOSS_CAP:,.0f}")


def _name(r):
    keys = [k for k in r if k not in ("dev", "recent")]
    txt = ", ".join(f"{k} {r[k]}" for k in keys if k != "factors")
    f = r.get("factors", 0)
    if f:
        names = FILTERS if "vol" in r or "sides" in r else NMASKS
        txt += " + " + ("; ".join(n for b, n in FILTERS.items() if f & b) if names is FILTERS else NMASKS.get(f, str(f)))
    return txt


def report(rows, orow, data, frows=None, rec=None, srows=None):
    rec = rec or {}
    L = [f"# Long test of the practice rules ({pd.Timestamp.now(tz='Asia/Kolkata'):%d %b %Y %H:%M} IST)", "",
         f"**Data: Kite 5-minute candles only - {data['stocks']:,} stocks, {data['days']:,} trading days, {data['first']} to "
         f"{data['last']}. Settings chosen on days before {CUT:%b %Y}; 'recent' = {CUT:%b %Y} onwards, not used for the choice.**", "",
         "| Rule | Setting | Period | Avg / day | Days in profit | Days ₹10k+ | Worst day | Worst fall |", "|---|---|---|---|---|---|---|---|"]
    for part, now, best in (("Stocks", rec.get("stocks_now"), rec.get("stocks_best")),
                            ("NIFTY options (estimate)", rec.get("nifty_now"), rec.get("nifty_best"))):
        for lab, r in (("now live", now), ("best", best)):
            if not r:
                continue
            for per in ("dev", "recent"):
                x = r[per]
                L.append(f"| {part} | {lab}: {_name(r)} | {'before 2024' if per == 'dev' else 'recent'} | ₹{x['avg_day']:+,.0f} | "
                         f"{x['win_days_pct']}% | {x['days_10k_pct']}% | ₹{x['worst_day']:,.0f} | ₹{x['max_fall']:,.0f} |")
    L += ["", "**Switched on for the practice trader:** " + (", ".join(rec["changes"]) if rec.get("changes") else
                                                            "nothing - no setting beat the live one in BOTH periods"),
          "", "**Size (goal ₹10,000 a day):** " + str(rec.get("size", "-")), ""]
    for part in ("stocks", "nifty"):
        if f"{part}_scale_for_10k" in rec:
            L.append(f"- {part}: averaging ₹10,000 a day would need {rec[part + '_scale_for_10k']}x today's risk per trade; "
                     f"₹50,800 allows at most ~{rec[part + '_max_scale']}x (and losses grow by the same factor).")
    if frows:
        L += ["", "## Extra factors on the live stock setting (stop 1%, target 2%)", "",
              "| Factors | Before 2024 avg/day | Recent avg/day | Recent worst fall |", "|---|---|---|---|"]
        for f in [x for x in frows if x["stop"] == 0.01 and x["target"] == 0.02 and x["dev"] and x["recent"]]:
            L.append(f"| {'; '.join(n for b, n in FILTERS.items() if f['factors'] & b)} | ₹{f['dev']['avg_day']:+,.0f} | "
                     f"₹{f['recent']['avg_day']:+,.0f} | ₹{f['recent']['max_fall']:,.0f} |")
    for title, R, cur in (("Scaling out - stocks (book part at 1R, stop to entry, rest to 2R/3R)", srows or [], rec.get("stocks_now")),
                          ("Scaling out - NIFTY options (estimate)", [r for r in orow if r.get("scale")], rec.get("nifty_now"))):
        if not R:
            continue
        L += ["", f"## {title}", "", "| Stop | Booked at 1R | Rest to | Before 2024 avg/day | Recent avg/day | Recent worst fall |",
              "|---|---|---|---|---|---|"]
        if cur and cur["dev"] and cur["recent"]:
            L.append(f"| {cur['stop']} | (now: all at {cur['target']}) | - | ₹{cur['dev']['avg_day']:+,.0f} | "
                     f"₹{cur['recent']['avg_day']:+,.0f} | ₹{cur['recent']['max_fall']:,.0f} |")
        for r in R:
            if r["dev"] and r["recent"]:
                L.append(f"| {r['stop']} | {r['scale']:.0%} | {r['t2_r']:.0f}R | ₹{r['dev']['avg_day']:+,.0f} | "
                         f"₹{r['recent']['avg_day']:+,.0f} | ₹{r['recent']['max_fall']:,.0f} |")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(L) + "\n")
    return L
