"""All-stocks baseline on the CURRENT price data (improve_trades_U.csv was made before 1,480 more stocks were
downloaded on 18 Nov; variant runs made after that are not comparable with it). -> improve_trades_U2.csv,
then re-scores the all-stock cells of rounds 10 (V2), 16 (D1) and 18 (Z1/Z2) against it."""
import json
import sys
from multiprocessing import Pool
import numpy as np
import pandas as pd
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import improve as im  # noqa: E402
from improve import iv, HERE, OOS  # noqa: E402
from improve10 import sim, load  # noqa: E402

im.BENCH, im.PARAMS = iv.nifty()["close"], {}
jobs = [(s, d[["open", "high", "low", "close", "volume"]], m, src) for s, d, m, src in im.all_stocks()]
tr = []
with Pool(4) as p:
    for r in p.imap_unordered(im._one, jobs, chunksize=4):
        tr += [t for t in r if "error" not in t]
pd.DataFrame(tr).to_csv(f"{HERE}/improve_trades_U2.csv", index=False)
print("U2 baseline trades:", len(tr), flush=True)
out = {}
for name, f in (("baseline_U2", "improve_trades_U2.csv"), ("R10_V2_wider_dips", "improve10_trades_U_D2.csv"),
                ("R16_D1_dips", "improve16_trades_U_D1.csv"), ("R18_Z1_stop4", "improve18_trades_Z1_all.csv"),
                ("R18_Z2_stop3", "improve18_trades_Z2_all.csv")):
    out[name] = {}
    for p in ("dev", "holdout"):
        T = load(f)
        T = T[T["signal"] < OOS] if p == "dev" else T[T["signal"] >= OOS]
        R = [sim(T, s) for s in range(15)]
        out[name][p] = {x: round(float(np.median([r[x] for r in R])), 1) for x in ("cagr", "maxdd", "per_week")}
    print(name, out[name], flush=True)
json.dump(out, open(f"{HERE}/rebuild_u_baseline.json", "w"), indent=1)
