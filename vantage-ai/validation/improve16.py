"""Round 16 (IMPROVE16_PREREGISTRATION.md)."""
import json
import sys
from multiprocessing import Pool
import numpy as np
import pandas as pd
sys.path.insert(0, "/home/user/shri-labh-jewellers/vantage-ai/validation")
import improve as im  # noqa: E402
from improve import iv, HERE, OOS  # noqa: E402
from improve10 import sim, load  # noqa: E402

if sys.argv[1] == "run":
    im.BENCH, im.PARAMS = iv.nifty()["close"], {"dipRsi": 5.0}
    jobs = [(s, d[["open", "high", "low", "close", "volume"]], m, src) for s, d, m, src in im.all_stocks()]
    tr = []
    with Pool(4) as p:
        for r in p.imap_unordered(im._one, jobs, chunksize=4):
            tr += [t for t in r if "error" not in t]
    pd.DataFrame(tr).to_csv(f"{HERE}/improve16_trades_U_D1.csv", index=False)
else:
    out, ok = {}, True
    for st, base, wide in (("top300", "trades_FINAL.csv", "improve_trades_D1.csv"), ("all", "improve_trades_U.csv", "improve16_trades_U_D1.csv")):
        out[st] = {}
        for p in ("dev", "holdout"):
            sel = (lambda T: T[T["signal"] < OOS]) if p == "dev" else (lambda T: T[T["signal"] >= OOS])
            res = {}
            for name, f in (("today", base), ("D1", wide)):
                T = sel(load(f))
                R = [sim(T, s) for s in range(15)]
                res[name] = {k: round(float(np.median([r[k] for r in R])), 1) for k in ("cagr", "maxdd", "per_week", "dips_taken")}
            ok &= res["D1"]["cagr"] >= res["today"]["cagr"] + 1.0 and res["D1"]["maxdd"] >= res["today"]["maxdd"] - 2.0
            out[st][p] = res
            print(st, p, res, flush=True)
    out["PASS"] = bool(ok)
    json.dump(out, open(f"{HERE}/improve16_results.json", "w"), indent=1)
    print("PASS", ok)
