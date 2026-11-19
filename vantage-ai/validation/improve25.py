"""Round 25 (IMPROVE25_PREREGISTRATION.md): compounding - size on the account's current value."""
import heapq
import json
import numpy as np
import pandas as pd
import improve21 as r21
from improve import HERE, OOS

HC = 0.00175


def sim(T, seed, mode="fixed", cap0=51000, risk=0.01, maxpct=0.25):
    rng = np.random.default_rng(seed)
    T = T.assign(rnd=rng.random(len(T))).sort_values(["entry_date", "rnd"])
    cash, eq, opn, hist, n = float(cap0), float(cap0), [], [], 0
    base, month = float(cap0), None
    for r in T.itertuples():
        ed = r.entry_date
        while opn and opn[0][0] <= ed:
            xd, _, pe, px, q = heapq.heappop(opn)
            cash += q * px * (1 - HC)
            eq += q * (px - pe) - q * (pe + px) * HC
            hist.append((xd, eq))
        if mode == "current":
            base = cash + sum(o[2] * o[4] for o in opn)
        elif mode == "monthly" and (ed.year, ed.month) != month:
            month, base = (ed.year, ed.month), cash + sum(o[2] * o[4] for o in opn)
        e = r.entry
        if e <= r.init_stop:
            continue
        q = min(int(base * risk // (e - r.init_stop)), int(base * maxpct // e))
        need = q * e * (1 + HC)
        if q < 1 or need > cash:
            continue
        cash -= need
        n += 1
        heapq.heappush(opn, (r.exit_date, n, e, r.exit, q))
    while opn:
        xd, _, pe, px, q = heapq.heappop(opn)
        eq += q * (px - pe) - q * (pe + px) * HC
        hist.append((xd, eq))
    hist.sort()
    v = np.array([x[1] for x in hist])
    yrs = (T["entry_date"].max() - T["entry_date"].min()).days / 365.25
    return ((eq / cap0) ** (1 / yrs) - 1) * 100, float((v / np.maximum.accumulate(v) - 1).min() * 100), eq


if __name__ == "__main__":
    SETS = {"B top300": r21.SETUPS["B"], "C+A top300 (live)": r21.SETUPS["C+A"], "all stocks": r21.load("improve_trades_U2.csv")}
    out = {}
    for per in ("dev", "holdout"):
        out[per] = {}
        for k, T in SETS.items():
            S = T[T["signal"] >= OOS] if per == "holdout" else T[T["signal"] < OOS]
            row = {}
            for mode in ("fixed", "current", "monthly"):
                R = [sim(S, s, mode) for s in range(15)]
                row[mode] = {"cagr": round(float(np.median([a for a, b, c in R])), 1),
                             "maxdd": round(float(np.median([b for a, b, c in R])), 1),
                             "rupees_end": int(np.median([c for a, b, c in R]))}
            out[per][k] = row
            print(per, k, row, flush=True)
    P = {}
    for mode in ("current", "monthly"):
        P[mode] = all(out[p][k][mode]["cagr"] >= out[p][k]["fixed"]["cagr"] + 1 and
                      out[p][k][mode]["maxdd"] >= out[p][k]["fixed"]["maxdd"] - 2
                      for p in out for k in ("C+A top300 (live)", "all stocks"))
    out["PASS"] = P
    print("PASS", P)
    json.dump(out, open(f"{HERE}/improve25_results.json", "w"), indent=1)
