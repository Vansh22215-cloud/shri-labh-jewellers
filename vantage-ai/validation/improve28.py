"""Round 28 (IMPROVE28_PREREGISTRATION.md): order of same-day tips when money is short, live setup C+A top-300."""
import heapq
import json
import numpy as np
import pandas as pd
import improve21 as r21
from improve import HERE, OOS

HC = 0.00175
C = r21.SETUPS["C+A"].copy()
F = pd.read_csv(f"{HERE}/lab_features.csv.gz", usecols=["set", "sym", "signal", "ret_6m", "from_52w_high", "atr_pct"],
                parse_dates=["signal"])
F = F[F["set"] == "top300"].drop_duplicates(["sym", "signal"]).drop(columns="set")
C = C.merge(F, on=["sym", "signal"], how="left")
C["score"] = pd.to_numeric(C["score"], errors="coerce")
day_pct = lambda c: C.groupby("entry_date")[c].rank(pct=True)
C["P1"] = C["ret_6m"]
C["P2"] = C["from_52w_high"]
C["P3"] = -C["atr_pct"]
C["P4"] = C["score"]
C["P5"] = (day_pct("ret_6m") + day_pct("from_52w_high")) / 2
print("feature coverage", C[["P1", "P2", "P3", "P4", "P5"]].notna().mean().round(3).to_dict(), flush=True)


def sim(T, seed, prio=None, mode="fixed", cap0=51000, risk=0.01, maxpct=0.25):
    rng = np.random.default_rng(seed)
    p = T[prio].fillna(T[prio].median()) if prio else 0.0
    T = T.assign(rnd=rng.random(len(T)), pr=-p if prio else 0.0).sort_values(["entry_date", "pr", "rnd"])
    cash, eq, opn, hist, n, base, month = float(cap0), float(cap0), [], [], 0, float(cap0), None
    for r in T.itertuples():
        ed = r.entry_date
        while opn and opn[0][0] <= ed:
            xd, _, pe, px, q = heapq.heappop(opn)
            cash += q * px * (1 - HC)
            eq += q * (px - pe) - q * (pe + px) * HC
            hist.append((xd, eq))
        if mode == "monthly" and (ed.year, ed.month) != month:
            month, base = (ed.year, ed.month), cash + sum(o[2] * o[4] for o in opn)
        e = r.entry
        if e <= r.init_stop:
            continue
        q = min(int(base * risk // (e - r.init_stop)), int(base * maxpct // e))
        if q < 1 or q * e * (1 + HC) > cash:
            continue
        cash -= q * e * (1 + HC)
        n += 1
        heapq.heappush(opn, (r.exit_date, n, e, r.exit, q))
    while opn:
        xd, _, pe, px, q = heapq.heappop(opn)
        eq += q * (px - pe) - q * (pe + px) * HC
        hist.append((xd, eq))
    hist.sort()
    v = np.array([x[1] for x in hist])
    yrs = (T["entry_date"].max() - T["entry_date"].min()).days / 365.25
    return ((eq / cap0) ** (1 / yrs) - 1) * 100, float((v / np.maximum.accumulate(v) - 1).min() * 100)


def med(S, prio, mode="fixed", seeds=15):
    R = [sim(S, s, prio, mode) for s in range(seeds)]
    return round(float(np.median([a for a, b in R])), 1), round(float(np.median([b for a, b in R])), 1)


if __name__ == "__main__":
    out = {}
    for prio in (None, "P1", "P2", "P3", "P4", "P5"):
        k = prio or "random (now)"
        row = {}
        for nm, S in (("dev", C[C["signal"] < OOS]), ("holdout", C[C["signal"] >= OOS])):
            row[f"{nm} fixed"], row[f"{nm} monthly"] = med(S, prio), med(S, prio, "monthly")
        row["years"] = {y: med(C[C["signal"].dt.year == y], prio, seeds=7)[0] for y in range(2013, 2027)}
        out[k] = row
        print(k, {a: b for a, b in row.items() if a != "years"}, flush=True)
    b = out["random (now)"]
    for k in ("P1", "P2", "P3", "P4", "P5"):
        r = out[k]
        yrs = sum(r["years"][y] >= b["years"][y] for y in r["years"])
        r["years_better"] = f"{yrs} of {len(r['years'])}"
        r["PASS"] = all(r[f"{p} fixed"][0] >= b[f"{p} fixed"][0] + 1 and r[f"{p} fixed"][1] >= b[f"{p} fixed"][1] - 2
                        for p in ("dev", "holdout")) and yrs >= 0.6 * len(r["years"])
        print(k, r["years_better"], "PASS" if r["PASS"] else "fail")
    json.dump(out, open(f"{HERE}/improve28_results.json", "w"), indent=1, default=str)
