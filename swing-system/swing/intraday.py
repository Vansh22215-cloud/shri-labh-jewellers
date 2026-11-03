"""INTRADAY (same-day) strategies on hourly bars, with Zerodha intraday (MIS) costs.

Bars: slot 0 = 09:15-10:15, 1 = 10:15, ... 5 = 14:15, 6 = 15:15-15:30.
Rules common to every variant (fixed before testing, see DECISIONS.md D43-D48):
  * A signal is known only when a bar CLOSES; entry at the NEXT bar's open. No entries after 14:15.
  * Stop-loss and target are checked bar by bar; if a bar's open is already beyond the stop we exit
    at that open; if stop and target are both inside one bar we assume the STOP came first.
  * Everything still open is sold at the 15:15 bar's open (square-off before the close).
  * Risk 1% of capital per trade, max position = 50% of capital (NO leverage), max 1-2 trades a day,
    taken in time order (and by relative volume when two trigger in the same bar) - no look-ahead.
  * Costs: Zerodha MIS - brokerage min(Rs 20, 0.03%) per order, STT 0.025% on the sell side, NSE
    0.00307%, SEBI Rs 10/crore, stamp 0.003% on buys, GST 18%; plus 0.05% slippage per side (re-checked at 0.10%).
  * Idle money earns NOTHING (it sits in the trading account) - conservative.
"""
import math
from itertools import product

import numpy as np
import pandas as pd

from . import data_prices, intraday_data
from .config import DATA, get_logger

log = get_logger()
SLIP = 0.0005   # per side; the gate also re-checks at 2x (D46)


def mis_costs(buy_value, sell_value):
    brok = min(20, 0.0003 * buy_value) + min(20, 0.0003 * sell_value)
    exch = (buy_value + sell_value) * 0.0000307
    sebi = (buy_value + sell_value) * 10 / 1e7
    return brok + sell_value * 0.00025 + exch + sebi + buy_value * 0.00003 + 0.18 * (brok + exch + sebi)


def context(days, syms, cube):
    """Per (day, stock) facts known BEFORE the day starts (or at 10:15 for first-bar facts)."""
    o, h, l, c, v = (cube[k] for k in ("o", "h", "l", "c", "v"))
    prev_close = np.vstack([np.full((1, len(syms)), np.nan), c[:-1, :, 6]])
    daily = {}
    for s in syms:
        df = data_prices.load(s)
        if df is not None:
            daily[s] = data_prices.adjusted(df)["raw_close"]
    dc = pd.DataFrame(daily).reindex(columns=syms)
    s50, s200 = dc.rolling(50).mean(), dc.rolling(200).mean()
    up = ((dc > s50) & (s50 > s200)).shift(1)        # as of the previous day's close
    dn = ((dc < s50) & (s50 < s200)).shift(1)
    up = up.reindex(days).fillna(False).values.astype(bool)
    dn = dn.reindex(days).fillna(False).values.astype(bool)
    fbv = pd.DataFrame(v[:, :, 0]).rolling(20, min_periods=10).mean().shift(1).values
    with np.errstate(divide="ignore", invalid="ignore"):
        rvol = v[:, :, 0] / fbv
    return {"prev_close": prev_close, "up": up, "dn": dn, "rvol": rvol}


def signals(cube, ctx, var):
    """For each (day, stock): direction (+1/-1/0), entry slot, stop. Uses only closed bars."""
    o, h, l, c = (cube[k] for k in ("o", "h", "l", "c"))
    D, S = o.shape[:2]
    direction = np.zeros((D, S), int)
    entry_slot = np.full((D, S), -1)
    h0, l0, o0, c0 = h[:, :, 0], l[:, :, 0], o[:, :, 0], c[:, :, 0]
    mid = (h0 + l0) / 2
    gap = o0 / ctx["prev_close"] - 1
    strat = var["strategy"]
    if strat in ("orb_long", "orb_both"):
        for k in range(1, 5):            # bars 10:15..13:15 closing beyond the first-hour range
            new_long = (direction == 0) & (c[:, :, k] > h0)
            direction[new_long], entry_slot[new_long] = 1, k + 1
            if strat == "orb_both":
                new_short = (direction == 0) & (c[:, :, k] < l0)
                direction[new_short], entry_slot[new_short] = -1, k + 1
        stop = np.where(direction == 1, l0 if var["stop"] == "range" else mid,
                        h0 if var["stop"] == "range" else mid)
    elif strat == "gap_go":
        m = (gap >= 0.01) & (c0 > o0)
        direction[m], entry_slot[m] = 1, 1
        stop = l0 if var["stop"] == "range" else mid
    elif strat == "gap_fade":
        m = (gap >= 0.015) & (c0 < o0)
        direction[m], entry_slot[m] = -1, 1
        stop = h0 if var["stop"] == "range" else mid
    elif strat == "first_hour_momo":
        m = (c0 / o0 - 1 >= 0.01) & (ctx["rvol"] >= 2)
        direction[m], entry_slot[m] = 1, 1
        stop = l0 if var["stop"] == "range" else mid
    else:
        raise ValueError(strat)
    if var["trend_filter"]:
        direction[(direction == 1) & ~ctx["up"]] = 0
        direction[(direction == -1) & ~ctx["dn"]] = 0
    direction[np.isnan(o0) | np.isnan(ctx["prev_close"])] = 0
    return direction, entry_slot, stop


def run(days, syms, cube, ctx, var, start=None, end=None, capital=45000.0, slip=None):
    SL = SLIP if slip is None else slip
    o, h, l, c = (cube[k] for k in ("o", "h", "l", "c"))
    direction, entry_slot, stop = signals(cube, ctx, var)
    rvol = np.nan_to_num(ctx["rvol"], nan=0)
    eq, trades, dates = capital, [], []
    curve = []
    for d in range(len(days)):
        if (start is not None and days[d] < start) or (end is not None and days[d] > end):
            continue
        idx = np.nonzero(direction[d])[0]
        pnl_day = 0.0
        if len(idx):
            order = sorted(idx, key=lambda j: (entry_slot[d, j], -rvol[d, j]))[:var["max_trades"]]
            for j in order:
                es, side, st = entry_slot[d, j], direction[d, j], stop[d, j]
                ep = o[d, j, es]
                if not np.isfinite(ep) or not np.isfinite(st):
                    continue
                fill = ep * (1 + SL * side)
                r = (fill - st) * side
                if r <= 0:
                    continue
                qty = math.floor(min(capital * 0.01 / r, capital * 0.5 / fill))
                if qty < 1:
                    continue
                tgt = fill + side * var["target_r"] * r if var["target_r"] else None
                exit_px, why = None, None
                for k in range(es, 6):
                    ok_, hk, lk = o[d, j, k], h[d, j, k], l[d, j, k]
                    if not np.isfinite(ok_):
                        continue
                    if k > es and (ok_ - st) * side <= 0:
                        exit_px, why = ok_, "stop_gap"; break
                    if (lk <= st) if side == 1 else (hk >= st):
                        exit_px, why = st, "stop"; break
                    if tgt is not None and ((hk >= tgt) if side == 1 else (lk <= tgt)):
                        exit_px, why = (ok_ if (k > es and (ok_ - tgt) * side >= 0) else tgt), "target"; break
                if exit_px is None:
                    exit_px, why = o[d, j, 6], "squareoff"
                    if not np.isfinite(exit_px):
                        exit_px = c[d, j, 5]
                xf = exit_px * (1 - SL * side)
                buy_v, sell_v = (fill * qty, xf * qty) if side == 1 else (xf * qty, fill * qty)
                pnl = (xf - fill) * side * qty - mis_costs(buy_v, sell_v)
                pnl_day += pnl
                trades.append({"date": days[d], "symbol": syms[j], "side": "long" if side == 1 else "short",
                               "entry": round(fill, 2), "exit": round(xf, 2), "reason": why,
                               "pnl": round(pnl, 2), "r_multiple": round(pnl / (r * qty), 3)})
        eq += pnl_day
        curve.append((days[d], eq))
    eqs = pd.Series([e for _, e in curve], index=pd.DatetimeIndex([d for d, _ in curve]), name="equity")
    return eqs, pd.DataFrame(trades)


def variant_space():
    out = []
    for strat, tgt, stp, tf, mt in product(["orb_long", "orb_both", "gap_go", "gap_fade", "first_hour_momo"],
                                           [1.0, 2.0, None], ["range", "mid"], [True, False], [1, 2]):
        out.append({"strategy": strat, "target_r": tgt, "stop": stp, "trend_filter": tf, "max_trades": mt})
    for i, v in enumerate(out):
        v["name"] = f"I{i:03d}"
    return out


def describe(v):
    return (f"{v['strategy']}, target {str(v['target_r']) + 'R' if v['target_r'] else 'none (exit 3:15 pm)'}, "
            f"stop at first-hour {'low/high' if v['stop'] == 'range' else 'midpoint'}, trend filter "
            f"{'on' if v['trend_filter'] else 'off'}, max {v['max_trades']} trade(s)/day")


HOLDOUT_START = pd.Timestamp("2026-07-01")
LOOKBACK_MONTHS, MIN_TRADES = 6, 30
PROC_NAME = "wf-search-intraday-v1: hourly bars, quarterly pick by 6m Sharpe, min 30 trades"


def run_search():
    import json
    from datetime import date
    from . import validate
    from .config import ROOT
    VAL = ROOT / "validation"
    syms = (DATA / "intraday_universe.txt").read_text().split()
    days, syms, cube = intraday_data.load_cube(syms)
    ctx = context(days, syms, cube)
    variants = variant_space()
    for v in variants:
        validate.register_variant(dict(v, kind="intraday"), "intraday: " + describe(v))
    procs = json.loads((VAL / "search_procedures.json").read_text()) if (VAL / "search_procedures.json").exists() else {}
    procs.setdefault(PROC_NAME, str(date.today()))
    (VAL / "search_procedures.json").write_text(json.dumps(procs, indent=1))
    cap = 45000.0
    wf_end = HOLDOUT_START - pd.Timedelta(days=1)
    R, NT, ST = {}, {}, {}
    for v in variants:
        eq, tr = run(days, syms, cube, ctx, v, end=wf_end)
        R[v["name"]] = eq.diff().fillna(eq.iloc[0] - cap) / cap
        NT[v["name"]] = (tr.groupby("date").size().reindex(eq.index).fillna(0) if len(tr)
                         else pd.Series(0, index=eq.index))
        ST[v["name"]] = {"total_pnl": round(eq.iloc[-1] - cap, 0), "trades": len(tr),
                         "win_rate_pct": round((tr["pnl"] > 0).mean() * 100, 1) if len(tr) else None}
    R, NT = pd.DataFrame(R), pd.DataFrame(NT)
    byname = {v["name"]: v for v in variants}
    bees = data_prices.benchmark()["close"]
    lf = data_prices.liquid_fund_nav()

    def pick(before):
        win = R[(R.index < before) & (R.index >= before - pd.DateOffset(months=LOOKBACK_MONTHS))]
        nt = NT.loc[win.index].sum()
        ok = nt[nt >= MIN_TRADES].index
        if len(ok) == 0 or len(win) < 60:
            return None
        sh = win[ok].mean() / win[ok].std().replace(0, np.nan)
        return sh.idxmax()

    quarters = pd.period_range(R.index[0], wf_end, freq="Q")
    picks, chain = [], []
    for q in quarters:
        qs, qe = q.start_time, min(q.end_time, wf_end)
        best = pick(qs)
        if best is None:
            continue
        r = R.loc[(R.index >= qs) & (R.index <= qe), best]
        b = bees.loc[qs:qe]
        lq = lf.reindex(lf.index.union(r.index)).ffill().reindex(r.index)
        picks.append({"quarter": str(q), "picked": best, "how": describe(byname[best]),
                      "return_pct": float(round(r.sum() * 100, 2)), "trades": int(NT.loc[r.index, best].sum()),
                      "niftybees_pct": float(round((b.iloc[-1] / b.iloc[0] - 1) * 100, 2)) if len(b) > 1 else 0.0,
                      "liquid_fund_pct": round((lq.iloc[-1] / lq.iloc[0] - 1) * 100, 2) if len(lq) > 1 else 0.0})
        chain.append(r)
    for p in picks:
        p["beat_niftybees"] = bool(p["return_pct"] > p["niftybees_pct"])
    chain = pd.concat(chain) if chain else pd.Series(dtype=float)
    ceq = cap * (1 + chain.cumsum())
    chain_dd = float((ceq / ceq.cummax() - 1).min() * 100) if len(ceq) else 0.0
    bd = bees.pct_change().reindex(chain.index).fillna(0)
    exc = (chain - bd).resample("ME").sum()
    t_chain = float(exc.mean() / (exc.std() / math.sqrt(len(exc)))) if len(exc) > 2 and exc.std() > 0 else 0.0

    hp = pick(HOLDOUT_START)
    hv = byname[hp]
    heq, htr = run(days, syms, cube, ctx, hv, start=HOLDOUT_START)
    heq2, _ = run(days, syms, cube, ctx, hv, start=HOLDOUT_START, slip=2 * SLIP)
    hb = bees.loc[HOLDOUT_START:]
    hl = lf.reindex(lf.index.union(heq.index)).ffill().reindex(heq.index)
    hold = {"picked": hp, "how": describe(hv), "return_pct": float(round((heq.iloc[-1] / cap - 1) * 100, 2)),
            "return_pct_double_slippage": float(round((heq2.iloc[-1] / cap - 1) * 100, 2)),
            "max_drawdown_pct": round(float((heq / heq.cummax() - 1).min() * 100), 2), "trades": len(htr),
            "niftybees_return_pct": float(round((hb.iloc[-1] / hb.iloc[0] - 1) * 100, 2)),
            "liquid_fund_return_pct": float(round((hl.iloc[-1] / hl.iloc[0] - 1) * 100, 2))}

    n_proc = len(procs)
    req_share = min(0.80, 0.60 + 0.02 * max(0, n_proc - 1))
    req_t = max(1.0, math.sqrt(2 * math.log(max(n_proc, 1))))
    share = float(np.mean([p["beat_niftybees"] for p in picks])) if picks else 0.0
    checks = []

    def add(name, ok, detail):
        checks.append({"check": name, "passed": bool(ok), "detail": detail})
    add("Walk-forward: quarterly picks beat NIFTYBEES in most quarters", share >= req_share,
        f"won {sum(p['beat_niftybees'] for p in picks)} of {len(picks)} quarters ({share:.0%}); needed {req_share:.0%}")
    add("Holdout: beats NIFTYBEES and liquid fund",
        hold["return_pct"] > hold["niftybees_return_pct"] and hold["return_pct"] > hold["liquid_fund_return_pct"],
        f"{hp} {hold['return_pct']}% vs NIFTYBEES {hold['niftybees_return_pct']}% vs liquid fund {hold['liquid_fund_return_pct']}%")
    add("Holdout still beats liquid fund with double slippage",
        hold["return_pct_double_slippage"] > hold["liquid_fund_return_pct"], f"{hold['return_pct_double_slippage']}%")
    add("Holdout drawdown <= 15%", hold["max_drawdown_pct"] >= -15, f"{hold['max_drawdown_pct']}%")
    add("Walk-forward drawdown <= 20%", chain_dd >= -20, f"{chain_dd:.1f}%")
    add("Enough trades (>= 100)", sum(p["trades"] for p in picks) >= 100, f"{sum(p['trades'] for p in picks)} trades")
    add("Excess return statistically convincing", t_chain >= req_t,
        f"t-stat {t_chain:.2f}; needed {req_t:.2f} ({n_proc} search procedures tried)")
    S = pd.DataFrame(ST).T.assign(how=[describe(byname[i]) for i in ST])
    S.to_csv(VAL / "search_all_variants_intraday.csv")
    top = S.sort_values("total_pnl", ascending=False).head(10)
    out = {"date": str(date.today()), "space": "intraday", "procedure": PROC_NAME, "variants_searched": len(variants),
           "passed": all(c["passed"] for c in checks), "checks": checks, "picks": picks, "holdout": hold,
           "chain_pnl_rs": round(float(chain.sum() * cap), 0), "chain_max_dd": round(chain_dd, 2),
           "chain_t": round(t_chain, 2),
           "share_variants_profitable": round(float((S["total_pnl"] > 0).mean()), 3),
           "cherry_picked_top10": top.reset_index(names="variant").to_dict("records"),
           "data_from": str(days[0].date()), "data_to": str(days[-1].date()), "stocks": len(syms)}
    (VAL / "search_intraday.json").write_text(json.dumps(out, indent=1, default=str))
    log.info("Intraday search: gate %s", "PASSED" if out["passed"] else "FAILED")
    return out
