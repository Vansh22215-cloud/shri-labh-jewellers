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
LIVE_STK = dict(stop=0.01, target=0.02, vol=1.5, last="11:30", sides="both")
LIVE_OPT = dict(stop=0.3, target=0.6, last="14:30")


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
    prev_close = None
    for day, g in _days(d):
        last_close = float(g["close"].iloc[-1]) if len(g) else prev_close
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
        for si, (vol_m, last, sides) in enumerate(SIG):
            ok = (end_m >= 575) & (end_m <= _hm(last)) & (strength >= vol_m)
            up = ok & (c > hi) & (c > vwap)
            dn = ok & (c < lo) & (c < vwap) if sides == "both" else np.zeros(len(c), bool)
            sig = np.flatnonzero(up | dn)
            if not len(sig) or sig[0] + 1 >= len(o):
                continue
            i = sig[0]
            lng = bool(up[i])
            px = o[i + 1]
            for ei, (stop_f, tgt_f) in enumerate(EXI):
                ex, j = fast_trade(o, h, l, c, end_m, i + 1, px, lng, stop_f, tgt_f)
                slp = 0.0005 * px
                buy, sell = ((px + slp), (ex - slp)) if lng else ((ex + slp), (px - slp))
                qty = int(min(1500 / (px * stop_f), 50800 * 5 * 0.45 / px))
                if qty < 1:
                    continue
                net = qty * (sell - buy) - costs.intraday_cost(qty * buy, qty * sell)
                out.append((day, sym, int(end_m[i]), int(end_m[j]), si * len(EXI) + ei, float(net), float(strength[i])))
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


def nifty_test():
    """The NIFTY option rule as an estimate on NIFTY 50 5-minute candles. -> {combo: daily DataFrame}."""
    d = candles.load("NIFTY50", "5minute")
    res = {}
    if d is None or len(d) < 1000:
        return res
    days = list(_days(d))
    for stop_f, tgt_f, last in itertools.product(OPT_GRID["stop"], OPT_GRID["target"], OPT_GRID["last"]):
        rows = []
        for day, g in days:
            if len(g) < 20:
                continue
            o, h, l, c = (g[k].values.astype(float) for k in ("open", "high", "low", "close"))
            starts = g.index.strftime("%H:%M").values
            ends = (g.index + pd.Timedelta(minutes=5)).strftime("%H:%M").values
            first = starts < "09:30"
            hi, lo, dopen = h[first].max(), l[first].min(), o[0]
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
                # option price path: p0 + 0.5 * (index move in the option's favour)
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
        res[(stop_f, tgt_f, last)] = pd.DataFrame(rows, columns=["day", "net", "trades"])
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
    O = nifty_test()
    orow = [{"stop": k[0], "target": k[1], "last": k[2], "dev": summary(D[D["day"] < CUT]),
             "recent": summary(D[D["day"] >= CUT])} for k, D in O.items()]
    data = {"stocks": int(V["sym"].nunique()) if len(V) else 0, "days": int(V["day"].nunique()) if len(V) else 0,
            "first": str(V["day"].min().date()) if len(V) else None, "last": str(V["day"].max().date()) if len(V) else None}
    json.dump({"data": data, "stocks": rows, "nifty": orow}, open(DATA / "long_test.json", "w"), default=str)
    L = report(rows, orow, data)
    if send:
        from . import telegram
        telegram.send(load_settings(), "\n".join(L[:40]), label="test result")
    return rows, orow, data


def _best(rows, live):
    ok = [r for r in rows if r["dev"] and r["recent"]]
    best = max(ok, key=lambda r: r["dev"]["avg_day"]) if ok else None
    cur = next((r for r in ok if all(r[k] == v for k, v in live.items())), None)
    return best, cur


def report(rows, orow, data):
    L = [f"# Long test of the practice rules ({pd.Timestamp.now(tz='Asia/Kolkata'):%d %b %Y %H:%M} IST)", "",
         f"**Data: Kite 5-minute candles only - {data['stocks']:,} stocks, {data['days']:,} trading days, {data['first']} to "
         f"{data['last']}. Settings chosen on days before {CUT:%b %Y}; 'recent' = {CUT:%b %Y} onwards, not used for the choice.**", ""]
    for title, R, live in (("Stocks (real Kite candles)", rows, LIVE_STK), ("NIFTY options (ESTIMATE - no expired option candles on Kite)", orow, LIVE_OPT)):
        best, cur = _best(R, live)
        L += [f"## {title}", "", "| Setting | Period | Avg / day | Days in profit | Days ₹10k+ | Worst day | Worst fall | Total |",
              "|---|---|---|---|---|---|---|---|"]
        for lab, r in (("now live", cur), ("best before 2024", best)):
            if not r:
                continue
            name = ", ".join(f"{k} {v}" for k, v in r.items() if k not in ("dev", "recent"))
            for per in ("dev", "recent"):
                s = r[per]
                L.append(f"| {lab}: {name} | {'before 2024' if per == 'dev' else 'recent'} | ₹{s['avg_day']:+,.0f} | "
                         f"{s['win_days_pct']}% | {s['days_10k_pct']}% | ₹{s['worst_day']:,.0f} | ₹{s['max_fall']:,.0f} | ₹{s['total']:+,.0f} |")
        L.append("")
    L.append("A setting is worth switching to only if it is also better in the 'recent' rows.")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(L) + "\n")
    return L
