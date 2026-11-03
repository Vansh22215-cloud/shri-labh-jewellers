"""Market-dynamics research: how does the tips strategy behave in different market REGIMES?

Regime of a day (known at that day's close, no look-ahead):
  trend  : Nifty above / below its 200-day average
  fear   : India VIX below 16 = calm, 16-22 = normal, above 22 = nervous
  breadth: share of top-500 stocks above their 50-day average: < 40% weak, 40-60% mixed, > 60% strong
Each backtest trade is tagged with the regime on its signal day; we report win rate and average R per
regime, and the regime of TODAY with the historical behaviour of trades started in such markets.
"""
import json

import numpy as np
import pandas as pd

from . import backtest, data_prices, engine
from .config import ROOT, get_logger, load_settings, load_strategy

log = get_logger()
OUT = ROOT / "validation" / "research_regimes.json"


def regime_frame(nifty, breadth):
    vix = data_prices.load("INDIAVIX")
    vix = vix["close"].reindex(nifty.index).ffill() if vix is not None else pd.Series(np.nan, index=nifty.index)
    trend = np.where(nifty > nifty.rolling(200).mean(), "uptrend", "downtrend")
    fear = pd.cut(vix, [-1, 16, 22, 999], labels=["calm", "normal", "nervous"]).astype(str)
    br = pd.cut(breadth.reindex(nifty.index), [-1, 40, 60, 101], labels=["weak", "mixed", "strong"]).astype(str)
    return pd.DataFrame({"trend": trend, "fear": fear, "breadth": br, "vix": vix,
                         "breadth_pct": breadth.reindex(nifty.index)}, index=nifty.index)


def run(strategy=None):
    s = load_settings()
    name = strategy or s.get("aggressive_strategy", "a1")
    p = load_strategy(name)
    P, sig, nifty, *_ = engine.build(p)
    lf = data_prices.liquid_fund_nav()
    _, tr, _ = backtest.run(P, sig, p, "2013-01-01", P["close"].index[-1], 45000, lf)
    reg = regime_frame(nifty.reindex(P["close"].index), sig["breadth"])
    tr = tr.join(reg[["trend", "fear", "breadth"]], on="signal_date")
    out = {"strategy": name, "trades": int(len(tr)), "by": {}}
    for col in ("trend", "fear", "breadth"):
        g = tr.groupby(col).agg(trades=("pnl", "size"), win_pct=("pnl", lambda x: (x > 0).mean() * 100),
                                avg_r=("r_multiple", "mean"))
        out["by"][col] = g.round(2).to_dict("index")
    combo = tr.groupby(["trend", "fear"]).agg(trades=("pnl", "size"), win_pct=("pnl", lambda x: (x > 0).mean() * 100),
                                              avg_r=("r_multiple", "mean")).round(2)
    out["by"]["trend+fear"] = {f"{a}/{b}": v for (a, b), v in combo.to_dict("index").items()}
    today = reg.dropna(subset=["vix"]).iloc[-1]
    out["today"] = {"date": str(reg.dropna(subset=["vix"]).index[-1].date()), "trend": today["trend"],
                    "fear": today["fear"], "breadth": today["breadth"], "vix": round(float(today["vix"]), 1),
                    "breadth_pct": round(float(today["breadth_pct"]), 0)}
    OUT.write_text(json.dumps(out, indent=1, default=str))
    log.info("Regime research written for %s (%d trades)", name, len(tr))
    return out


def today_line(html=False):
    """One-paragraph 'market dynamics' summary for reports and Telegram."""
    try:
        o = json.loads(OUT.read_text())
    except Exception:
        return ""
    t = o["today"]
    key = f"{t['trend']}/{t['fear']}"
    h = o["by"]["trend+fear"].get(key)
    b = o["by"]["breadth"].get(t["breadth"])
    txt = (f"Market type: Nifty in {t['trend'].upper()}, mood {t['fear'].upper()} (VIX {t['vix']}), "
           f"breadth {t['breadth'].upper()} ({t['breadth_pct']:.0f}% of stocks above 50-day avg).")
    if h:
        txt += (f" In markets like this, past {o['strategy']} trades won {h['win_pct']:.0f}% "
                f"(avg {h['avg_r']:+.2f}R over {h['trades']} trades)")
        if b:
            txt += f"; with {t['breadth']} breadth: {b['win_pct']:.0f}% wins, avg {b['avg_r']:+.2f}R"
        txt += "."
    return txt
