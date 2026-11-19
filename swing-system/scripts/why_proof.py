"""Proof run of the why-engine (19 Nov 2026): the last months of real 13-year-test trades (top-300, closed) are treated
as if they were live tips. They are removed from the history first, so the engine judges them blind.
-> journal/why_proof.md (+ .csv); its leads go to data/why_proof_leads.json, never to the live leads file."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np
import pandas as pd
from swing import why_engine as we, data_prices, learning

if __name__ == "__main__":
    start = sys.argv[1] if len(sys.argv) > 1 else "2026-06-01"
    we.LOG_CSV, we.LOG_MD = we.ROOT / "journal" / "why_proof.csv", we.ROOT / "journal" / "why_proof.md"
    we.LEADS_F = we.DATA / "why_proof_leads.json"
    if we.LEADS_F.exists():
        we.LEADS_F.unlink()
    H = we.history()
    demo = H[H["signal"] >= start].copy()
    we._H["h"] = H[H["signal"] < start]
    c = data_prices.benchmark()["close"]
    load = data_prices.load
    def nif(a, b):
        x = c[(c.index >= a) & (c.index <= b)]
        return float((x.iloc[-1] / x.iloc[0] - 1) * 100) if len(x) > 1 else 0.0
    R = pd.DataFrame({"source": "VANTAGE", "type": "VANTAGE " + demo["setup"].replace({"RCP": "Rolling Candle Profile"}),
                      "symbol": demo["sym"], "date": demo["signal"].dt.date.astype(str), "status": "closed",
                      "why": demo["why"], "entry": demo["entry"], "stop": demo["init_stop"],
                      "result_pct": (demo["net"] * 100).round(2), "days": demo["days"], "market": demo["mkt_trend"],
                      "results_week": demo["results_soon"], "entry_date": demo["entry_date"].astype(str),
                      "exit_date": pd.to_datetime(demo["exit_date"]).dt.date.astype(str),
                      "nifty_same_days_pct": [nif(a, b) for a, b in zip(demo["entry_date"], pd.to_datetime(demo["exit_date"]))]},
                     index=demo.index)
    R["vs_nifty_pct"] = R["result_pct"] - R["nifty_same_days_pct"]
    R["exit"] = demo["exit"]
    best = []
    for _, r in R.iterrows():                      # best close during the trade (adjusted prices, like the test)
        d = load(r["symbol"])
        try:
            a = d["adj_close"] if "adj_close" in d else d["close"]
            w = a[(a.index > pd.Timestamp(r["entry_date"])) & (a.index <= pd.Timestamp(r["exit_date"]))]
            best.append(round(float((w.max() / r["entry"] - 1) * 100), 2) if len(w) else np.nan)
        except Exception:
            best.append(np.nan)
    R["best_pct"] = best
    # the Learner's own diagnosis of every loser (same code as live)
    codes = []
    for _, r in R.iterrows():
        try:
            codes.append(learning.diagnose(r, load) if r["result_pct"] <= 0 else "")
        except Exception:
            codes.append("")
    R["mistake"] = [x if isinstance(x, str) else (x[0] if x else "") for x in codes]
    facts = demo.to_dict("index")
    R["_i"] = R.index
    W = we.explain(R, facts=lambda r: facts[r["_i"]])
    we.write(W, title=f"Why-engine PROOF RUN on real test trades signalled since {start} (judged blind)")
    print(len(W), W["surprise"].str.split(" \\(").str[0].value_counts().to_dict())
