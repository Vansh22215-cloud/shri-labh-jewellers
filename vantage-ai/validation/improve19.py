"""Round 19 (IMPROVE19_PREREGISTRATION.md): sector cap."""
import json
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from improve import HERE, OOS, SW  # noqa: E402
from improve10 import load  # noqa: E402

SEC = pd.read_csv(f"{SW}/data/events/nifty500.csv")
SMAP = dict(zip(SEC["Symbol"].astype(str), SEC["Industry"].astype(str)))


def sim(T, seed, cap=None, cap0=45000, risk=0.01, maxpct=0.25):
    rng = np.random.default_rng(seed)
    T = T.assign(rnd=rng.random(len(T))).sort_values(["entry_date", "rnd"])
    cash, eq, opn, hist, n = cap0, cap0, [], [], 0
    for r in T.itertuples():
        keep = []
        for (xd, pe, px, q, sec) in opn:
            if xd <= r.entry_date:
                cash += q * px * (1 - 0.00175)
                eq += q * (px - pe) - q * (pe + px) * 0.00175
                hist.append((xd, eq))
            else:
                keep.append((xd, pe, px, q, sec))
        opn = keep
        sec = SMAP.get(r.sym)
        if cap and sec and sum(1 for o in opn if o[4] == sec) >= cap:
            continue
        q = min(int(cap0 * risk // (r.entry - r.init_stop)), int(cap0 * maxpct // r.entry))
        if q < 1 or q * r.entry * 1.00175 > cash:
            continue
        cash -= q * r.entry * 1.00175
        opn.append((r.exit_date, r.entry, r.exit, q, sec))
        n += 1
    for (xd, pe, px, q, _) in opn:
        eq += q * (px - pe) - q * (pe + px) * 0.00175
        hist.append((xd, eq))
    H = pd.Series([e for _, e in sorted(hist)], index=[d for d, _ in sorted(hist)]).groupby(level=0).last()
    yrs = (T["entry_date"].max() - T["entry_date"].min()).days / 365.25
    return {"cagr": ((eq / cap0) ** (1 / yrs) - 1) * 100, "maxdd": float((H / H.cummax() - 1).min() * 100),
            "per_week": n / (yrs * 52)}


out, ok = {}, {"K3": True, "K2": True}
for st, f in (("top300", "trades_FINAL.csv"), ("all", "improve_trades_U2.csv")):
    T = load(f)
    out[st] = {"sector_known_share": round(float(T["sym"].map(SMAP).notna().mean()), 3)}
    for p in ("dev", "holdout"):
        S = T[T["signal"] < OOS] if p == "dev" else T[T["signal"] >= OOS]
        res = {}
        for name, c in (("today", None), ("K3", 3), ("K2", 2)):
            R = [sim(S, s, c) for s in range(15)]
            res[name] = {k: round(float(np.median([r[k] for r in R])), 1) for k in ("cagr", "maxdd", "per_week")}
        for k in ("K3", "K2"):
            ok[k] &= res[k]["maxdd"] >= res["today"]["maxdd"] + 2.0 and res[k]["cagr"] >= res["today"]["cagr"] - 1.0
        out[st][p] = res
        print(st, p, res, flush=True)
out.update({k + "_PASS": bool(v) for k, v in ok.items()})
json.dump(out, open(f"{HERE}/improve19_results.json", "w"), indent=1)
print({k: v for k, v in out.items() if k.endswith("PASS")}, out["top300"]["sector_known_share"], out["all"]["sector_known_share"])
