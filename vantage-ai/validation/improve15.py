"""Round 15 (IMPROVE15_PREREGISTRATION.md): Minervini trend template."""
import json
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, "/home/user/shri-labh-jewellers/vantage-ai/validation")
import improve as im  # noqa: E402
from improve import iv, HERE, OOS  # noqa: E402
from improve10 import sim  # noqa: E402


def template(T, data):
    ok = []
    for t in T.itertuples():
        d = data.get(t.sym)
        if d is None or t.signal not in d.index:
            ok.append(False)
            continue
        k = d.index.get_loc(t.signal)
        c = d["close"].values[:k + 1]
        if len(c) < 252:
            ok.append(False)
            continue
        hi, lo = d["high"].values[k - 251:k + 1].max(), d["low"].values[k - 251:k + 1].min()
        m50, m150, m200 = c[-50:].mean(), c[-150:].mean(), c[-200:].mean()
        ok.append(bool(c[-1] >= 0.75 * hi and c[-1] >= 1.30 * lo and m50 > m150 > m200 and c[-1] > m50))
    return np.array(ok)


out, okT = {}, {"T1": True, "T2": True}
for st, f, gen in (("top300", "trades_FINAL.csv", lambda: iv.universe(include_delisted=True)),
                   ("all", "improve_trades_U.csv", im.all_stocks)):
    T = pd.read_csv(f"{HERE}/{f}", parse_dates=["signal", "entry_date", "exit_date"])
    T = T[(T["entry"] > T["init_stop"]) & (T["entry"] > 0)].reset_index(drop=True)
    T["tmpl"] = template(T, {s: d for s, d, m, src in gen()})
    keep1 = (T["setup"] != "Breakout") | T["tmpl"]
    keep2 = (T["setup"] == "Dip-buy") | T["tmpl"]
    out[st] = {"template_share_by_type": T.groupby("setup")["tmpl"].mean().round(3).to_dict()}
    for p in ("dev", "holdout"):
        m = T["signal"] < OOS if p == "dev" else T["signal"] >= OOS
        res = {}
        for name, S in (("today", T[m]), ("T1", T[m & keep1]), ("T2", T[m & keep2])):
            R = [sim(S, s) for s in range(15)]
            res[name] = {k: round(float(np.median([r[k] for r in R])), 1) for k in ("cagr", "maxdd", "per_week")}
        for k in ("T1", "T2"):
            okT[k] &= res[k]["cagr"] >= res["today"]["cagr"] + 1.0 and res[k]["maxdd"] >= res["today"]["maxdd"] - 2.0
        out[st][p] = res
        print(st, p, res, flush=True)
out.update({k + "_PASS": bool(v) for k, v in okT.items()})
json.dump(out, open(f"{HERE}/improve15_results.json", "w"), indent=1)
print({k: v for k, v in out.items() if k.endswith("PASS")}, out["top300"]["template_share_by_type"], out["all"]["template_share_by_type"])
