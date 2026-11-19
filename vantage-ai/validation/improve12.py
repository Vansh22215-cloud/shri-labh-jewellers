"""Round 12 (IMPROVE12_PREREGISTRATION.md)."""
import glob
import json
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from improve import HERE, OOS, SW  # noqa: E402
from improve8 import load, SETS, g  # noqa: E402
from improve10 import sim  # noqa: E402

rows = []
for f in sorted(glob.glob(f"{SW}/data/participant_oi/*.csv")):
    try:
        d = pd.read_csv(f)
        d.columns = [c.strip() for c in d.columns]
        r = d[d.iloc[:, 0].astype(str).str.strip() == "FII"].iloc[0]
        L, S = float(r["Future Index Long"]), float(r["Future Index Short"])
        rows.append((pd.Timestamp(f.rsplit("/", 1)[-1][:8]), L / (L + S)))
    except Exception:
        pass
share = pd.Series(dict(rows)).sort_index()
pct = share.rolling(250, min_periods=200).apply(lambda x: (x[:-1] < x[-1]).mean(), raw=True)
out = {"days": int(len(share))}
for rule, cond in (("F1_skip_when_fii_bearish", pct <= 0.2), ("F2_skip_when_fii_bullish", pct >= 0.8)):
    flag = cond.to_dict()
    res, ok = {}, True
    for k, f in SETS.items():
        T = load(f)
        T["skip"] = T["signal"].map(flag).fillna(False).astype(bool)
        res[k] = {}
        for p, m in (("dev", T["signal"] < OOS), ("holdout", T["signal"] >= OOS)):
            a, b = g(T[m & T["skip"]]), g(T[m & ~T["skip"]])
            acc0 = [sim(T[m], s) for s in range(15)]
            acc1 = [sim(T[m & ~T["skip"]], s) for s in range(15)]
            res[k][p] = {"skipped": a, "kept": b,
                         "account_today": {x: round(float(np.median([z[x] for z in acc0])), 1) for x in ("cagr", "maxdd")},
                         "account_with_rule": {x: round(float(np.median([z[x] for z in acc1])), 1) for x in ("cagr", "maxdd")}}
            ok &= a.get("n", 0) >= 100 and b["per_trade"] - a["per_trade"] >= 1.0
            print(rule, k, p, res[k][p], flush=True)
    res["PASS"] = bool(ok)
    out[rule] = res
json.dump(out, open(f"{HERE}/improve12_results.json", "w"), indent=1)
print({k: v["PASS"] for k, v in out.items() if isinstance(v, dict)})
