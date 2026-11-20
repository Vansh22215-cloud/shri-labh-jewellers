"""The tester: one strategy on Kite candles of every NSE stock (owner 20 Nov: "all tests on Kite data, not Yahoo").

Rules of the simulation (the same for every strategy, so results are comparable):
  - entry: the signal candle's close (or the next candle's open, if the strategy says so);
  - stop-loss: 1% below the entry by default (settings.yaml stop_loss_pct); if a candle opens below the stop the
    trade is sold at that open (a gap is never hidden);
  - target: the last target in targets_r; if the stop and the target are both inside one candle, the STOP is
    assumed first (the cautious answer);
  - the strategy's own exit rule at a candle's close; max_bars; intraday trades are sold by 3:20 pm;
  - one trade at a time per stock;
  - costs: Zerodha's real charges (delivery or intraday) + 0.15% slippage each side, on the quantity the
    owner's settings give (capital, 1% risk, 25% cap);
  - every trade keeps its context at entry (time, weekday, trend, market, VIX, gap, volume, volatility) for the
    Learner, and its best/worst move while open.
Results: results/tests/<strategy>.md (public, no prices) + the trade list in data/tests/ (private cache).
Data: Kite candles only - every report starts with the data line (which interval, stocks, dates, stocks missing)."""
import json
import os
from datetime import timedelta

import numpy as np
import pandas as pd

from . import candles, costs
from .config import DATA, RESULTS, get_logger, load_settings

log = get_logger()
TESTS = DATA / "tests"
OUT = RESULTS / "tests"
HOLDOUT_YEARS = 2            # the most recent 2 years are reported separately ("recent", the fair check)


# ----------------------------------------------------------------------------- context (known at entry)
def daily_context(sym, nifty_d=None, vix_d=None):
    """Per day: values KNOWN at that day's close (stock trend, volatility, turnover, market, VIX)."""
    d = candles.load(sym, "day")
    if d is None or len(d) < 30:
        return None
    c = d["close"]
    tr = pd.concat([d["high"] - d["low"], (d["high"] - c.shift()).abs(), (d["low"] - c.shift()).abs()], axis=1).max(axis=1)
    x = pd.DataFrame(index=d.index)
    x["above_50d"] = c > c.rolling(50).mean()
    x["above_200d"] = c > c.rolling(200).mean()
    x["atr_pct"] = tr.rolling(14).mean() / c * 100
    x["turnover_cr"] = (c * d["volume"]).rolling(20).mean() / 1e7
    x["day_change_pct"] = c.pct_change() * 100
    x["close"] = c
    x["open"] = d["open"]
    if nifty_d is not None and len(nifty_d):
        n = nifty_d["close"]
        x["nifty_above_50d"] = (n > n.rolling(50).mean()).reindex(x.index)
        x["nifty_change_pct"] = (n.pct_change() * 100).reindex(x.index)
    if vix_d is not None and len(vix_d):
        x["vix"] = vix_d["close"].reindex(x.index)
    return x


def _bucket(v, edges, labels):
    if v is None or v != v:
        return "unknown"
    for e, lab in zip(edges, labels):
        if v < e:
            return lab
    return labels[-1]


def context_at(t, interval, dctx, d):
    """Context of a trade entered at candle time t. Intraday: yesterday's daily values (today's are not known
    yet) + today's gap; day candles: that day's values (known at its close)."""
    out = {"weekday": t.strftime("%a"), "month": t.strftime("%b"), "year": t.year}
    if interval != "day":
        m = t.hour * 60 + t.minute
        out["time_of_day"] = _bucket(m, [600, 660, 720, 780, 840, 930],
                                     ["9:15-10", "10-11", "11-12", "12-13", "13-14", "14-15:30", "14-15:30"])
    i = d.index.get_loc(t) if t in d.index else None
    if i is not None and i >= 20:
        v = d["volume"].iloc[i - 20:i].mean()
        out["rel_volume"] = _bucket(d["volume"].iloc[i] / v if v else None, [0.7, 1.5, 3], ["low", "normal", "high", "very high"])
    if dctx is not None and len(dctx):
        day = t.normalize()
        known = dctx[dctx.index < day] if interval != "day" else dctx[dctx.index <= day]
        if len(known):
            r = known.iloc[-1]
            out["stock_trend"] = ("above 50 & 200-day avg" if r.get("above_50d") and r.get("above_200d") else
                                  "below 50 & 200-day avg" if not r.get("above_50d") and not r.get("above_200d") else "mixed")
            out["volatility"] = _bucket(r.get("atr_pct"), [2, 3.5, 5], ["calm (<2%)", "normal (2-3.5%)", "wild (3.5-5%)", "very wild (>5%)"])
            out["turnover"] = _bucket(r.get("turnover_cr"), [1, 10, 100], ["< ₹1 cr", "₹1-10 cr", "₹10-100 cr", "> ₹100 cr"])
            if "nifty_above_50d" in r:
                out["market"] = "NIFTY above 50-day avg" if r["nifty_above_50d"] else "NIFTY below 50-day avg"
            if "vix" in r:
                out["vix"] = _bucket(r["vix"], [13, 18, 25], ["< 13", "13-18", "18-25", "> 25"])
        if interval != "day" and day in dctx.index and len(known):
            prev = known["close"].iloc[-1]
            gap = (dctx.at[day, "open"] / prev - 1) * 100 if prev else None
            out["gap"] = _bucket(gap, [-1, -0.2, 0.2, 1], ["gap down > 1%", "small gap down", "flat open", "small gap up", "gap up > 1%"])
    return out


# ----------------------------------------------------------------------------- one stock
def simulate(sym, d, strat, settings, dctx=None):
    """All trades of one strategy on one stock's candles -> list of dicts."""
    if d is None or len(d) < 3:
        return []
    ent = strat.entries(d).fillna(False).astype(bool).values
    ex = strat.exits(d).fillna(False).astype(bool).values
    o, h, l, c = (d[k].values.astype(float) for k in ("open", "high", "low", "close"))
    idx = d.index
    intraday = strat.kind == "intraday"
    cap = float(settings.get("capital") or 0) or 51000.0
    lim = settings.get("risk_limits") or {}
    trades, i, n = [], 0, len(d)
    while i < n - 1:
        if not ent[i] or (intraday and idx[i].strftime("%H:%M") > strat.last_entry_time):
            i += 1
            continue
        if strat.entry_at == "next_open":
            j0, px = i + 1, o[i + 1]
            if intraday and idx[j0].normalize() != idx[i].normalize():
                i += 1
                continue
        else:
            j0, px = i + 1, c[i]
        if not px > 0:
            i += 1
            continue
        stop, tg = strat.levels(px, settings)
        tgt = tg[-1] if tg else None
        hi, lo, why, exit_px, j = px, px, None, None, j0
        t1 = False
        while j < n:
            if intraday and (idx[j].normalize() != idx[i].normalize() or idx[j].strftime("%H:%M") >= strat.square_off_time):
                if idx[j].normalize() != idx[i].normalize():
                    j -= 1
                    why, exit_px = "square-off 3:20 pm", c[j]
                else:
                    why, exit_px = "square-off 3:20 pm", o[j]
                break
            if strat.entry_at == "next_open" and j == j0:
                pass                                       # the entry candle itself can still hit the stop/target
            if l[j] <= stop:
                why, exit_px = "stop-loss", min(o[j], stop)
                lo = min(lo, l[j])
                break
            if tgt is not None and h[j] >= tgt:
                why, exit_px = "target", max(o[j], tgt)
                hi = max(hi, h[j])
                break
            hi, lo = max(hi, h[j]), min(lo, l[j])
            if tg and h[j] >= tg[0]:
                t1 = True
            if ex[j]:
                why, exit_px = "exit rule", c[j]
                break
            if strat.max_bars and j - i >= strat.max_bars:
                why, exit_px = f"time ({strat.max_bars} candles)", c[j]
                break
            j += 1
        if why is None:                                    # still open at the end of the data: not counted
            break
        value = min(cap * float(lim.get("risk_per_trade_pct", 1)) / 100 / max(px - stop, 1e-9) * px,
                    cap * float(lim.get("max_order_pct", 25)) / 100)
        qty = int(value // px)
        cost = costs.round_trip_pct(max(qty, 1) * px, "intraday" if intraday else "delivery")
        gross = exit_px / px - 1
        tr = {"sym": sym, "signal": idx[i], "entry_time": idx[i] if strat.entry_at == "close" else idx[j0],
              "entry": round(px, 2), "stop": round(stop, 2), "target": tgt, "exit_time": idx[j], "exit": round(exit_px, 2),
              "why": why, "bars": int(j - i), "gross_pct": round(gross * 100, 3), "net_pct": round((gross - cost) * 100, 3),
              "cost_pct": round(cost * 100, 3), "best_pct": round((hi / px - 1) * 100, 3),
              "worst_pct": round((lo / px - 1) * 100, 3), "t1_hit": t1, "qty": qty}
        tr.update(context_at(idx[i], strat.interval, dctx, d))
        trades.append(tr)
        i = j + 1
    return trades


def _one(args):
    sym, name, start, end = args
    from .strategy import load_all
    strat = load_all()[name]
    s = load_settings()
    d = candles.load(sym, strat.interval, start=start, end=end)
    if d is None or len(d) < 3:
        return sym, None, []
    try:
        if getattr(strat, "needs_nifty", False):
            d.attrs["nifty"] = candles.load("NIFTY50", strat.interval, start=start, end=end)
        dctx = daily_context(sym, candles.load("NIFTY50", "day"), candles.load("INDIAVIX", "day"))
        return sym, (str(d.index[0])[:16], str(d.index[-1])[:16], len(d)), simulate(sym, d, strat, s, dctx)
    except Exception as e:
        log.warning("Test %s %s: %s", name, sym, type(e).__name__)
        return sym, None, []


# ----------------------------------------------------------------------------- whole market
def run(name, symbols=None, start=None, end=None, workers=None):
    """Test one strategy on every stock -> (trades DataFrame, data line dict). Also writes the report."""
    from .strategy import load_all
    strat = load_all()[name]
    syms = symbols or [s for s in candles.symbols(strat.interval) if s not in candles.INDICES]
    workers = workers or max(1, min(4, os.cpu_count() or 1))
    jobs = [(s, name, start, end) for s in syms]
    if workers > 1:
        from multiprocessing import get_context
        with get_context("spawn").Pool(workers) as p:
            res = p.map(_one, jobs, chunksize=8)
    else:
        res = [_one(j) for j in jobs]
    rows, spans, missing = [], [], []
    for sym, span, tr in res:
        if span is None:
            missing.append(sym)
        else:
            spans.append(span)
        rows += tr
    T = pd.DataFrame(rows)
    data = {"source": "Kite Connect historical candles (nothing else)", "interval": strat.interval,
            "stocks_tested": len(spans), "stocks_without_kite_candles": len(missing),
            "first": min((s[0] for s in spans), default=None), "last": max((s[1] for s in spans), default=None),
            "candles": int(sum(s[2] for s in spans)), "splits": "clear splits/bonuses found in Kite's own daily candles",
            "delisted": "not included (Kite lists only today's stocks)"}
    TESTS.mkdir(parents=True, exist_ok=True)
    if len(T):
        T.to_parquet(TESTS / f"{name}.parquet")
    report(name, strat, T, data)
    return T, data


def stats(T):
    if T is None or not len(T):
        return None
    n = T["net_pct"]
    w, ls = n[n > 0], n[n <= 0]
    return {"trades": int(len(T)), "win_pct": round(float((n > 0).mean() * 100), 1),
            "avg_net_pct": round(float(n.mean()), 3), "avg_win_pct": round(float(w.mean()), 2) if len(w) else None,
            "avg_loss_pct": round(float(ls.mean()), 2) if len(ls) else None,
            "profit_factor": round(float(w.sum() / -ls.sum()), 2) if len(ls) and ls.sum() < 0 else None,
            "stop_hit_pct": round(float((T["why"] == "stop-loss").mean() * 100), 1),
            "target_hit_pct": round(float((T["why"] == "target").mean() * 100), 1),
            "avg_bars": round(float(T["bars"].mean()), 1)}


def account(T, settings=None):
    """Money result if every trade had been taken in order, with the owner's sizing and cash limit."""
    s = settings or load_settings()
    cap0 = float(s.get("capital") or 0) or 51000.0
    if T is None or not len(T):
        return None
    E = T.sort_values("entry_time")
    cash, open_, eq_pts, taken, skipped = cap0, [], [], 0, 0
    for r in E.itertuples():
        for x in [x for x in open_ if x[0] <= r.entry_time]:
            cash += x[1]
            open_.remove(x)
        value = r.qty * r.entry
        if r.qty < 1 or value > cash:
            skipped += 1
            continue
        cash -= value
        open_.append((r.exit_time, value * (1 + r.net_pct / 100)))
        taken += 1
        eq_pts.append(cash + sum(x[1] for x in open_))
    end = cash + sum(x[1] for x in open_)
    eq = pd.Series(eq_pts) if eq_pts else pd.Series([cap0])
    dd = float((eq / eq.cummax() - 1).min() * 100)
    years = max((E["exit_time"].max() - E["entry_time"].min()).days / 365.25, 0.01)
    return {"start": cap0, "end": round(end), "taken": taken, "skipped_no_cash": skipped,
            "per_year_pct": round(((end / cap0) ** (1 / years) - 1) * 100, 1) if end > 0 else -100.0,
            "worst_fall_pct": round(dd, 1), "years": round(years, 1)}


def data_line(data):
    return (f"Data: {data['source']} - {data['interval']} candles, {data['stocks_tested']:,} stocks, "
            f"{data['first']} to {data['last']}, {data['candles']:,} candles; {data['stocks_without_kite_candles']:,} "
            f"stocks had no Kite candles; splits/bonuses: {data['splits']}; delisted stocks: {data['delisted']}. "
            "Yahoo: not used.")


def report(name, strat, T, data):
    OUT.mkdir(parents=True, exist_ok=True)
    L = [f"# Test: {name} (v{strat.version}) - {pd.Timestamp.now(tz='Asia/Kolkata'):%d %b %Y %H:%M} IST", "",
         f"**{data_line(data)}**", "",
         f"Rules: {strat.description or '(see swing/strategies/' + name + '.py)'}", "",
         f"Interval {strat.interval}, {strat.kind}; entry at the {'signal candle close' if strat.entry_at == 'close' else 'next open'}; "
         f"stop {strat.stop_fraction() * 100:.1f}% below entry; targets {', '.join(f'{r}R' for r in strat.targets_r) or 'none'}; "
         f"costs: Zerodha {strat.kind} charges + 0.15% slippage each side.", ""]
    if T is None or not len(T):
        L.append("No trades.")
    else:
        cut = T["entry_time"].max() - pd.DateOffset(years=HOLDOUT_YEARS)
        parts = [("All", T), (f"Before {cut:%b %Y}", T[T["entry_time"] < cut]), (f"Recent {HOLDOUT_YEARS} years", T[T["entry_time"] >= cut])]
        L += ["| Period | Trades | Win % | Avg after costs | Avg win | Avg loss | Profit factor | Stop hit | Target hit | Avg candles |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for lab, P in parts:
            s = stats(P)
            if s:
                L.append(f"| {lab} | {s['trades']:,} | {s['win_pct']} | {s['avg_net_pct']:+.2f}% | {s['avg_win_pct']}% | "
                         f"{s['avg_loss_pct']}% | {s['profit_factor']} | {s['stop_hit_pct']}% | {s['target_hit_pct']}% | {s['avg_bars']} |")
        a = account(T)
        if a:
            L += ["", f"Account (every trade in order, ₹{a['start']:,.0f}, owner's sizing, cash limit): ₹{a['end']:,.0f} after "
                      f"{a['years']} years ({a['per_year_pct']:+.1f}% a year), worst fall {a['worst_fall_pct']}%, "
                      f"{a['taken']:,} trades taken, {a['skipped_no_cash']:,} skipped (no free cash). Before tax."]
        y = T.groupby(T["entry_time"].dt.year)["net_pct"].agg(["count", "mean", lambda x: (x > 0).mean() * 100])
        L += ["", "| Year | Trades | Avg after costs | Win % |", "|---|---|---|---|"] + \
             [f"| {k} | {int(r['count']):,} | {r['mean']:+.2f}% | {r['<lambda_0>']:.0f} |" for k, r in y.iterrows()]
        L += ["", "Why trades ended: " + ", ".join(f"{k} {v}" for k, v in T["why"].value_counts().items()),
              "", "The Learner's breakdown (where it works and where it does not): results/learner/" + name + ".md"]
    (OUT / f"{name}.md").write_text("\n".join(L) + "\n")
    json.dump({"name": name, "version": strat.version, "data": data, "all": stats(T), "account": account(T) if len(T) else None},
              open(OUT / f"{name}.json", "w"), indent=1, default=str)
    return L
