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
                       summary, vix_before, _compact, T_COLS, _ctx)

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
    nctx = _ctx()["nifty"]
    if d is None or not days:
        return None
    days = set(days)
    pc = ph = pl = ppc = None
    for day, g in _days(d):
        if len(g) < 10:
            continue
        if day in days and pc:
            o, h, l, c, v, end_m = _arrays(g)
            vb = SL.vix_bucket(vix_before(day))
            x = SL.ctx(o, h, l, c, v, end_m, pc, ph, pl, (pc / ppc - 1) if ppc else None)
            for si, name in enumerate(S_NAMES):
                sig = SL.first_signal(SL.STOCK[name], x)
                if sig is None or sig[0] + 1 >= len(o):
                    continue
                i, lng = sig
                px = o[i + 1]
                nd = nctx.get(day)
                al = SL.market_align(nd[0], nd[1].get(int(end_m[i])), lng) if nd else 0
                for ei, (stop_f, tgt_f) in enumerate(S_EXITS):
                    ex, j = fast_trade(o, h, l, c, end_m, i + 1, px, lng, stop_f, tgt_f)
                    slp = 0.0005 * px
                    buy, sell = ((px + slp), (ex - slp)) if lng else ((ex + slp), (px - slp))
                    qty = int(min(1500 / (px * stop_f), 50800 * 4 * 0.45 / px))
                    if qty < 1:
                        continue
                    net = qty * (sell - buy) - costs.intraday_cost(qty * buy, qty * sell)
                    out.append((day, sym, int(end_m[i]), int(end_m[j]), si * 100 + ei, float(net), float(x["strength"][i]),
                                int(lng), al, vb))
        ppc, pc = pc, float(g["close"].iloc[-1])
        ph, pl = float(g["high"].max()), float(g["low"].min())
    return _compact2(out)


T2_COLS = T_COLS + ["lng", "align", "vixb"]


def _compact2(rows):
    if not rows:
        return None
    base = _compact([r[:7] for r in rows])
    base.update(lng=np.array([r[7] for r in rows], dtype=np.int8), align=np.array([r[8] for r in rows], dtype=np.int8),
                vixb=np.array([r[9] for r in rows], dtype=np.int8))
    return base


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


MIN_TRADE = 100.0        # ₹ a trade after charges, in BOTH periods, for a strategy in one market condition
LIVE_STK, LIVE_OPT = 1000.0 / 1500.0, 2500.0 / 3000.0   # live risk caps (D178) vs the test's base size


def _portfolio(X, all_days):
    """Daily result of the chosen trades with the live limits: 3 a day, 2 at a time, one trade a stock, strongest
    first; days without a trade count as ₹0."""
    out = {}
    for day, g in X.sort_values(["day", "t_in", "strength"], ascending=[True, True, False]).groupby("day", sort=False):
        taken, syms, net = [], set(), 0.0
        for sym, t_in, t_out, nt in zip(g["sym"].values, g["t_in"].values, g["t_out"].values, g["net"].values):
            if sym in syms or len(taken) >= 3 or sum(1 for t in taken if t > t_in) >= 2:
                continue
            net += nt
            taken.append(t_out)
            syms.add(sym)
        out[day] = (net, len(taken))
    D = pd.DataFrame([(d, *out.get(d, (0.0, 0))) for d in all_days], columns=["day", "net", "trades"])
    return D


def conditions(T, all_days):
    """Every stock strategy (1% stop) split by the market at the signal: with / against NIFTY's move so far and
    yesterday's India VIX. A strategy is allowed in a condition only where it earned ≥ ₹100 a trade both before
    2024 (and clearly, t ≥ 2) and from 2024 - so nothing is rigid, but nothing trades where it lost before."""
    res = {"rules": [], "rows": [], "dev": None, "recent": None}
    if T is None or not len(T):
        return res
    one = [si * 100 + ei for si in range(len(S_NAMES)) for ei, (st, _) in enumerate(S_EXITS)
           if abs(st - OWNER_STOCK_STOP) < 1e-9]
    X = T[T["combo"].isin(one)]
    rec = X["day"] >= CUT
    rows = []
    for (cb, al, vb), g in X.groupby(["combo", "align", "vixb"]):
        r = rec.loc[g.index]
        d, n = g.loc[~r, "net"], g.loc[r, "net"]
        t = float(d.mean() / (d.std(ddof=1) / np.sqrt(len(d)))) if len(d) > 2 and d.std(ddof=1) > 0 else 0.0
        row = {"strategy": S_NAMES[cb // 100], "target": S_EXITS[cb % 100][1], "align": int(al), "vixb": int(vb),
               "combo": int(cb), "dev_n": int(len(d)), "dev_trade": round(float(d.mean()), 0) if len(d) else 0.0,
               "rec_n": int(len(n)), "rec_trade": round(float(n.mean()), 0) if len(n) else 0.0, "t": round(t, 1)}
        row["ok"] = bool(row["dev_n"] >= 100 and row["rec_n"] >= 40 and row["dev_trade"] >= MIN_TRADE
                         and row["rec_trade"] >= MIN_TRADE and t >= 2)
        rows.append(row)
    best = {}
    for r in rows:
        if r["ok"]:
            k = (r["strategy"], r["align"], r["vixb"])
            if k not in best or r["dev_trade"] > best[k]["dev_trade"]:
                best[k] = r
    res["rows"] = sorted(rows, key=lambda r: (not r["ok"], r["dev_n"] < 100 or r["rec_n"] < 40,
                                              -min(r["dev_trade"], r["rec_trade"])))
    res["rules"] = [[r["strategy"], r["target"], r["align"], r["vixb"]] for r in best.values()]
    if best:
        keys = {(r["combo"], r["align"], r["vixb"]) for r in best.values()}
        m = np.array([(c, a, v) in keys for c, a, v in zip(X["combo"].values, X["align"].values, X["vixb"].values)])
        D = _portfolio(X[m], all_days)
        D["net"] *= LIVE_STK
        res["dev"], res["recent"] = summary(D[D["day"] < CUT]), summary(D[D["day"] >= CUT])
    return res


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
        T = pd.DataFrame({k: np.concatenate([p[k] for p in parts]) for k in T2_COLS})
        T["day"] = pd.to_datetime(T["day"].astype(np.int64) - 719163, unit="D")
    else:
        T = pd.DataFrame(columns=T2_COLS)
    del parts
    srows = []
    for si, name in enumerate(S_NAMES):
        for ei, (stop_f, tgt_f) in enumerate(S_EXITS):
            srows.append(_row(stock_portfolio(T, si * 100 + ei), strategy=name, stop=stop_f, target=tgt_f))
    nrows = [_row(D, strategy=k[0], stop=k[1], target=k[2], vix=bool(k[3])) for k, D in nifty_search().items()]
    data = {"stocks": int(V["sym"].nunique()) if len(V) else 0, "days": int(V["day"].nunique()) if len(V) else 0,
            "first": str(V["day"].min().date()) if len(V) else None, "last": str(V["day"].max().date()) if len(V) else None}
    all_days = pd.DatetimeIndex(sorted(V["day"].unique())) if len(V) else pd.DatetimeIndex([])
    cond = conditions(T, all_days)
    del T
    rec = choose(srows, nrows, cond)
    L = report(srows, nrows, data, rec, cond["rows"])
    strip = lambda R: [{k: v for k, v in r.items() if k != "_daily"} for r in R]
    json.dump({"data": data, "stocks": strip(srows), "nifty": strip(nrows), "chosen": {k: v for k, v in rec.items()
               if not k.startswith("_")}}, open(DATA / "strategy_search.json", "w"), default=str)
    if send:
        from . import telegram
        telegram.send(load_settings(), "\n".join(L[:45]), label="test result")
    return srows, nrows, rec


def choose(srows, nrows, cond=None):
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
    cond = cond or {"rules": []}
    out["conditions"] = {k: cond.get(k) for k in ("rules", "dev", "recent")}
    if cond["rules"]:                                  # D179: every strategy, in the conditions where it earned
        p.update(stk_max_trades=3, stk_strategy="rules", stk_rules=cond["rules"], stk_stop=OWNER_STOCK_STOP)
    good_n = {}
    for r in sorted(pn, key=lambda r: -r["dev"]["avg_day"]):
        good_n.setdefault(r["strategy"], r)
    if good_n:
        p["opt_strategies"] = [[r["strategy"], r["stop"], r["target"], 8 if r["vix"] else 0] for r in good_n.values()]
    out["live_expected"] = round((cond["recent"]["avg_day"] if cond.get("recent") else 0.0)
                                 + (bn["recent"]["avg_day"] * LIVE_OPT if bn else 0.0))
    p["opt_max_trades"] = 2 if bn else 0
    if bn:
        p.update(opt_strategy=bn["strategy"], opt_stop=bn["stop"], opt_target=bn["target"],
                 opt_factors=8 if bn["vix"] else 0, opt_risk=round(3000 * kn))
    p["day_max_loss"] = DAY_LOSS_CAP
    (DATA / "practice_params.json").write_text(json.dumps(p))
    return out


def report(srows, nrows, data, rec, c_rows=None):
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
    c = rec.get("conditions") or {}
    L += ["## Every stock strategy by market condition (1% stop) - D179", "",
          f"Allowed where it earned ≥ ₹{MIN_TRADE:,.0f} a trade before 2024 (clearly: t ≥ 2, ≥ 100 trades) AND from 2024 "
          "(≥ 40 trades). Condition = trade with / against NIFTY's move so far + yesterday's India VIX.", "",
          "| Strategy | Target | Market | VIX | Trades before 2024 | ₹/trade before | Trades 2024+ | ₹/trade 2024+ | t | Allowed |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for r in (c_rows or [])[:25]:
        L.append(f"| {r['strategy']} | {r['target']} | {SL.ALIGN[r['align']]} | {SL.VIXB[r['vixb']]} | {r['dev_n']:,} | "
                 f"₹{r['dev_trade']:+,.0f} | {r['rec_n']:,} | ₹{r['rec_trade']:+,.0f} | {r['t']} | {'✅' if r['ok'] else '❌'} |")
    L.append("")
    if c.get("recent"):
        L += [f"Allowed together, at the live size (₹1,000 risk a trade): ₹{c['dev']['avg_day']:+,.0f} a day before 2024, "
              f"₹{c['recent']['avg_day']:+,.0f} a day from 2024 ({c['recent']['win_days_pct']}% of trading days in profit, "
              f"worst day ₹{c['recent']['worst_day']:,.0f}).", ""]
    else:
        L += ["No stock strategy earned in any market condition in both periods.", ""]
    s, n = rec.get("stock"), rec.get("nifty")
    L += ["## Chosen for the practice trader", "",
          f"- Stocks: {s['strategy'] + ' (stop ' + str(s['stop']) + ', target ' + str(s['target']) + ')' if s else 'none passed - stock trades stay paused'}",
          f"- NIFTY options (best): {n['strategy'] + ' (stop ' + str(n['stop']) + ', target ' + str(n['target']) + (', VIX < 20' if n['vix'] else '') + ')' if n else 'none passed - option trades paused'}"]
    os_ = rec.get("params", {}).get("opt_strategies") or []
    if os_:
        L.append("- NIFTY strategies that may fire (first signal takes the slot, max 2 a day): "
                 + ", ".join(f"{x[0]} (stop {x[1]}, target {x[2]}{', VIX < 20' if x[3] else ''})" for x in os_))
    if rec.get("conditions", {}).get("rules"):
        L.append(f"- Stocks, by market condition: {len(rec['conditions']['rules'])} strategy/condition pairs allowed")
    if rec.get("live_expected") is not None:
        L.append(f"- Expected at the live size (₹1,000 a stock trade, ₹2,500 an option trade, ₹3,000 day loss limit): "
                 f"≈ ₹{rec['live_expected']:+,} a day from 2024 (goal ₹10,000)")
    if "expected_day" in rec and False:            # D178: the live caps replace this older sizing line
        L += [f"- Together, recent years: ₹{rec['combined_recent']['avg_day']:+,.0f} a day at today's size; "
              f"₹10,000 a day would need {rec['scale_needed']}x the size; ₹50,800 allows "
              f"{rec['scales']['stocks']}x stocks / {rec['scales']['nifty']}x options -> expected ≈ ₹{rec['expected_day']:,} a day "
              f"(goal ₹10,000), day loss limit ₹{DAY_LOSS_CAP:,.0f}."]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(L) + "\n")
    return L
