"""Round 18 (IMPROVE18_PREREGISTRATION.md): tighter stop for trend trades."""
import json
import sys
from multiprocessing import Pool
import numpy as np
import pandas as pd
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import improve as im  # noqa: E402
from improve import iv, HERE, OOS  # noqa: E402
from improve10 import sim, load  # noqa: E402

V = {"Z1": 4.0, "Z2": 3.0}
if sys.argv[1] == "run":
    im.BENCH = iv.nifty()["close"]
    top = list(iv.universe(include_delisted=True))
    allj = [(s, d[["open", "high", "low", "close", "volume"]], m, src) for s, d, m, src in im.all_stocks()]
    for k, mult in V.items():
        im.PARAMS = {"rcpStopMult": mult}
        for st, jobs in (("top300", top), ("all", allj)):
            tr = []
            with Pool(4) as p:
                for r in p.imap_unordered(im._one, jobs, chunksize=4):
                    tr += [t for t in r if "error" not in t]
            pd.DataFrame(tr).to_csv(f"{HERE}/improve18_trades_{k}_{st}.csv", index=False)
            print(k, st, len(tr), flush=True)
else:
    out, ok = {}, {k: True for k in V}
    for st, base in (("top300", "trades_FINAL.csv"), ("all", "improve_trades_U.csv")):
        out[st] = {}
        for p in ("dev", "holdout"):
            sel = (lambda T: T[T["signal"] < OOS]) if p == "dev" else (lambda T: T[T["signal"] >= OOS])
            res = {}
            for name, f in [("today", base)] + [(k, f"improve18_trades_{k}_{st}.csv") for k in V]:
                T = sel(load(f))
                R = [sim(T, s) for s in range(15)]
                res[name] = {x: round(float(np.median([r[x] for r in R])), 1) for x in ("cagr", "maxdd", "per_week")}
            for k in V:
                ok[k] &= res[k]["cagr"] >= res["today"]["cagr"] + 1.0 and res[k]["maxdd"] >= res["today"]["maxdd"] - 2.0
            out[st][p] = res
            print(st, p, res, flush=True)
    out.update({k + "_PASS": bool(v) for k, v in ok.items()})
    json.dump(out, open(f"{HERE}/improve18_results.json", "w"), indent=1)
    print({k: v for k, v in out.items() if k.endswith("PASS")})
