"""Luck check 2: random STOCK and random DAY from the same universe (point-in-time members / all stocks >= Rs 2 cr),
held for VANTAGE's own holding times, same costs. Tests whether VANTAGE's STOCK CHOICE adds value
(luck_check.py tested timing only, inside VANTAGE's own stocks). -> luck_check2.json"""
import json
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import improve as im  # noqa: E402
from improve import iv, OOS, COST  # noqa: E402

out = {}
for st, f, gen in (("top300", "trades_FINAL.csv", lambda: iv.universe(include_delisted=True)),
                   ("all", "improve_trades_U2.csv", im.all_stocks)):
    T = pd.read_csv(f, parse_dates=["signal", "entry_date", "exit_date"])
    T["net"] = T["exit"] / T["entry"] - 1 - COST
    pool = []                                   # (open array, eligible day positions, dates)
    for s, d, m, src in gen():
        o = d["open"].values
        turn = (d["close"] * d["volume"]).rolling(20).mean().values
        ok = np.where(np.asarray(m, bool) & (turn >= 2e7))[0]
        ok = ok[ok >= 260]
        if len(ok):
            pool.append((o, ok, d.index.values))
    rng = np.random.default_rng(11)
    out[st] = {}
    for p in ("dev", "holdout"):
        R = T[(T["signal"] < OOS) if p == "dev" else (T["signal"] >= OOS)]
        holds = np.maximum(1, R["days"].fillna(1).astype(int).values)
        cut = np.datetime64(OOS)
        sub = []
        for o, ok, dt in pool:
            okp = ok[(dt[ok] < cut)] if p == "dev" else ok[(dt[ok] >= cut)]
            okp = okp[okp < len(o) - 2]
            if len(okp):
                sub.append((o, okp))
        means, wins = [], []
        for k in range(200):
            picks = rng.integers(0, len(sub), size=len(holds))
            r = []
            for j, h in zip(picks, holds):
                o, okp = sub[j]
                a = okp[rng.integers(0, len(okp))]
                b = min(a + h, len(o) - 1)
                r.append(o[b] / o[a] - 1 - COST)
            r = np.array(r)
            r = r[np.isfinite(r)]
            means.append(r.mean()); wins.append((r > 0).mean())
        means = np.array(means)
        out[st][p] = {"vantage_avg_pct": round(float(R["net"].mean() * 100), 2),
                      "random_stock_random_day_avg_pct_median": round(float(np.median(means) * 100), 2),
                      "random_best_of_200": round(float(means.max() * 100), 2),
                      "random_win_pct_median": round(float(np.median(wins) * 100), 1),
                      "vantage_beats_random_pct": round(float((means < R["net"].mean()).mean() * 100), 1)}
        print(st, p, out[st][p], flush=True)
json.dump(out, open("luck_check2.json", "w"), indent=1)
