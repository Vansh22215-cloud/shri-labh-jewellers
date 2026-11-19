"""Round 23b: no liquidity floor, but thin stocks (< Rs 2 cr/day) pay an extra 1% (0.5% worse buy + 0.5% worse sell)
for wider spreads - is the live floor justified by execution cost? Same sim, data and seeds as round 23."""
import json
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import improve as im  # noqa: E402
from improve import HERE, OOS  # noqa: E402
from improve10 import sim, load  # noqa: E402

T = load("improve_trades_U2.csv").reset_index(drop=True)
turn = {}
for s, d, m, src in im.all_stocks():
    if s in set(T["sym"]):
        turn[s] = (d["raw_close"] * d["volume"]).rolling(20).mean()
T["turn_cr"] = [float(turn[s].get(day, np.nan)) / 1e7 if s in turn else np.nan for s, day in zip(T["sym"], T["signal"])]
thin = T["turn_cr"] < 2
X = T.copy()
X.loc[thin, "entry"] *= 1.005
X.loc[thin, "exit"] *= 0.995
X = X[X["entry"] > X["init_stop"]]
out = {}
for p in ("dev", "holdout", "all_years"):
    f = (lambda D: D[D["signal"] < OOS]) if p == "dev" else (lambda D: D[D["signal"] >= OOS]) if p == "holdout" else (lambda D: D)
    res = {}
    for name, S in (("floor_2cr", f(T[~thin])), ("no_floor_plus_1pct_thin_cost", f(X))):
        R = [sim(S, s) for s in range(15)]
        res[name] = {k: round(float(np.median([r[k] for r in R])), 1) for k in ("cagr", "maxdd", "per_week")}
    out[p] = res
    print(p, res, flush=True)
json.dump(out, open(f"{HERE}/improve23b_results.json", "w"), indent=1)
