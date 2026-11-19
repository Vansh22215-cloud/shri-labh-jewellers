"""Post-hoc robustness of P1 (not used to choose the rule): nearby triggers + share of paired runs where P1 wins."""
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from improve import HERE, OOS  # noqa: E402
from improve10 import sim  # noqa: E402

P = pd.read_csv(f"{HERE}/recycle_paths.csv", parse_dates=["signal", "entry_date", "exit_date", "od10", "od15", "od20"])
for st, f in (("top300", "trades_FINAL.csv"), ("all", "improve_trades_U.csv")):
    T = pd.read_csv(f"{HERE}/{f}", parse_dates=["signal", "entry_date", "exit_date"])
    T = T[(T["entry"] > T["init_stop"]) & (T["entry"] > 0)]
    orig = T[T["setup"] == "RCP"][["sym", "entry_date", "entry", "init_stop"]]
    for day, thr in ((15, 0.08), (10, 0.08), (20, 0.08), (15, 0.05), (15, 0.12)):
        x = P[(P["set"] == st) & (P[f"c{day}"] >= thr)].dropna(subset=[f"o{day}"]).merge(orig, on=["sym", "entry_date", "entry"])
        sp = (x["entry"] - x["init_stop"]) / x["entry"]
        add = pd.DataFrame({"sym": x["sym"], "signal": x["signal"], "entry_date": x[f"od{day}"], "exit_date": x["exit_date"],
                            "entry": x[f"o{day}"], "exit": x["exit"], "init_stop": x[f"o{day}"] * (1 - sp), "setup": "RCP-add"})
        A = pd.concat([T, add], ignore_index=True)
        line = []
        for p in ("dev", "holdout"):
            m0 = T["signal"] < OOS if p == "dev" else T["signal"] >= OOS
            m1 = A["signal"] < OOS if p == "dev" else A["signal"] >= OOS
            r0 = [sim(T[m0], s)["cagr"] for s in range(15)]
            r1 = [sim(A[m1], s)["cagr"] for s in range(15)]
            line.append(f"{p}: +{np.median(r1) - np.median(r0):.1f} pts, wins {np.mean(np.array(r1) > np.array(r0)) * 100:.0f}% of runs")
        print(st, f"day {day} >= {thr:.0%}:", " | ".join(line), flush=True)
