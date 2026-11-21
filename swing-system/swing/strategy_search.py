"""STRATEGY SEARCH (owner 21 Nov: "start the strategy search; the ultimate goal is ₹10,000 profit every day").

Every strategy in strategies_lib.py, on every day of Kite 5-minute history (2015 onwards):
  - stocks: the day's 100 most-traded stocks (value 9:15-9:30), the first signal of each stock each day, entry at
    the next candle's open (+0.05%), stop / target grid (0.5/1/1.5% x 1/2/3%), stop to entry after +1 stop
    distance, out by 3:15 pm, Zerodha intraday charges, ~₹1,500 risk a trade, 3 a day and 2 at a time;
  - NIFTY weekly options: ESTIMATE (Kite keeps no expired option candles): option = 0.35% of NIFTY, moves half as
    much as NIFTY, no time decay; up to 2 trades a day; stop 20/30% x target 60/100% of the premium, with and
    without "India VIX below 20"; ~₹3,000 risk a trade.
Fair check: chosen on days before 2024, shown on 2024 onwards. A strategy counts only if it earns in BOTH.
Then: the best stock + best NIFTY strategy together, the trade size needed for ₹10,000 a day, and what ₹50,800
allows. Winners are switched on for the practice trader (data/practice_params.json). Data: Kite candles only."""
import itertools
import json
import os

import numpy as np
import pandas as pd

from . import candles, costs, strategies_lib as SL
from .config import DATA, RESULTS, get_logger, load_settings
from .longtest import (CUT, MAX_SCALE, DAY_LOSS_CAP, _days, _simulate, fast_trade, stock_portfolio, stock_values,
                       summary, vix_before, _compact, T_COLS)

log = get_logger()
REPORT = RESULTS / "strategy_search.md"
S_EXITS = list(itertools.product([0.005, 0.01, 0.015], [0.01, 0.02, 0.03]))
N_EXITS = list(itertools.product([0.2, 0.3], [0.6, 1.0], [0, 8]))
S_NAMES = list(SL.STOCK)
N_NAMES = list(SL.NIFTY)


def _arrays(g):
    o, h, l, c, v = (g[k].values.astype(float) for k in ("open", "high", "low", "close", "volume"))
    end_m = np.array([t.hour * 60 + t.minute + 5 for t in g.index])
    return o, h, l, c, v, end_m


def prev_values(sym):
    """Each day -> the stock's traded value on the PREVIOUS trading day (known at 9:15, so a signal on the first
    candle never depends on later trading; live uses the same ranking: Engine -> market.universe_open)."""
    d = candles.load(sym, "5minute", adjusted=False)
    if d is None or len(d) < 50:
        return []
    v = (d["close"] * d["volume"]).groupby(d.index.normalize()).sum()
    return [(day, sym, float(val)) for day, val in zip(v.index[1:], v.values[:-1])]


def stock_trades(args):
    """One stock: for each day it was in the top 100, the first signal of every strategy and its result in rupees
    for every stop/target pair."""
    sym, days = args
    d = candles.load(sym, "5minute")
    out = []
    if d is None or not days:
        return None
    days = set(days)
    pc = ph = pl = ppc = None
    for day, g in _days(d):
        if len(g) < 10:
            continue
        if day in days and pc:
            o, h, l, c, v, end_m = _arrays(g)
            x = SL.ctx(o, h, l, c, v, end_m, pc, ph, pl, (pc / ppc - 1) if ppc else None)
            for si, name in enumerate(S_NAMES):
                sig = SL.first_signal(SL.STOCK[name], x)
                if sig is None or sig[0] + 1 >= len(o):
                    continue
                i, lng = sig
                px = o[i + 1]
                for ei, (stop_f, tgt_f) in enumerate(S_EXITS):
                    ex, j = fast_trade(o, h, l, c, end_m, i + 1, px, lng, stop_f, tgt_f)
                    slp = 0.0005 * px
                    buy, sell = ((px + slp), (ex - slp)) if lng else ((ex + slp), (px - slp))
                    qty = int(min(1500 / (px * stop_f), 50800 * 4 * 0.45 / px))
                    if qty < 1:
                        continue
                    net = qty * (sell - buy) - costs.intraday_cost(qty * buy, qty * sell)
                    out.append((day, sym, int(end_m[i]), int(end_m[j]), si * 100 + ei, float(net), float(x["strength"][i])))
        ppc, pc = pc, float(g["close"].iloc[-1])
        ph, pl = float(g["high"].max()), float(g["low"].min())
    return _compact(out)


def nifty_search():
    """{(name, stop, target, vix_mask): daily DataFrame} for every NIFTY strategy (option ESTIMATE)."""
    d = candles.load("NIFTY50", "5minute")
    res = {}
    if d is None or len(d) < 1000:
        return res
    days, prev = [], None
    for day, g in _days(d):
        if len(g) >= 20 and prev:
            days.append((day, g, prev, vix_before(day)))
        if len(g):
            prev = (float(g["close"].iloc[-1]), float(g["high"].max()), float(g["low"].min()))
    for name in N_NAMES:
        fn = SL.NIFTY[name]
        for stop_f, tgt_f, mask in N_EXITS:
            rows = []
            for day, g, (pc, ph, pl), vx in days:
                if mask & 8 and (vx is None or vx >= 20):
                    rows.append((day, 0.0, 0))
                    continue
                o, h, l, c, v, end_m = _arrays(g)
                x = SL.ctx(o, h, l, c, np.ones(len(c)), end_m, pc, ph, pl)
                lg, sh = fn(x)
                ends = (g.index + pd.Timedelta(minutes=5)).strftime("%H:%M").values
                net, n, start = 0.0, 0, 0
                while n < 2:
                    hit = np.flatnonzero((lg | sh)[start:])
                    if not len(hit) or start + hit[0] + 1 >= len(c):
                        break
                    k = start + int(hit[0])
                    s0 = o[k + 1]
                    p0 = 0.0035 * s0
                    sgn = 1 if lg[k] else -1
                    po = p0 + 0.5 * sgn * (o - s0)
                    ph_ = p0 + 0.5 * np.where(sgn > 0, h - s0, s0 - l)
                    pl_ = p0 + 0.5 * np.where(sgn > 0, l - s0, s0 - h)
                    pc_ = p0 + 0.5 * sgn * (c - s0)
                    ex, why, j = _simulate(po, ph_, pl_, pc_, ends, k + 1, p0, "LONG", stop_f, tgt_f)
                    ex = max(ex, 0.05)
                    lots = int(min(3000 / (stop_f * p0 * 65), 50800 * 0.95 / (p0 * 65)))
                    if lots >= 1:
                        q = lots * 65
                        b, s_ = p0 + max(0.05, 0.003 * p0), ex - max(0.05, 0.003 * ex)
                        net += q * (s_ - b) - costs.option_cost(q * b, q * s_)
                    n += 1
                    start = j + 1
                rows.append((day, net, n))
            res[(name, stop_f, tgt_f, mask)] = pd.DataFrame(rows, columns=["day", "net", "trades"])
    return res


def _row(D, **k):
    return dict(k, dev=summary(D[D["day"] < CUT]), recent=summary(D[D["day"] >= CUT]), _daily=D)


OWNER_STOCK_STOP = 0.01   # owner 21 Nov: "sl will be 1%" -> only 1%-stop stock settings can be switched on
MIN_EDGE = 100.0          # ₹ a day in BOTH periods: +₹11 a day is break-even noise, not worth real money


def _passes(r):
    return r["dev"] and r["recent"] and r["dev"]["avg_day"] > 0 and r["recent"]["avg_day"] > 0


def _usable(r, stock):
    return (_passes(r) and r["dev"]["avg_day"] >= MIN_EDGE and r["recent"]["avg_day"] >= MIN_EDGE
            and (not stock or abs(r["stop"] - OWNER_STOCK_STOP) < 1e-9))


def run(send=True, workers=None):
    from multiprocessing import get_context
    syms = [x for x in candles.symbols("5minute") if x not in candles.INDICES]
    workers = workers or max(1, min(4, os.cpu_count() or 1))
    pool = get_context("spawn").Pool(workers) if workers > 1 else None
    mp = (lambda f, it: pool.imap_unordered(f, it, chunksize=16)) if pool else map
    V = pd.DataFrame([r for rows in mp(prev_values, syms) for r in rows], columns=["day", "sym", "value_prev"])
    V["rank"] = V.groupby("day")["value_prev"].rank(ascending=False, method="first")
    top = V[V["rank"] <= 100].groupby("sym")["day"].apply(list).to_dict()
    parts = [p for p in mp(stock_trades, [(s, top.get(s, [])) for s in syms if s in top]) if p]
    if pool:
        pool.close()
    if parts:
        T = pd.DataFrame({k: np.concatenate([p[k] for p in parts]) for k in T_COLS})
        T["day"] = pd.to_datetime(T["day"].astype(np.int64) - 719163, unit="D")
    else:
        T = pd.DataFrame(columns=T_COLS)
    del parts
    srows = []
    for si, name in enumerate(S_NAMES):
        for ei, (stop_f, tgt_f) in enumerate(S_EXITS):
            srows.append(_row(stock_portfolio(T, si * 100 + ei), strategy=name, stop=stop_f, target=tgt_f))
    nrows = [_row(D, strategy=k[0], stop=k[1], target=k[2], vix=bool(k[3])) for k, D in nifty_search().items()]
    data = {"stocks": int(V["sym"].nunique()) if len(V) else 0, "days": int(V["day"].nunique()) if len(V) else 0,
            "first": str(V["day"].min().date()) if len(V) else None, "last": str(V["day"].max().date()) if len(V) else None}
    rec = choose(srows, nrows)
    L = report(srows, nrows, data, rec)
    strip = lambda R: [{k: v for k, v in r.items() if k != "_daily"} for r in R]
    json.dump({"data": data, "stocks": strip(srows), "nifty": strip(nrows), "chosen": {k: v for k, v in rec.items()
               if not k.startswith("_")}}, open(DATA / "strategy_search.json", "w"), default=str)
    if send:
        from . import telegram
        telegram.send(load_settings(), "\n".join(L[:45]), label="test result")
    return srows, nrows, rec


def choose(srows, nrows):
    """Best stock and best NIFTY strategy (chosen before 2024, must also earn from 2024), the size needed for
    ₹10,000 a day, and the practice settings."""
    ps = [r for r in srows if _usable(r, True)]
    pn = [r for r in nrows if _usable(r, False)]
    bs = max(ps, key=lambda r: r["dev"]["avg_day"]) if ps else None
    bn = max(pn, key=lambda r: r["dev"]["avg_day"]) if pn else None
    out = {"stock": bs and {k: v for k, v in bs.items() if k != "_daily"},
           "nifty": bn and {k: v for k, v in bn.items() if k != "_daily"}, "params": {}}
    parts = [r["_daily"].set_index("day")["net"] for r in (bs, bn) if r]
    if parts:
        both = pd.concat(parts, axis=1).fillna(0).sum(axis=1).rename("net").reset_index()
        both["trades"] = 1
        rec_avg = summary(both[both["day"] >= CUT])
        out["combined_recent"] = rec_avg
        avg_s = bs["recent"]["avg_day"] if bs else 0.0
        avg_n = bn["recent"]["avg_day"] if bn else 0.0
        k = 10000.0 / max(avg_s + avg_n, 1e-9)
        cap_s = min(MAX_SCALE["stocks"], DAY_LOSS_CAP / (3 * 1500))
        cap_n = min(MAX_SCALE["nifty"], DAY_LOSS_CAP / (2 * 3000))
        ks, kn = (round(min(max(k, 1.0), cap_s), 2) if bs else 1.0), (round(min(max(k, 1.0), cap_n), 2) if bn else 1.0)
        out["scale_needed"] = round(k, 1)
        out["expected_day"] = round(avg_s * ks + avg_n * kn)
        out["scales"] = {"stocks": ks, "nifty": kn}
    p = out["params"]
    p["stk_max_trades"] = 3 if bs else 0
    if bs:
        p.update(stk_strategy=bs["strategy"], stk_stop=bs["stop"], stk_target=bs["target"], stk_risk=round(1500 * ks))
    p["opt_max_trades"] = 2 if bn else 0
    if bn:
        p.update(opt_strategy=bn["strategy"], opt_stop=bn["stop"], opt_target=bn["target"],
                 opt_factors=8 if bn["vix"] else 0, opt_risk=round(3000 * kn))
    p["day_max_loss"] = DAY_LOSS_CAP
    (DATA / "practice_params.json").write_text(json.dumps(p))
    return out


def report(srows, nrows, data, rec):
    L = [f"# Strategy search ({pd.Timestamp.now(tz='Asia/Kolkata'):%d %b %Y %H:%M} IST) - goal ₹10,000 a day", "",
         f"**Data: Kite 5-minute candles only - {data['stocks']:,} stocks, {data['days']:,} days, {data['first']} to "
         f"{data['last']}. NIFTY options are an ESTIMATE (no expired option candles on Kite). Chosen before 2024, "
         "checked on 2024 onwards.**", ""]
    for title, R, keys in (("Stocks", srows, ("strategy", "stop", "target")),
                           ("NIFTY options (estimate)", nrows, ("strategy", "stop", "target", "vix"))):
        best = {}
        for r in R:
            if r["dev"] and r["recent"]:
                b = best.get(r["strategy"])
                if b is None or r["dev"]["avg_day"] > b["dev"]["avg_day"]:
                    best[r["strategy"]] = r
        L += [f"## {title} - best setting of each strategy", "",
              "| Strategy | Setting | Before 2024 avg/day | Recent avg/day | Recent days in profit | Recent worst day | Passes |",
              "|---|---|---|---|---|---|---|"]
        for r in sorted(best.values(), key=lambda r: -r["recent"]["avg_day"]):
            setting = ", ".join(f"{k} {r[k]}" for k in keys[1:])
            L.append(f"| {r['strategy']} | {setting} | ₹{r['dev']['avg_day']:+,.0f} | ₹{r['recent']['avg_day']:+,.0f} | "
                     f"{r['recent']['win_days_pct']}% | ₹{r['recent']['worst_day']:,.0f} | {'✅' if _passes(r) else '❌'} |")
        L.append("")
    one = {}
    for r in srows:
        if r["dev"] and r["recent"] and abs(r["stop"] - OWNER_STOCK_STOP) < 1e-9:
            b = one.get(r["strategy"])
            if b is None or r["dev"]["avg_day"] > b["dev"]["avg_day"]:
                one[r["strategy"]] = r
    L += ["## Stocks with the owner's 1% stop-loss (only these can be switched on)", "",
          f"Switched on only if it earns at least ₹{MIN_EDGE:,.0f} a day both before 2024 and from 2024.", "",
          "| Strategy | Target | Before 2024 avg/day | Recent avg/day | Recent days in profit | Recent worst day | Usable |",
          "|---|---|---|---|---|---|---|"]
    for r in sorted(one.values(), key=lambda r: -r["recent"]["avg_day"]):
        L.append(f"| {r['strategy']} | {r['target']} | ₹{r['dev']['avg_day']:+,.0f} | ₹{r['recent']['avg_day']:+,.0f} | "
                 f"{r['recent']['win_days_pct']}% | ₹{r['recent']['worst_day']:,.0f} | {'✅' if _usable(r, True) else '❌'} |")
    L.append("")
    s, n = rec.get("stock"), rec.get("nifty")
    L += ["## Chosen for the practice trader", "",
          f"- Stocks: {s['strategy'] + ' (stop ' + str(s['stop']) + ', target ' + str(s['target']) + ')' if s else 'none passed - stock trades stay paused'}",
          f"- NIFTY options: {n['strategy'] + ' (stop ' + str(n['stop']) + ', target ' + str(n['target']) + (', VIX < 20' if n['vix'] else '') + ')' if n else 'none passed - option trades paused'}"]
    if "expected_day" in rec:
        L += [f"- Together, recent years: ₹{rec['combined_recent']['avg_day']:+,.0f} a day at today's size; "
              f"₹10,000 a day would need {rec['scale_needed']}x the size; ₹50,800 allows "
              f"{rec['scales']['stocks']}x stocks / {rec['scales']['nifty']}x options -> expected ≈ ₹{rec['expected_day']:,} a day "
              f"(goal ₹10,000), day loss limit ₹{DAY_LOSS_CAP:,.0f}."]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(L) + "\n")
    return L
