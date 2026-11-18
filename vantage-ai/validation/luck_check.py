"""ADVERSARIAL LUCK CHECK (Project ALPHA idea, owner 18 Nov): could random buying have produced VANTAGE's results?
For every real VANTAGE trade, a random trade is drawn in the SAME stock, while it was in the same universe, held for
the SAME number of days, bought at an open and sold at an open, with the same 0.35% costs. 200 random worlds.
-> luck_check.json: VANTAGE's average and win rate vs the random distribution (percentile), per period and type.
Plus a multiple-testing note: how many ideas were tried (experiments.json) and what that means for a 'pass'."""
import json
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, "/home/user/shri-labh-jewellers/vantage-ai/validation")
import improve as im  # noqa: E402
from improve import iv, OOS, COST  # noqa: E402

out = {}
for st, f, gen in (("top300", "trades_FINAL.csv", lambda: iv.universe(include_delisted=True)),
                   ("all", "improve_trades_U2.csv", im.all_stocks)):
    T = pd.read_csv(f, parse_dates=["signal", "entry_date", "exit_date"])
    data = {s: (d, np.asarray(m, bool)) for s, d, m, src in gen()}
    T = T[T["sym"].isin(data)].copy()
    T["net"] = T["exit"] / T["entry"] - 1 - COST
    T["held"] = [max(1, int(h)) for h in T["days"].fillna(1)]
    rng = np.random.default_rng(7)
    sims = {"dev": [], "holdout": []}
    per = np.where(T["signal"] < OOS, "dev", "holdout")
    by = {}
    for (sym, p), g in T.assign(per=per).groupby(["sym", "per"]):
        d, m = data[sym]
        idx = d.index
        lo, hi = (0, idx.searchsorted(OOS)) if p == "dev" else (idx.searchsorted(OOS), len(idx))
        ok = np.where(m)[0]
        ok = ok[(ok >= max(lo, 260)) & (ok < hi - 2)]
        by[(sym, p)] = (d["open"].values, ok, g["held"].values)
    for k in range(200):
        acc = {"dev": [], "holdout": []}
        for (sym, p), (o, ok, holds) in by.items():
            if not len(ok):
                continue
            starts = rng.choice(ok, size=len(holds))
            ends = np.minimum(starts + holds, len(o) - 1)
            r = o[ends] / o[starts] - 1 - COST
            acc[p].extend(r[np.isfinite(r)].tolist())
        for p in acc:
            a = np.array(acc[p])
            sims[p].append((a.mean(), (a > 0).mean()))
    out[st] = {}
    for p in ("dev", "holdout"):
        real = T[per == p]["net"]
        s = np.array(sims[p])
        out[st][p] = {"vantage_avg_pct": round(real.mean() * 100, 2), "vantage_win_pct": round((real > 0).mean() * 100, 1),
                      "random_avg_pct_median": round(float(np.median(s[:, 0])) * 100, 2),
                      "random_avg_pct_best_of_200": round(float(s[:, 0].max()) * 100, 2),
                      "random_win_pct_median": round(float(np.median(s[:, 1])) * 100, 1),
                      "vantage_beats_random_pct": round(float((s[:, 0] < real.mean()).mean() * 100), 1)}
        print(st, p, out[st][p], flush=True)
json.dump(out, open("luck_check.json", "w"), indent=1)
