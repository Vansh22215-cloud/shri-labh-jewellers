"""Round 14 (IMPROVE14_PREREGISTRATION.md)."""
import json
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from improve import HERE, OOS  # noqa: E402
import improve10  # noqa: E402

A = pd.read_csv(f"{HERE}/champ_features.csv", parse_dates=["signal", "entry_date", "exit_date"])
A = A[(A["entry"] > A["init_stop"]) & (A["entry"] > 0)]
A["rs"] = A["rs"].fillna(0.5)


def sim_order(T, seed, leaders):
    rng = np.random.default_rng(seed)
    T = T.assign(rnd=rng.random(len(T)))
    T = T.sort_values(["entry_date", "rs", "rnd"], ascending=[True, False, True]) if leaders else T.sort_values(["entry_date", "rnd"])
    # improve10.sim re-sorts by (entry_date, rnd): give rnd the wanted order inside each day
    T = T.assign(rnd=np.arange(len(T)) / len(T))
    orig = np.random.default_rng
    class R:                                                     # make improve10.sim keep our order
        def __init__(self, *a): pass
        def random(self, n): return T["rnd"].values
    improve10.np.random.default_rng = R
    try:
        return improve10.sim(T.drop(columns="rnd"), seed)
    finally:
        improve10.np.random.default_rng = orig


out, ok = {}, {"S1": True, "S2": True, "S3": True}
for st in ("top300", "all"):
    X = A[A["set"] == st]
    vol_ok = ~((X["setup"] == "Breakout") & ~(X["vol_ratio"] >= 3))
    out[st] = {}
    for p in ("dev", "holdout"):
        m = X["signal"] < OOS if p == "dev" else X["signal"] >= OOS
        res = {}
        for name, T, lead in (("today", X[m], False), ("S1", X[m], True), ("S2", X[m & vol_ok], False), ("S3", X[m & vol_ok], True)):
            R = [sim_order(T, s, lead) for s in range(15)]
            res[name] = {k: round(float(np.median([r[k] for r in R])), 1) for k in ("cagr", "maxdd", "per_week")}
        out[st][p] = res
        for k in ("S1", "S2", "S3"):
            ok[k] &= res[k]["cagr"] >= res["today"]["cagr"] + 1.0 and res[k]["maxdd"] >= res["today"]["maxdd"] - 2.0
        print(st, p, res, flush=True)
out.update({k + "_PASS": bool(v) for k, v in ok.items()})
json.dump(out, open(f"{HERE}/improve14_results.json", "w"), indent=1)
print({k: v for k, v in out.items() if k.endswith("PASS")})
