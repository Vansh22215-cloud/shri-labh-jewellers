"""Performance analytics (ROADMAP A1): what the strategy really earns, after charges AND tax, and why losers lose.

Inputs: backtest trades of the tips strategy (13 years) and the live/paper tips journal.
Outputs (validation/analytics.json + dashboard rows):
  * per year: trades, win rate, P&L before and after short-term capital gains tax (20% of each year's net gain;
    a losing year pays none - carry-forward ignored, conservative), worst fall
  * per month of the year (seasonality, information only)
  * loss review: how losers ended (stop, gap through stop, time limit) and their average size
"""
import json

import pandas as pd

from . import backtest, engine
from .config import ROOT, load_strategy

OUT = ROOT / "validation" / "analytics.json"
STCG = 0.20


def run(name):
    p = load_strategy(name)
    P, sig, *_ = engine.build(p)
    eq, tr, _ = backtest.run(P, sig, p, "2013-01-01", P["close"].index[-1], 45000, None)
    tr["year"] = pd.to_datetime(tr["exit_date"]).dt.year
    tr["month"] = pd.to_datetime(tr["entry_date"]).dt.month
    yearly = []
    for y, g in tr.groupby("year"):
        gross = float(g["pnl"].sum())
        tax = max(0.0, gross) * STCG
        e = eq[eq.index.year == y]
        dd = float((e / e.cummax() - 1).min() * 100) if len(e) else 0.0
        yearly.append({"year": int(y), "trades": int(len(g)), "win_pct": round((g["pnl"] > 0).mean() * 100, 1),
                       "pnl_before_tax": round(gross), "tax": round(tax), "pnl_after_tax": round(gross - tax),
                       "worst_fall_pct": round(dd, 1)})
    monthly = tr.groupby("month").agg(trades=("pnl", "size"), win_pct=("pnl", lambda x: (x > 0).mean() * 100),
                                      avg_pnl=("pnl", "mean")).round(1).reset_index().to_dict("records")
    losers = tr[tr["pnl"] <= 0]
    loss = losers.groupby("exit_reason").agg(count=("pnl", "size"), avg_loss=("pnl", "mean")).round(0)
    loss["share_pct"] = (loss["count"] / len(losers) * 100).round(1)
    total = float(tr["pnl"].sum())
    out = {"strategy": name, "years": yearly, "months": monthly,
           "loss_review": loss.reset_index().to_dict("records"),
           "summary": {"trades": int(len(tr)), "pnl_before_tax": round(total),
                       "tax_paid": round(sum(y["tax"] for y in yearly)),
                       "pnl_after_tax": round(sum(y["pnl_after_tax"] for y in yearly)),
                       "losing_years": int(sum(1 for y in yearly if y["pnl_before_tax"] < 0))}}
    OUT.write_text(json.dumps(out, indent=1, default=str))
    return out
