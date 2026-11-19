"""Round 17 (IMPROVE17_PREREGISTRATION.md)."""
import json
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from improve import HERE, OOS  # noqa: E402
from improve10 import sim  # noqa: E402

P = pd.read_csv(f"{HERE}/recycle_paths.csv", parse_dates=["signal", "entry_date", "exit_date", "od15", "od30"])


def adds(T, st, day, thr, need=None):
    orig = T[T["setup"] == "RCP"][["sym", "entry_date", "entry", "init_stop"]]
    x = P[(P["set"] == st) & (P[f"c{day}"] >= thr)].dropna(subset=[f"o{day}"])
    if need is not None:
        x = x[x[need[0]] >= need[1]]
    x = x.merge(orig, on=["sym", "entry_date", "entry"])
    return pd.DataFrame({"sym": x["sym"], "signal": x["signal"], "entry_date": x[f"od{day}"], "exit_date": x["exit_date"],
                         "entry": x[f"o{day}"], "exit": x["exit"], "init_stop": x["init_stop"], "setup": f"RCP-add{day}"})


out, ok = {}, True
for st, f in (("top300", "trades_FINAL.csv"), ("all", "improve_trades_U.csv")):
    T = pd.read_csv(f"{HERE}/{f}", parse_dates=["signal", "entry_date", "exit_date"])
    T = T[(T["entry"] > T["init_stop"]) & (T["entry"] > 0)]
    a15 = adds(T, st, 15, 0.08)
    a30 = adds(T, st, 30, 0.15, need=("c15", 0.08))
    base, p2 = pd.concat([T, a15], ignore_index=True), pd.concat([T, a15, a30], ignore_index=True)
    out[st] = {"third_lots": int(len(a30))}
    for p in ("dev", "holdout"):
        res = {}
        for name, S in (("base_live", base), ("P2", p2)):
            m = S["signal"] < OOS if p == "dev" else S["signal"] >= OOS
            R = [sim(S[m], s) for s in range(15)]
            res[name] = {k: round(float(np.median([r[k] for r in R])), 1) for k in ("cagr", "maxdd")}
        ok &= res["P2"]["cagr"] >= res["base_live"]["cagr"] + 1.0 and res["P2"]["maxdd"] >= res["base_live"]["maxdd"] - 2.0
        out[st][p] = res
        print(st, p, res, flush=True)
out["PASS"] = bool(ok)
json.dump(out, open(f"{HERE}/improve17_results.json", "w"), indent=1)
print("PASS", ok)
