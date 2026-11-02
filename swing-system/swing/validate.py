"""THE VALIDATION GATE.

Live tips are allowed ONLY if ALL of these hold (rules fixed before the first run,
see DECISIONS.md; they are never loosened to make a strategy pass):
  1. Walk-forward: the strategy beats buying NIFTYBEES (after all costs) in at least
     `required_wf_share` of the yearly out-of-sample periods. The bar starts at 60%
     and rises 2 percentage points for every extra variant ever tried (max 80%).
  2. Holdout (never used for any choice): strategy beats NIFTYBEES AND the liquid fund.
  3. Max drawdown <= 20% over the walk-forward span and <= 15% in the holdout.
  4. Enough evidence: >= 100 trades in the walk-forward span.
  5. Multiple-testing haircut: the t-statistic of monthly returns in excess of NIFTYBEES
     must be >= max(1.0, sqrt(2 ln N)) where N = number of variants tried.
"""
import hashlib
import json
import math
from datetime import date

import numpy as np
import pandas as pd

from . import backtest, data_prices
from .config import ROOT, get_logger

log = get_logger()
VAL = ROOT / "validation"
VAL.mkdir(exist_ok=True)
REGISTRY = VAL / "variants_tried.json"
GATE = VAL / "gate_status.json"

WF_START = "2013-01-01"
HOLDOUT_FILE = VAL / "holdout.json"


def holdout_start():
    """Start of the untouched holdout. Rotated forward by the weekly job (see DECISIONS.md)."""
    try:
        return json.loads(HOLDOUT_FILE.read_text())["start"]
    except Exception:
        HOLDOUT_FILE.write_text(json.dumps({"start": "2025-05-01", "history": []}, indent=1))
        return "2025-05-01"


HOLDOUT_START = holdout_start()


def params_hash(params):
    core = {k: v for k, v in params.items() if k not in ("name", "created", "description")}
    return hashlib.sha1(json.dumps(core, sort_keys=True).encode()).hexdigest()[:10]


def register_variant(params, note):
    reg = json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {}
    h = params_hash(params)
    if h not in reg:
        reg[h] = {"name": params.get("name"), "first_tested": str(date.today()), "note": note}
        REGISTRY.write_text(json.dumps(reg, indent=1))
    return len(reg)


def n_variants():
    return len(json.loads(REGISTRY.read_text())) if REGISTRY.exists() else 1


def periods(end):
    out = []
    for y in range(int(WF_START[:4]), int(HOLDOUT_START[:4]) + 1):
        s = pd.Timestamp(f"{y}-01-01")
        e = min(pd.Timestamp(f"{y}-12-31"), pd.Timestamp(HOLDOUT_START) - pd.Timedelta(days=1))
        if s < pd.Timestamp(HOLDOUT_START):
            out.append((f"WF {y}" if e.month == 12 else f"WF {y} (Jan-{e:%b})", s, e))
    out.append(("HOLDOUT", pd.Timestamp(HOLDOUT_START), pd.Timestamp(end)))
    return out


def evaluate(P, sig, params, capital=45000.0):
    """Run every period independently (fresh capital each time) + benchmarks."""
    lf = data_prices.liquid_fund_nav()
    bees = data_prices.benchmark()
    end = P["close"].index[-1]
    rows, all_trades = [], []
    for name, s, e in periods(end):
        eq, tr, ex = backtest.run(P, sig, params, s, e, capital, lf)
        if len(eq) < 5:
            continue
        b = backtest.buy_and_hold(bees["open"].reindex(eq.index).fillna(bees["close"]), s, e, capital)
        b = b * (bees["close"].reindex(eq.index) / bees["open"].reindex(eq.index)).fillna(1)  # mark at close
        lfq = lf.reindex(lf.index.union(eq.index)).ffill().reindex(eq.index)
        m = backtest.exposure_matched(bees["close"], ex, lf, capital)
        st = backtest.stats(eq, tr)
        row = {"period": name, "start": str(s.date()), "end": str(eq.index[-1].date()), **st,
               "niftybees_return_pct": round((b.iloc[-1] / capital - 1) * 100, 2),
               "niftybees_max_dd_pct": round(((b / b.cummax()) - 1).min() * 100, 2),
               "liquid_fund_return_pct": round((lfq.iloc[-1] / lfq.iloc[0] - 1) * 100, 2),
               "exposure_matched_return_pct": round((m.iloc[-1] / capital - 1) * 100, 2),
               "avg_exposure_pct": round(ex.mean() * 100, 1)}
        row["beat_niftybees"] = row["total_return_pct"] > row["niftybees_return_pct"]
        rows.append(row)
        if len(tr):
            tr["period"] = name
            all_trades.append(tr)
    trades = pd.concat(all_trades) if all_trades else pd.DataFrame()
    return pd.DataFrame(rows), trades


def continuous(P, sig, params, capital=45000.0):
    """One continuous run over the walk-forward span (holdout excluded) for the t-test."""
    lf = data_prices.liquid_fund_nav()
    bees = data_prices.benchmark()["close"]
    end = pd.Timestamp(HOLDOUT_START) - pd.Timedelta(days=1)
    eq, tr, ex = backtest.run(P, sig, params, WF_START, end, capital, lf)
    m_s = eq.resample("ME").last().pct_change().dropna()
    m_b = bees.reindex(eq.index).ffill().resample("ME").last().pct_change().dropna()
    exc = (m_s - m_b).dropna()
    t = exc.mean() / (exc.std() / math.sqrt(len(exc))) if len(exc) > 2 and exc.std() > 0 else 0.0
    return eq, tr, ex, float(t)


def gate(table, cont_eq, cont_trades, tstat, n_var):
    wf = table[table["period"].str.startswith("WF")]
    ho = table[table["period"] == "HOLDOUT"]
    req_share = min(0.80, 0.60 + 0.02 * max(0, n_var - 1))
    req_t = max(1.0, math.sqrt(2 * math.log(max(n_var, 1))))
    share = wf["beat_niftybees"].mean() if len(wf) else 0
    wf_dd = backtest.stats(cont_eq)["max_drawdown_pct"]
    checks = []

    def add(name, ok, detail):
        checks.append({"check": name, "passed": bool(ok), "detail": detail})
    add("Walk-forward: beats NIFTYBEES in most periods", share >= req_share,
        f"won {int(wf['beat_niftybees'].sum())} of {len(wf)} periods ({share:.0%}); needed {req_share:.0%}")
    if len(ho):
        h = ho.iloc[0]
        add("Holdout: beats NIFTYBEES and liquid fund",
            h["total_return_pct"] > h["niftybees_return_pct"] and h["total_return_pct"] > h["liquid_fund_return_pct"],
            f"strategy {h['total_return_pct']:.1f}% vs NIFTYBEES {h['niftybees_return_pct']:.1f}% "
            f"vs liquid fund {h['liquid_fund_return_pct']:.1f}%")
        add("Holdout drawdown <= 15%", h["max_drawdown_pct"] >= -15, f"{h['max_drawdown_pct']:.1f}%")
    else:
        add("Holdout available", False, "no holdout data")
    add("Walk-forward drawdown <= 20%", wf_dd >= -20, f"{wf_dd:.1f}% (continuous run)")
    add("Enough trades (>= 100)", len(cont_trades) >= 100, f"{len(cont_trades)} trades")
    add("Excess return statistically convincing", tstat >= req_t,
        f"t-stat {tstat:.2f}; needed {req_t:.2f} (because {n_var} variant(s) tried)")
    passed = all(c["passed"] for c in checks)
    return {"passed": passed, "checks": checks, "variants_tried": n_var,
            "required_wf_share": req_share, "required_t": round(req_t, 2)}


def setup_stats(trades):
    """Historical hit-rate per setup type (walk-forward trades only)."""
    out = {}
    if len(trades) == 0:
        return out
    for s, g in trades.groupby("setup"):
        out[s] = {"trades": int(len(g)), "win_rate_pct": round((g["pnl"] > 0).mean() * 100, 1),
                  "avg_r": round(g["r_multiple"].mean(), 2), "avg_days": round(g["days"].mean(), 1)}
    return out
