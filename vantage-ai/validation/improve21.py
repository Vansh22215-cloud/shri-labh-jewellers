"""Round 21 (IMPROVE21_PREREGISTRATION.md): stress test of the live setup with Rs 51,000."""
import json
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from improve import HERE, OOS  # noqa: E402

P = pd.read_csv(f"{HERE}/recycle_paths.csv", parse_dates=["signal", "entry_date", "exit_date", "od15"])


def load(f):
    T = pd.read_csv(f"{HERE}/{f}", parse_dates=["signal", "entry_date", "exit_date"])
    return T[(T["entry"] > T["init_stop"]) & (T["entry"] > 0)]


def with_adds(T):
    x = P[(P["set"] == "top300") & (P["c15"] >= 0.08)].dropna(subset=["o15"])
    x = x.merge(T[T["setup"] == "RCP"][["sym", "signal", "init_stop"]], on=["sym", "signal"])
    add = pd.DataFrame({"sym": x["sym"], "signal": x["signal"], "entry_date": x["od15"], "exit_date": x["exit_date"],
                        "entry": x["o15"], "exit": x["exit"], "init_stop": x["init_stop"], "setup": "RCP-add"})
    return pd.concat([T, add], ignore_index=True)


def sim(T, seed, cost=0.0035, slip=0.0, miss=0.0, cap0=51000, risk=0.01, maxpct=0.25):
    rng = np.random.default_rng(seed)
    T = T.assign(rnd=rng.random(len(T)), keep=rng.random(len(T)) >= miss)
    T = T[T["keep"]].sort_values(["entry_date", "rnd"])
    half = cost / 2
    cash, eq, opn, hist = cap0, cap0, [], []
    for r in T.itertuples():
        keep = []
        for (xd, pe, px, q) in opn:
            if xd <= r.entry_date:
                cash += q * px * (1 - half)
                eq += q * (px - pe) - q * (pe + px) * half
                hist.append((xd, eq))
            else:
                keep.append((xd, pe, px, q))
        opn = keep
        e = r.entry * (1 + slip)
        if e <= r.init_stop:
            continue
        q = min(int(cap0 * risk // (e - r.init_stop)), int(cap0 * maxpct // e))
        if q < 1 or q * e * (1 + half) > cash:
            continue
        cash -= q * e * (1 + half)
        opn.append((r.exit_date, e, r.exit, q))
    for (xd, pe, px, q) in opn:
        eq += q * (px - pe) - q * (pe + px) * half
        hist.append((xd, eq))
    H = pd.Series([v for _, v in sorted(hist)], index=[d for d, _ in sorted(hist)]).groupby(level=0).last()
    yrs = (T["entry_date"].max() - T["entry_date"].min()).days / 365.25
    return ((eq / cap0) ** (1 / yrs) - 1) * 100, float((H / H.cummax() - 1).min() * 100)


SETUPS = {"B": load("trades_FINAL.csv"), "C": load("improve3_trades_C1.csv")}
SETUPS["C+A"] = with_adds(SETUPS["C"])
STRESS = {"S0 normal": {}, "S1 costs 0.6%": {"cost": 0.006}, "S2 buys 0.3% worse": {"slip": 0.003},
          "S3 30% of tips missed": {"miss": 0.3}, "S4 all three": {"cost": 0.006, "slip": 0.003, "miss": 0.3}}
if __name__ == "__main__":
    out, flags = {}, []
    for per in ("holdout", "dev"):
        out[per] = {}
        for sname, kw in STRESS.items():
            row = {}
            for k, T in SETUPS.items():
                S = T[T["signal"] >= OOS] if per == "holdout" else T[T["signal"] < OOS]
                R = [sim(S, s, **kw) for s in range(15)]
                row[k] = {"cagr": round(float(np.median([a for a, b in R])), 1), "maxdd": round(float(np.median([b for a, b in R])), 1)}
            out[per][sname] = row
            for k in ("C", "C+A"):
                if row[k]["cagr"] < row["B"]["cagr"]:
                    flags.append(f"{per} {sname}: {k} below B")
            print(per, sname, row, flush=True)
    out["flags"] = flags
    json.dump(out, open(f"{HERE}/improve21_results.json", "w"), indent=1)
    print("FLAGS:", flags)
