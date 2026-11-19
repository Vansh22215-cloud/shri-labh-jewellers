"""Round 27 (IMPROVE27_PREREGISTRATION.md): universe size robustness."""
import json
import numpy as np
import pandas as pd
from improve import HERE, OOS, iv
import autoresearch as ar
from improve25 import sim

out = {}
for N in (100, 200, 300, 400, 500):
    T = ar._trades(list(iv.universe(include_delisted=True, top=N)))
    T = T[(T["entry"] > T["init_stop"]) & (T["entry"] > 0)]
    row = {"trades": len(T)}
    for nm, S in (("dev", T[T["signal"] < OOS]), ("holdout", T[T["signal"] >= OOS])):
        for mode in ("fixed", "monthly"):
            R = [sim(S, s, mode) for s in range(15)]
            row[f"{nm} {mode}"] = (round(float(np.median([a for a, b, c in R])), 1), round(float(np.median([b for a, b, c in R])), 1))
    yr = {}
    for y in range(2013, 2027):
        Y = T[T["signal"].dt.year == y]
        if len(Y) >= 30:
            yr[y] = round(float(np.median([sim(Y, s)[0] for s in range(7)])), 1)
    row["years"] = yr
    out[N] = row
    print(N, {k: v for k, v in row.items() if k != "years"}, flush=True)
h = {N: out[N]["holdout fixed"][0] for N in out}
out["ROBUST"] = abs(h[200] - h[300]) <= 2 and abs(h[400] - h[300]) <= 2 and h[200] > 7.2 and h[400] > 7.2
print("holdout", h, "ROBUST", out["ROBUST"])
json.dump(out, open(f"{HERE}/improve27_results.json", "w"), indent=1, default=str)
