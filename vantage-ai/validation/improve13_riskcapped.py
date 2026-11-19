"""Round 13 (IMPROVE13_PREREGISTRATION.md): pyramiding winning trend trades."""
import json
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from improve import HERE, OOS  # noqa: E402
from improve10 import sim  # noqa: E402

P = pd.read_csv(f"{HERE}/recycle_paths.csv", parse_dates=["signal", "entry_date", "exit_date", "od15"])
out, ok = {}, True
for st, f in (("top300", "trades_FINAL.csv"), ("all", "improve_trades_U.csv")):
    T = pd.read_csv(f"{HERE}/{f}", parse_dates=["signal", "entry_date", "exit_date"])
    T = T[(T["entry"] > T["init_stop"]) & (T["entry"] > 0)]
    x = P[(P["set"] == st) & (P["c15"] >= 0.08)].dropna(subset=["o15"])
    orig = T[T["setup"] == "RCP"][["sym", "entry_date", "entry", "init_stop"]]
    x = x.merge(orig, on=["sym", "entry_date", "entry"], how="inner")
    stop_pct = (x["entry"] - x["init_stop"]) / x["entry"]
    add = pd.DataFrame({"sym": x["sym"], "signal": x["signal"], "entry_date": x["od15"], "exit_date": x["exit_date"],
                        "entry": x["o15"], "exit": x["exit"], "init_stop": x["init_stop"], "setup": "RCP-add"})
    A = pd.concat([T, add], ignore_index=True)
    out[st] = {"add_ons": int(len(add))}
    for p in ("dev", "holdout"):
        m0 = T["signal"] < OOS if p == "dev" else T["signal"] >= OOS
        m1 = A["signal"] < OOS if p == "dev" else A["signal"] >= OOS
        r0 = [sim(T[m0], s) for s in range(15)]
        r1 = [sim(A[m1], s) for s in range(15)]
        a = {k: round(float(np.median([z[k] for z in r0])), 1) for k in ("cagr", "maxdd", "per_week")}
        b = {k: round(float(np.median([z[k] for z in r1])), 1) for k in ("cagr", "maxdd", "per_week")}
        out[st][p] = {"today": a, "with_add_ons": b}
        ok &= b["cagr"] >= a["cagr"] + 1.0 and b["maxdd"] >= a["maxdd"] - 2.0
        print(st, p, out[st][p], flush=True)
out["PASS"] = bool(ok)
json.dump(out, open(f"{HERE}/improve13_results_riskcapped.json", "w"), indent=1)
print("PASS", ok)
