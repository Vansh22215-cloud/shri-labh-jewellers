"""Round 2 (IMPROVE2_PREREGISTRATION.md): how each trade is taken.
python3 improve2.py runs     -> improve2_trades_R1..R4.csv
python3 improve2.py analyse  -> improve2_results.json
"""
import json
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import improve as im  # noqa: E402  (shared helpers, same paths and costs)
from improve import iv, replica, HERE, SW, stats, split, frame  # noqa: E402

VARIANTS = {"R1": {"gapGuardAtr": 0.5}, "R2": {"limitAtr": 0.25}, "R3": {"scaleOutR": 2.0}, "R4": {"earnDays": 5}}
BENCH, PARAMS, EARN = None, None, {}


def _earn(sym):
    try:
        e = pd.to_datetime(pd.read_csv(f"{SW}/data/events/earnings/{sym}.csv")["date"], errors="coerce").dropna()
        return np.sort(e.values.astype("datetime64[ns]").astype(np.int64))
    except Exception:
        return None


def _one(args):
    sym, d, m, src = args
    prm = dict(im.BASE_P, **PARAMS)
    if "earnDays" in PARAMS:
        prm["earnings"] = EARN.get(sym)
    try:
        tr = replica.run(d, BENCH, allow=m, p=prm)
        for x in tr:
            x.update(sym=sym, src=src)
        return tr
    except Exception as e:
        return [{"error": f"{sym}: {e}"}]


def runs():
    global BENCH, PARAMS, EARN
    BENCH = iv.nifty()["close"]
    data = list(iv.universe(include_delisted=True))
    EARN = {s: _earn(s) for s, d, m, src in data}
    for name, prm in VARIANTS.items():
        PARAMS = prm
        tr = []
        with Pool(4) as p:
            for r in p.imap_unordered(_one, data, chunksize=4):
                tr += r
        T = pd.DataFrame([t for t in tr if "error" not in t])
        T.to_csv(f"{HERE}/improve2_trades_{name}.csv", index=False)
        print(name, len(T), "trades", sum("error" in t for t in tr), "errors", file=sys.stderr)


def frame2(path):
    T = frame(path)
    if "gross_override" in T:
        g = T["gross_override"].notna()
        T.loc[g, "gross"] = T.loc[g, "gross_override"]
        T["net"] = T["gross"] - im.COST
    return T


PRIO = {("Dip-buy", "A"): 0, ("Dip-buy", "B"): 1, ("Dip-buy", "C"): 1}


def slots(T, k=8, ranked=True):
    """8-slot account: on each entry day the free slots go to the best-ranked signals (or alphabetical)."""
    T = T.copy()
    T["prio"] = [PRIO.get((s, str(t)), 2 if s == "RCP" else 3) for s, t in zip(T["setup"], T["tier"].fillna(""))]
    T = T.sort_values(["entry_date", "prio", "score"], ascending=[True, True, False]) if ranked else \
        T.sort_values(["entry_date", "sym"])
    keep, open_ex = [], []
    for i, r in T.iterrows():
        open_ex = [x for x in open_ex if x > r["entry_date"]]
        if len(open_ex) < k:
            keep.append(i)
            open_ex.append(r["exit_date"])
    C = T.loc[keep]
    R = (C["net"] / C["stop_pct"].clip(lower=0.005))
    return C, float(R.sum())


def analyse():
    base = frame(f"{HERE}/trades_FINAL.csv")
    bdev, bho = split(base)
    out = {"baseline": {"dev": stats(bdev), "holdout": stats(bho)}}
    for k in ("R1", "R2", "R4"):
        V = frame2(f"{HERE}/improve2_trades_{k}.csv")
        vd, vh = split(V)
        sd, sh = stats(vd), stats(vh)
        ok = (sh["n"] >= 0.5 * stats(bho)["n"] and sh["exp"] > stats(bho)["exp"] and sh["win"] >= stats(bho)["win"]
              and sd["exp"] > stats(bdev)["exp"] and sd["win"] >= stats(bdev)["win"])
        out[k] = {"PASS": bool(ok), "dev": sd, "holdout": sh}
    V = frame2(f"{HERE}/improve2_trades_R3.csv")
    vd, vh = split(V)
    sd, sh, xd, xh = stats(vd), stats(vh), stats(bdev), stats(bho)
    ok = all(s_["exp"] >= x_["exp"] and (s_["dd_1pct"] > x_["dd_1pct"] or (s_["pf"] or 0) > (x_["pf"] or 0))
             for s_, x_ in ((sd, xd), (sh, xh)))
    out["R3"] = {"PASS": bool(ok), "dev": sd, "holdout": sh}
    res = {}
    for name, ranked in (("alphabetical", False), ("ranked", True)):
        res[name] = {}
        for per, part in (("dev", bdev), ("holdout", bho)):
            C, totR = slots(part, 8, ranked)
            res[name][per] = dict(stats(C), total_R=round(totR, 1))
    ok = all(res["ranked"][p_]["total_R"] > res["alphabetical"][p_]["total_R"]
             and res["ranked"][p_]["exp"] > res["alphabetical"][p_]["exp"] for p_ in ("dev", "holdout"))
    out["R5"] = {"PASS": bool(ok), **res}
    json.dump(out, open(f"{HERE}/improve2_results.json", "w"), indent=1, default=str)
    return out


if __name__ == "__main__":
    {"runs": runs, "analyse": analyse}[sys.argv[1]]()
