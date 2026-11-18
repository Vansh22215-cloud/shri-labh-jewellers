"""Round 23 (IMPROVE23_PREREGISTRATION.md): the liquidity floor under attack."""
import json
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, "/home/user/shri-labh-jewellers/vantage-ai/validation")
import improve as im  # noqa: E402
from improve import HERE, OOS  # noqa: E402
from improve10 import sim, load  # noqa: E402

T = load("improve_trades_U2.csv").reset_index(drop=True)
turn = {}
for s, d, m, src in im.all_stocks():
    if s in set(T["sym"]):
        turn[s] = (d["raw_close"] * d["volume"]).rolling(20).mean()
T["turn_cr"] = [float(turn[s].get(day, np.nan)) / 1e7 if s in turn else np.nan for s, day in zip(T["sym"], T["signal"])]
out = {"share_with_turnover": round(float(T["turn_cr"].notna().mean()), 3)}
for p in ("dev", "holdout", "all_years"):
    S = T[T["signal"] < OOS] if p == "dev" else T[T["signal"] >= OOS] if p == "holdout" else T
    res = {}
    for name, f in (("L0", 0), ("L1", 1), ("L2", 2), ("L3", 3), ("L5", 5)):
        X = S[(S["turn_cr"] >= f) | (f == 0)]
        R = [sim(X, s) for s in range(15)]
        res[name] = {k: round(float(np.median([r[k] for r in R])), 1) for k in ("cagr", "maxdd", "per_week")}
        res[name]["signals"] = int(len(X))
    out[p] = res
    print(p, res, flush=True)
L2 = {p: out[p]["L2"]["cagr"] for p in ("dev", "holdout")}
out["ROBUST"] = bool(all(abs(out[p][k]["cagr"] - L2[p]) <= 2 for p in ("dev", "holdout") for k in ("L1", "L3", "L5"))
                     and out["holdout"]["L0"]["cagr"] <= L2["holdout"])
json.dump(out, open(f"{HERE}/improve23_results.json", "w"), indent=1)
print("ROBUST", out["ROBUST"])
