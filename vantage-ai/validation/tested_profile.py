"""What a VANTAGE tip of each type is EXPECTED to do, from the 13-year test (holdout Nov 2023+ = the most recent
behaviour, development for reference). Used by swing/learning.py to judge the live record.
-> tested_profile.json {type: {n, win_pct, avg_pct, sd_pct, median_days, mfe_med, mae_med, mae_p90, stop_rate}}"""
import json
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, "/home/user/shri-labh-jewellers/vantage-ai/validation")
from improve import iv, OOS, COST  # noqa: E402

T = pd.read_csv("trades_FINAL.csv", parse_dates=["signal", "entry_date", "exit_date"])
data = {s: d for s, d, m, src in iv.universe(include_delisted=True)}
mfe, mae = [], []
for t in T.itertuples():
    d = data.get(t.sym)
    if d is None or t.entry_date not in d.index:
        mfe.append(np.nan); mae.append(np.nan); continue
    w = d.loc[t.entry_date:t.exit_date]
    mfe.append(w["high"].max() / t.entry - 1); mae.append(w["low"].min() / t.entry - 1)
T["mfe"], T["mae"] = mfe, mae
T["net"] = T["exit"] / T["entry"] - 1 - COST
T["days_td"] = T["days"]
T["kind"] = np.where(T["setup"] == "Dip-buy", "Dip-buy " + T["tier"].fillna(""), T["setup"])
out = {}
for per, m in (("holdout", T["signal"] >= OOS), ("development", T["signal"] < OOS)):
    out[per] = {}
    for k, g in T[m].groupby("kind"):
        out[per][k] = {"n": int(len(g)), "win_pct": round(float((g.net > 0).mean() * 100), 1),
                       "avg_pct": round(float(g.net.mean() * 100), 2), "sd_pct": round(float(g.net.std() * 100), 2),
                       "median_days": float(g.days_td.median()), "mfe_med": round(float(g.mfe.median() * 100), 2),
                       "mae_med": round(float(g.mae.median() * 100), 2), "mae_p90": round(float(g.mae.quantile(0.1) * 100), 2),
                       "stop_rate": round(float(g.why.astype(str).str.contains("Stop").mean() * 100), 1)}
json.dump(out, open("tested_profile.json", "w"), indent=1)
print(json.dumps(out["holdout"], indent=1))
