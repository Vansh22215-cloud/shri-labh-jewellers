"""Round 26 (IMPROVE26_PREREGISTRATION.md): VANTAGE universe - top-300 vs all stocks >= Rs 2 cr/day vs mix."""
import json
import numpy as np
import pandas as pd
from improve import HERE, OOS
import improve21 as r21
from improve25 import sim

X = pd.read_csv(f"{HERE}/lab_features.csv.gz", usecols=["set", "sym", "signal", "turnover_cr"], parse_dates=["signal"])
top = set(map(tuple, X[X["set"] == "top300"][["sym", "signal"]].astype(str).values))
U = r21.load("improve_trades_U2.csv")
tv = X[X["set"] == "all"].drop_duplicates(["sym", "signal"]).set_index(["sym", "signal"])["turnover_cr"]
U = U.join(tv, on=["sym", "signal"])
U = U[U["turnover_cr"] >= 2].copy()
U["in300"] = [(s, str(d)) for s, d in zip(U["sym"], U["signal"].astype(str))]
U["in300"] = U["in300"].isin(top)
B = r21.SETUPS["B"]


def run(T, mode, mix=False, seeds=15):
    R = []
    for s in range(seeds):
        T2 = T
        if mix:   # top-300 first among same-day entries: shift their random key below every other
            rng = np.random.default_rng(1000 + s)
            T2 = T.assign(entry_date=T["entry_date"]) 
        R.append(sim_mix(T2, s, mode) if mix else sim(T2, s, mode))
    return round(float(np.median([a for a, b, c in R])), 1), round(float(np.median([b for a, b, c in R])), 1)


def sim_mix(T, seed, mode):
    # same simulation, order within a day: top-300 first, then random
    rng = np.random.default_rng(seed)
    T = T.assign(rnd=rng.random(len(T)) + (~T["in300"]).astype(float))
    import improve25 as m
    orig = np.random.default_rng
    class R:   # make sim's own random key reuse ours
        def __init__(self, *_): pass
        def random(self, n): return T["rnd"].values
    m.np.random.default_rng = R
    try:
        return m.sim(T, seed, mode)
    finally:
        m.np.random.default_rng = orig


out = {"per_year": {}, "periods": {}}
for mode in ("fixed", "current"):
    for nm, f in (("dev", lambda T: T[T["signal"] < OOS]), ("holdout", lambda T: T[T["signal"] >= OOS]),
                  ("all years", lambda T: T)):
        out["periods"][f"{nm} {mode}"] = {"U-300": run(f(B), mode), "U-all": run(f(U), mode),
                                          "U-mix": run(f(U), mode, mix=True)}
        print(nm, mode, out["periods"][f"{nm} {mode}"], flush=True)
for y in range(2013, 2027):
    f = lambda T: T[T["signal"].dt.year == y]
    out["per_year"][y] = {"U-300": run(f(B), "fixed", seeds=7), "U-all": run(f(U), "fixed", seeds=7),
                          "U-mix": run(f(U), "fixed", mix=True, seeds=7)}
    print(y, out["per_year"][y], flush=True)
json.dump(out, open(f"{HERE}/improve26_results.json", "w"), indent=1)
