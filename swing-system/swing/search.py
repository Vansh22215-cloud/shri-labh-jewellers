"""Walk-forward STRATEGY SEARCH over hundreds of variants (see DECISIONS.md D37-D42).

The honest way to search many strategies: each year, choose a variant using ONLY the
previous 36 months, then measure that choice on the following year. Only those
out-of-sample results are judged by the validation gate.
"""
import json
import math
import os
from datetime import date
from itertools import product

import numpy as np
import pandas as pd

from . import backtest, data_prices, engine, validate
from .config import ROOT, get_logger, load_strategy
from .families import FAMILIES, LIBRARY_FAMILIES, SHORT_FAMILIES, base_indicators, family_signals

log = get_logger()
VAL = ROOT / "validation"
PROCS = VAL / "search_procedures.json"
SEARCH_NAME = "wf-search-v1: 36m Sharpe pick, yearly, min 30 trades"
LOOKBACK_M, MIN_TRADES, FIRST_YEAR = 36, 30, 2016


def variant_space(base):
    out = []
    exits = {"targets": {"exit_style": "targets", "target1_r": 1.5, "target2_r": 3.0},
             "wide": {"exit_style": "targets", "target1_r": 2.0, "target2_r": 4.0},
             "trail": {"exit_style": "trail", "trail_atr_mult": 3.0}}
    for fam in FAMILIES:
        if fam == "mean_reversion":
            for stop, ex, hold, reg in product([2.0, 3.0], ["signal", "targets"], [5, 10], [True, False]):
                e = {"exit_style": "signal"} if ex == "signal" else exits["targets"]
                out.append(dict(base, family=fam, stop_atr_mult=stop, max_hold_days=hold, use_regime_filter=reg, **e))
            continue
        extra = [{"donchian_n": 20}, {"donchian_n": 55}] if fam == "donchian" else [{}]
        for x, stop, ex, hold, reg in product(extra, [1.5, 2.0, 3.0], list(exits), [10, 25, 50], [True, False]):
            out.append(dict(base, family=fam, stop_atr_mult=stop, max_hold_days=hold, use_regime_filter=reg,
                            **exits[ex], **x))
    for i, v in enumerate(out):
        v["name"] = f"S{i:03d}"
    return out


def short_space(base):
    """Short-term space (added 2026-11-03 at the user's request: hold 1-5 days, exit at target).
    Rule changes vs v1: holds of 2/3/5 days, tighter stops and targets, and a second sizing
    option of 2% risk per trade with up to 6 open trades."""
    out = []
    exits = {"quick": {"exit_style": "targets", "target1_r": 1.0, "target2_r": 2.0},
             "targets": {"exit_style": "targets", "target1_r": 1.5, "target2_r": 3.0},
             "trail": {"exit_style": "trail", "trail_atr_mult": 2.0}}
    sizing = {"1pct": {"risk_per_trade_pct": 1.0, "max_open_positions": 4},
              "2pct": {"risk_per_trade_pct": 2.0, "max_open_positions": 6}}
    fams = ["trend_pb_bo", "mean_reversion", "high52", "volume_surge", "nr7", "squeeze"] + SHORT_FAMILIES
    for fam, stop, ex, hold, sz, reg in product(fams, [1.0, 1.5, 2.0], list(exits), [2, 3, 5], list(sizing),
                                                [True, False]):
        e = dict(exits[ex])
        if fam == "mean_reversion" and ex == "trail":
            e = {"exit_style": "signal"}
        out.append(dict(base, family=fam, stop_atr_mult=stop, max_hold_days=hold, use_regime_filter=reg,
                        **e, **sizing[sz]))
    for i, v in enumerate(out):
        v["name"] = f"T{i:04d}"
    return out


def library_space(base):
    """Strategy library (ROADMAP S1-S9): famous published methods x exits (added 2026-11-03)."""
    out = []
    exits = {"targets": {"exit_style": "targets", "target1_r": 2.0, "target2_r": 4.0},
             "trail": {"exit_style": "trail", "trail_atr_mult": 3.0}}
    for fam, stop, ex, hold, reg in product(LIBRARY_FAMILIES, [2.0, 3.0], list(exits), [25, 50], [True, False]):
        out.append(dict(base, family=fam, stop_atr_mult=stop, max_hold_days=hold, use_regime_filter=reg, **exits[ex]))
    for i, v in enumerate(out):
        v["name"] = f"L{i:03d}"
    return out


SPACES = {
    "swing": (variant_space, SEARCH_NAME, "search_latest.json"),
    "short": (short_space, "wf-search-short-v1: 1-5 day holds, 36m Sharpe pick, yearly, min 30 trades",
              "search_short.json"),
    "library": (library_space, "wf-search-library-v1: famous methods, 36m Sharpe pick, yearly, min 30 trades",
                "search_library.json"),
}


def describe(v):
    ex = v.get("exit_style")
    exs = (f"targets {v['target1_r']}R/{v['target2_r']}R" if ex == "targets" else
           f"trailing stop {v.get('trail_atr_mult', 3.0)} ATR" if ex == "trail" else "exit on bounce")
    fam = v["family"] + (f"({v['donchian_n']})" if v["family"] == "donchian" else "")
    return (f"{fam}, stop {v['stop_atr_mult']} ATR, {exs}, max {v['max_hold_days']} days, "
            f"market filter {'on' if v.get('use_regime_filter', True) else 'off'}, "
            f"risk {v.get('risk_per_trade_pct', 1.0)}% x {v.get('max_open_positions', 4)} trades")


_G = {}


def _run_one(v):
    try:
        return _run_one_inner(v)
    except Exception as e:   # one broken variant must not kill the whole search
        log.error("Variant %s (%s) failed: %s", v["name"], v.get("family"), e)
        return None


def _run_one_inner(v):
    P, B, lf, end = _G["P"], _G["B"], _G["lf"], _G["end"]
    sig = family_signals(B, v)
    eq, tr, ex = backtest.run(P, sig, v, validate.WF_START, end, 45000.0, lf)
    m = eq.resample("ME").last()
    m = pd.concat([pd.Series([45000.0], index=[m.index[0] - pd.offsets.MonthEnd(1)]), m])
    mret = m.pct_change().dropna()
    if len(tr):
        tm = tr.groupby(pd.to_datetime(tr["exit_date"]).dt.to_period("M")).size()
        tm.index = tm.index.to_timestamp("M")
    else:
        tm = pd.Series(dtype=float)
    return v["name"], mret, tm.reindex(mret.index).fillna(0), backtest.stats(eq, tr)


def run_search(processes=None, space="swing"):
    space_fn, proc_name, out_file = SPACES[space]
    base = load_strategy("v1")
    variants = space_fn({k: v for k, v in base.items() if k not in ("name", "created", "description")})
    for v in variants:
        validate.register_variant(v, f"search: {describe(v)}")
    procs = json.loads(PROCS.read_text()) if PROCS.exists() else {}
    procs.setdefault(proc_name, str(date.today()))
    PROCS.write_text(json.dumps(procs, indent=1))

    P, sig0, nifty, industry, coverage, hist = engine.build(base)
    from . import universe
    mask = universe.membership_mask(hist, P["close"].index, list(P["close"].columns))
    B = base_indicators(P, nifty, mask, industry, base)
    lf = data_prices.liquid_fund_nav()
    end = pd.Timestamp(validate.holdout_start()) - pd.Timedelta(days=1)
    _G.update(P=P, B=B, lf=lf, end=end)
    n = processes or (max(1, (os.cpu_count() or 2) - 1) if os.name != "nt" else 1)
    log.info("Searching %d variants with %d process(es)", len(variants), n)
    if n > 1:
        import multiprocessing as mp
        with mp.get_context("fork").Pool(n) as pool:
            res = pool.map(_run_one, variants, chunksize=4)
    else:
        res = [_run_one(v) for v in variants]
    res = [r for r in res if r is not None]
    R = pd.DataFrame({r[0]: r[1] for r in res})
    T = pd.DataFrame({r[0]: r[2] for r in res})
    S = pd.DataFrame({r[0]: r[3] for r in res}).T
    byname = {v["name"]: v for v in variants}

    bees = data_prices.benchmark()["close"]
    bm = bees.resample("ME").last().pct_change().reindex(R.index)

    # walk-forward selection chain
    chain, picks = [], []
    years = sorted({d.year for d in R.index if d.year >= FIRST_YEAR})
    for y in years:
        start_y = pd.Timestamp(f"{y}-01-01")
        win = R[(R.index < start_y) & (R.index >= start_y - pd.DateOffset(months=LOOKBACK_M))]
        tw = T.loc[win.index].sum()
        ok = tw[tw >= MIN_TRADES].index
        if len(ok) == 0:
            continue
        sh = win[ok].mean() / win[ok].std().replace(0, np.nan) * math.sqrt(12)
        best = sh.idxmax()
        yr = R.loc[R.index.year == y, best]
        chain.append(yr)
        picks.append({"year": y, "picked": best, "how": describe(byname[best]),
                      "past_36m_sharpe": round(float(sh[best]), 2),
                      "return_pct": round((float((1 + yr).prod()) - 1) * 100, 2),
                      "niftybees_pct": round((float((1 + bm.loc[yr.index]).prod()) - 1) * 100, 2),
                      "trades": int(T.loc[yr.index, best].sum())})
    chain = pd.concat(chain)
    for pk in picks:
        pk["beat_niftybees"] = pk["return_pct"] > pk["niftybees_pct"]
    exc = (chain - bm.loc[chain.index]).dropna()
    t_chain = float(exc.mean() / (exc.std() / math.sqrt(len(exc)))) if len(exc) > 2 else 0.0
    ceq = 45000 * (1 + chain).cumprod()
    chain_dd = float((ceq / ceq.cummax() - 1).min() * 100)

    # holdout: pick with the 36 months before the holdout, run once, fresh
    hs = pd.Timestamp(validate.holdout_start())
    win = R[(R.index < hs) & (R.index >= hs - pd.DateOffset(months=LOOKBACK_M))]
    tw = T.loc[win.index].sum()
    ok = tw[tw >= MIN_TRADES].index
    sh = win[ok].mean() / win[ok].std().replace(0, np.nan) * math.sqrt(12)
    hpick = sh.idxmax()
    hv = byname[hpick]
    sigh = family_signals(B, hv)
    heq, htr, hex_ = backtest.run(P, sigh, hv, hs, P["close"].index[-1], 45000.0, lf)
    b = backtest.buy_and_hold(bees, hs, P["close"].index[-1])
    lfq = lf.reindex(lf.index.union(heq.index)).ffill().reindex(heq.index)
    hst = backtest.stats(heq, htr)
    hold = {"picked": hpick, "how": describe(hv), **hst,
            "niftybees_return_pct": round((b.iloc[-1] / 45000 - 1) * 100, 2),
            "liquid_fund_return_pct": round((lfq.iloc[-1] / lfq.iloc[0] - 1) * 100, 2)}

    n_proc = len(json.loads(PROCS.read_text()))
    req_share = min(0.80, 0.60 + 0.02 * max(0, n_proc - 1))
    req_t = max(1.0, math.sqrt(2 * math.log(max(n_proc, 1))))
    share = float(np.mean([p["beat_niftybees"] for p in picks]))
    n_tr = sum(p["trades"] for p in picks)
    checks = []

    def add(name, okk, detail):
        checks.append({"check": name, "passed": bool(okk), "detail": detail})
    add("Walk-forward search: picks beat NIFTYBEES in most years", share >= req_share,
        f"won {sum(p['beat_niftybees'] for p in picks)} of {len(picks)} years ({share:.0%}); needed {req_share:.0%}")
    add("Holdout: beats NIFTYBEES and liquid fund",
        hold["total_return_pct"] > hold["niftybees_return_pct"] and hold["total_return_pct"] > hold["liquid_fund_return_pct"],
        f"{hpick} {hold['total_return_pct']}% vs NIFTYBEES {hold['niftybees_return_pct']}% vs liquid fund {hold['liquid_fund_return_pct']}%")
    add("Holdout drawdown <= 15%", hold["max_drawdown_pct"] >= -15, f"{hold['max_drawdown_pct']}%")
    add("Walk-forward drawdown <= 20%", chain_dd >= -20, f"{chain_dd:.1f}%")
    add("Enough trades (>= 100)", n_tr >= 100, f"{n_tr} trades")
    add("Excess return statistically convincing", t_chain >= req_t,
        f"t-stat {t_chain:.2f}; needed {req_t:.2f} ({n_proc} search procedure(s) tried)")
    passed = all(c["passed"] for c in checks)

    # informational: the cherry-picked best variant over the whole walk-forward span
    full_exc = R.sub(bm, axis=0).dropna()
    tt = full_exc.mean() / (full_exc.std() / np.sqrt(len(full_exc)))
    top = tt.sort_values(ascending=False).head(10)
    raw_n = validate.n_variants()
    cherry = [{"variant": k, "how": describe(byname[k]), "t_vs_niftybees": round(float(t), 2),
               "cagr_pct": S.loc[k, "cagr_pct"], "max_dd_pct": S.loc[k, "max_drawdown_pct"],
               "trades": int(S.loc[k, "trades"])} for k, t in top.items()]
    fam_summary = (S.assign(family=[byname[i]["family"] for i in S.index])
                   .groupby("family")[["cagr_pct", "max_drawdown_pct", "sharpe"]].median().round(2)
                   .sort_values("cagr_pct", ascending=False))
    bees_cagr = backtest.stats(bees.loc[validate.WF_START:end])["cagr_pct"]

    # latest pick (what would go live if the gate passed)
    last = R.index[-1]
    win = R[R.index > last - pd.DateOffset(months=LOOKBACK_M)]
    tw = T.loc[win.index].sum()
    ok = tw[tw >= MIN_TRADES].index
    sh = win[ok].mean() / win[ok].std().replace(0, np.nan) * math.sqrt(12)
    latest = sh.idxmax()

    out = {"date": str(date.today()), "procedure": proc_name, "space": space, "variants_searched": len(variants),
           "raw_variants_ever": raw_n, "search_procedures_tried": n_proc, "passed": passed, "checks": checks,
           "picks": picks, "holdout": hold, "chain_t": round(t_chain, 2), "chain_max_dd": round(chain_dd, 2),
           "chain_cagr_pct": round(((1 + chain).prod() ** (12 / len(chain)) - 1) * 100, 2),
           "niftybees_cagr_pct_wf": bees_cagr,
           "cherry_picked_top10": cherry,
           "cherry_haircut_t_needed": round(math.sqrt(2 * math.log(raw_n)), 2),
           "family_medians": fam_summary.reset_index().to_dict("records"),
           "share_variants_beating_niftybees_cagr": round(float((S["cagr_pct"] > bees_cagr).mean()), 3),
           "latest_pick": {"variant": latest, "how": describe(byname[latest]), "params": byname[latest]}}
    (VAL / out_file).write_text(json.dumps(out, indent=1, default=str))
    S.assign(how=[describe(byname[i]) for i in S.index]).to_csv(VAL / f"search_all_variants_{space}.csv")
    from . import search_report
    search_report.write(out_file)
    log.info("Search done: gate %s", "PASSED" if passed else "FAILED")
    return out
