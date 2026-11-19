"""Round 7 (IMPROVE7_PREREGISTRATION.md): RCP exits."""
import json
import sys
from multiprocessing import Pool
import numpy as np
import pandas as pd
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import improve as im  # noqa: E402
from improve import iv, HERE, stats, split, frame  # noqa: E402

V = {"X1": {"rcpSellMinDays": 10000}, "X2": {"rcpMaxDays": 120}, "X3": {"rcpSellMinDays": 10000, "rcpMaxDays": 120},
     "X4": {"rcpSellMinDays": 20}, "X5": {"rcpMaxDays": 120, "rcpTrailAtr": 5.0}}


def runs():
    im.BENCH = iv.nifty()["close"]
    data = list(iv.universe(include_delisted=True))
    for k, prm in V.items():
        im.PARAMS = prm
        tr = []
        with Pool(4) as p:
            for r in p.imap_unordered(im._one, data, chunksize=4):
                tr += r
        pd.DataFrame([t for t in tr if "error" not in t]).to_csv(f"{HERE}/improve7_trades_{k}.csv", index=False)
        print(k, "done", file=sys.stderr, flush=True)


def st(T):
    s = stats(T)
    if len(T):
        s["per_day"] = round(float((T["net"] / T["days"].clip(lower=1)).mean() * 100), 3)
        s["total_per_day"] = round(float(T["net"].sum() / T["days"].clip(lower=1).sum() * 100), 3)
        s["avg_days"] = round(float(T["days"].mean()), 1)
    return s


def analyse():
    B = frame(f"{HERE}/trades_FINAL.csv")
    out = {}
    bd, bh = split(B[B["setup"] == "RCP"])
    out["baseline"] = {"dev": st(bd), "holdout": st(bh), "all_types_holdout": st(split(B)[1])}
    for k in V:
        T = frame(f"{HERE}/improve7_trades_{k}.csv")
        d, h = split(T[T["setup"] == "RCP"])
        sd, sh = st(d), st(h)
        b = out["baseline"]
        ok = (sh["exp"] > b["holdout"]["exp"] and sh["total_per_day"] > b["holdout"]["total_per_day"]
              and sh["dd_1pct"] >= 1.1 * b["holdout"]["dd_1pct"] and sd["exp"] > b["dev"]["exp"])
        out[k] = {"PASS": bool(ok), "dev": sd, "holdout": sh, "all_types_holdout": st(split(T)[1])}
    json.dump(out, open(f"{HERE}/improve7_results.json", "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    {"runs": runs, "analyse": analyse}[sys.argv[1]]()
