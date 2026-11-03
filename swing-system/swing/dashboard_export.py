"""Exports everything the dashboard shows into ONE JSON file of rows (data/dashboard/desk.json).

Each row has a `table` field (headline, market, idea, trade, tip, pertrade, family, research, regime, equity, fii)
and the page splits them. Refreshed after every scan and every nightly run (ROADMAP UI1).
"""
import json
import re
from datetime import datetime

import numpy as np
import pandas as pd

from . import data_prices, journal
from .config import DATA, ROOT, load_settings, load_strategy, load_state

OUT_DIR = DATA / "dashboard"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / "desk.json"
IDEAS = DATA / "last_ideas.json"
VAL = ROOT / "validation"


def save_ideas(ideas, trades, source):
    """Called by the hourly scan / nightly run with their latest ideas and your-trade statuses."""
    IDEAS.write_text(json.dumps({"at": str(datetime.now()), "source": source, "ideas": ideas, "trades": trades},
                                default=str))


def _num(x, nd=2):
    try:
        x = float(x)
        return None if not np.isfinite(x) else round(x, nd)
    except Exception:
        return None


def build():
    s = load_settings()
    st = load_state()
    name = s.get("aggressive_strategy", "a1") if s.get("tips_mode") == "aggressive" else s.get("live_strategy")
    p = load_strategy(name)
    rows = []
    li = json.loads(IDEAS.read_text()) if IDEAS.exists() else {"ideas": [], "trades": [], "at": None, "source": "-"}

    # market
    n = data_prices.load("NIFTY50")
    vix = data_prices.load("INDIAVIX")
    reg = {}
    try:
        reg = json.loads((VAL / "research_regimes.json").read_text())["today"]
    except Exception:
        pass
    fii_last = None
    try:
        from .intel_positioning import load_panel
        pp = load_panel()
        fii_last = float(pp["fii_idx_fut_long_pct"].iloc[-1]) if pp is not None else None
    except Exception:
        pp = None
    mk = []
    if n is not None and len(n) > 200:
        c = n["close"]
        mk.append({"metric": "Nifty 50", "value": f"{c.iloc[-1]:,.0f}",
                   "note": f"{(c.iloc[-1] / c.iloc[-2] - 1) * 100:+.2f}% on the day · {(c.iloc[-1] / c.tail(200).mean() - 1) * 100:+.1f}% vs 200-day avg",
                   "status": "good" if c.iloc[-1] > c.tail(200).mean() else "bad"})
    if reg:
        mk.append({"metric": "Breadth", "value": f"{reg.get('breadth_pct', 0):.0f}%", "note": "of top-500 stocks above their 50-day avg",
                   "status": "good" if reg.get("breadth_pct", 0) >= 50 else "warn" if reg.get("breadth_pct", 0) >= 40 else "bad"})
    if vix is not None:
        v = vix["close"].dropna()
        mk.append({"metric": "India VIX", "value": f"{v.iloc[-1]:.1f}", "note": f"{(v.iloc[-1] / v.iloc[-2] - 1) * 100:+.1f}% on the day (fear gauge)",
                   "status": "good" if v.iloc[-1] < 16 else "warn" if v.iloc[-1] < 22 else "bad"})
    if fii_last is not None:
        mk.append({"metric": "FII index futures", "value": f"{fii_last:.0f}% long",
                   "note": "big foreign funds' position in Nifty futures", "status": "good" if fii_last >= 50 else "warn" if fii_last >= 30 else "bad"})
    if reg:
        mk.append({"metric": "Market type", "value": f"{reg.get('trend', '?')} / {reg.get('fear', '?')}",
                   "note": "Nifty trend / mood (VIX)", "status": "good" if reg.get("trend") == "uptrend" else "warn"})
    rows += [dict(table="market", **m) for m in mk]

    # ideas and your trades (latest scan)
    for i, it in enumerate(li.get("ideas", []), 1):
        cal = it.get("cal") or {}
        rows.append({"table": "idea", "rank": i, "symbol": it["symbol"], "name": it.get("name") or "",
                     "setup": it.get("setup"), "score": _num(it.get("score"), 0), "risk": it.get("risk"),
                     "ltp": _num(it.get("ltp") or it.get("last_close")), "entry_low": _num(it.get("entry_low")),
                     "entry_high": _num(it.get("entry_high")), "stop": _num(it.get("stop")),
                     "target1": _num(it.get("target1")), "target2": _num(it.get("target2")), "target3": _num(it.get("target3")),
                     "qty": it.get("qty"), "max_loss": _num(it.get("risk_rupees"), 0),
                     "p_t1": cal.get("p_t1"), "p_stop": cal.get("p_stop"),
                     "why": "; ".join((it.get("reasons") or [])[:3]),
                     "risk_factors": "; ".join(it.get("risk_reasons") or it.get("risks") or [])})
    for t in li.get("trades", []):
        rows.append({"table": "trade", "symbol": t.get("symbol"), "buy": _num(t.get("buy")), "last": _num(t.get("last")),
                     "pnl_pct": _num(t.get("pnl_pct"), 1), "status": re.sub("<[^>]+>", "", str(t.get("status", "")))})

    # tips journal
    tj = journal.load_tips()
    for _, t in tj[tj["kind"] == "tip"].tail(60).iterrows():
        rows.append({"table": "tip", "date": str(t["date"]), "symbol": t["symbol"], "status": str(t["status"]),
                     "entry_price": _num(t.get("entry_price")), "exit_reason": None if pd.isna(t.get("exit_reason")) else t.get("exit_reason"),
                     "pnl": _num(t.get("pnl"), 0), "r_multiple": _num(t.get("r_multiple"), 2)})

    # per-trade stats + calibrated odds
    bs = p.get("backtest_stats") or {}
    cal = {}
    try:
        cal = json.loads((VAL / "calibration.json").read_text()).get(name, {}).get("all", {})
    except Exception:
        pass
    for k, lab, unit in (("win_rate_pct", "Winning trades", "%"), ("avg_win_rs", "Average win", "Rs"),
                         ("avg_loss_rs", "Average loss", "Rs"), ("avg_per_trade_rs", "Average per trade", "Rs"),
                         ("avg_days_held", "Average holding", "days"), ("trades_per_month", "Trades per month", ""),
                         ("max_losing_streak", "Longest losing streak", "trades")):
        if k in bs:
            rows.append({"table": "pertrade", "metric": lab, "value": bs[k], "unit": unit})
    for k, lab in (("p_t1", "Reached T1 before stop"), ("p_t2", "Reached T2 before stop"), ("p_stop", "Hit the stop")):
        if k in cal:
            rows.append({"table": "pertrade", "metric": lab, "value": cal[k], "unit": "%"})

    # families (median of each family's variants)
    seen = set()
    for fn in ("search_library.json", "search_latest.json"):
        try:
            o = json.loads((VAL / fn).read_text())
        except Exception:
            continue
        for f in o.get("family_medians", []):
            if f["family"] in seen:
                continue
            seen.add(f["family"])
            rows.append({"table": "family", "family": f["family"], "cagr_pct": f["cagr_pct"],
                         "max_drawdown_pct": f["max_drawdown_pct"], "sharpe": f["sharpe"],
                         "group": "famous methods" if fn == "search_library.json" else "core strategies"})

    # research log
    try:
        from .weekly import parse_proposals
        for pr in parse_proposals():
            stt = pr.get("status", "")
            res = "adopted" if stt.startswith("PROMOTED") else "rejected" if stt.startswith("rejected") else "queued"
            m = re.search(r"CAGR ([\d.\-]+)% vs ([\d.\-]+)%", stt)
            rows.append({"table": "research", "id": pr.get("id"), "result": res,
                         "idea": (pr.get("reason") or "")[:140], "cagr_pct": float(m.group(1)) if m else None,
                         "base_cagr_pct": float(m.group(2)) if m else None})
    except Exception:
        pass

    # regimes
    try:
        rg = json.loads((VAL / "research_regimes.json").read_text())["by"]["trend+fear"]
        for k, v in rg.items():
            rows.append({"table": "regime", "regime": k, "trades": v["trades"], "win_pct": v["win_pct"], "avg_r": v["avg_r"]})
    except Exception:
        pass

    # equity: walk-forward months of the current pick vs NIFTYBEES (from the saved search matrix)
    try:
        R = pd.read_csv(VAL / "search_R_combined.csv.gz", index_col=0, parse_dates=True)
        col = p.get("search_variant", "S385")
        if col in R.columns:
            eq = 45000 * (1 + R[col].fillna(0)).cumprod()
            bees = data_prices.benchmark()["close"].resample("ME").last()
            b = bees.reindex(eq.index).ffill()
            b = 45000 * b / b.iloc[0]
            for d, v in eq.items():
                rows.append({"table": "equity", "month": str(d.date()), "strategy": round(float(v)),
                             "niftybees": round(float(b.get(d, np.nan))) if pd.notna(b.get(d, np.nan)) else None})
    except Exception:
        pass

    # FII positioning, weekly, last 3 years
    if pp is not None and len(pp):
        w = pp["fii_idx_fut_long_pct"].dropna()
        w = w[w.index >= w.index[-1] - pd.DateOffset(years=3)].resample("W-FRI").last().dropna()
        rows += [{"table": "fii", "week": str(d.date()), "fii_long_pct": round(float(v), 1)} for d, v in w.items()]

    # headline
    n_ideas = len(li.get("ideas", []))
    mood = f"{reg.get('trend', '?')}, {reg.get('fear', '?')} market" if reg else "market"
    take = (f"{n_ideas} trade idea{'s' if n_ideas != 1 else ''} from the latest {li.get('source', 'scan')} in a {mood}. "
            + ("Strategy is NOT validated (aggressive mode): keep each trade at the size shown."
               if s.get("tips_mode") == "aggressive" else ""))
    rows.append({"table": "headline", "updated": f"{pd.Timestamp.now(tz='Asia/Kolkata'):%d %b %Y, %I:%M %p} IST", "takeaway": take,
                 "strategy": name, "ideas_at": str(li.get("at") or "")[:16]})
    OUT.write_text(json.dumps(rows, default=str))
    return OUT, len(rows)
