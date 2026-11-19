"""Round 29 (IMPROVE29_PREREGISTRATION.md): VANTAGE and the live dip-buy share the money - which first?"""
import json
import os
import numpy as np
import pandas as pd
import improve21 as r21
from improve import HERE, OOS, SW
from improve28 import sim

V = r21.SETUPS["C+A"][["sym", "signal", "entry_date", "exit_date", "entry", "exit", "init_stop"]].assign(src_="V")
D = pd.read_csv(os.path.join(SW, "validation", "independent_trades_DIP.csv"), parse_dates=["signal", "entry_date", "exit_date"])
D = D.assign(init_stop=D["entry"] * (1 - D["stop_pct"]), src_="D")[["sym", "signal", "entry_date", "exit_date", "entry", "exit", "init_stop", "src_"]]
B = pd.concat([V, D], ignore_index=True)
B["dipfirst"], B["vfirst"] = (B["src_"] == "D").astype(float), (B["src_"] == "V").astype(float)
print("trades V", len(V), "D", len(D), flush=True)


def _main():
    def med(S, prio, seeds=15):
        R = [sim(S, s, prio) for s in range(seeds)]
        return round(float(np.median([a for a, b in R])), 1), round(float(np.median([b for a, b in R])), 1)


    cases = {"A0 VANTAGE alone": (V, None), "A1 both, random order (now)": (B, None),
             "A2 both, dip-buys first": (B, "dipfirst"), "A3 both, VANTAGE first": (B, "vfirst")}
    out = {}
    for k, (T, pr) in cases.items():
        row = {"dev": med(T[T["signal"] < OOS], pr), "holdout": med(T[T["signal"] >= OOS], pr)}
        row["years"] = {y: med(T[T["signal"].dt.year == y], pr, 7)[0] for y in range(2013, 2027) if (T["signal"].dt.year == y).sum() > 30}
        out[k] = row
        print(k, row["dev"], row["holdout"], flush=True)
    b = out["A1 both, random order (now)"]
    for k in ("A2 both, dip-buys first", "A3 both, VANTAGE first"):
        r = out[k]
        yb = sum(r["years"][y] >= b["years"][y] for y in r["years"])
        r["years_better"] = f"{yb} of {len(r['years'])}"
        r["PASS"] = all(r[p][0] >= b[p][0] + 1 and r[p][1] >= b[p][1] - 2 for p in ("dev", "holdout")) and yb >= 0.6 * len(r["years"])
        print(k, r["years_better"], "PASS" if r["PASS"] else "fail")
    json.dump(out, open(f"{HERE}/improve29_results.json", "w"), indent=1, default=str)



if __name__ == "__main__":
    _main()