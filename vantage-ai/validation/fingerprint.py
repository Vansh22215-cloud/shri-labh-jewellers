"""Backlog 13a: VANTAGE's stock-choice fingerprint (top-300, point-in-time).
1) For every VANTAGE BUY, its percentile among all universe stocks that day on: 6-month return, distance from the
   52-week high, 20-day volatility, traded value, 1-month return.
2) Fingerprint-matched random baseline: random universe stocks on random days whose percentiles fall in the same
   band as VANTAGE's typical pick (middle 50% of picks on each fact), held for VANTAGE's holding times.
   If they earn as much as VANTAGE, the edge is 'that kind of stock' -> more trades possible.
-> fingerprint.json"""
import json
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from improve import iv, OOS, COST  # noqa: E402

data = list(iv.universe(include_delisted=True))
close = pd.DataFrame({s: d["close"] for s, d, m, src in data}).sort_index()
high = pd.DataFrame({s: d["high"] for s, d, m, src in data}).reindex(close.index)
opn = pd.DataFrame({s: d["open"] for s, d, m, src in data}).reindex(close.index)
vol = pd.DataFrame({s: d["volume"] for s, d, m, src in data}).reindex(close.index)
mem = pd.DataFrame({s: pd.Series(m, index=d.index) for s, d, m, src in data}).reindex(close.index).fillna(False).astype(bool)
F = {"ret6m": close / close.shift(126) - 1, "from_high": close / high.rolling(252, min_periods=200).max() - 1,
     "vol20": close.pct_change(fill_method=None).rolling(20).std(), "turnover": (close * vol).rolling(20).mean(),
     "ret1m": close / close.shift(21) - 1}
P = {k: v.where(mem).rank(axis=1, pct=True) for k, v in F.items()}
T = pd.read_csv("trades_FINAL.csv", parse_dates=["signal", "entry_date", "exit_date"])
T["net"] = T["exit"] / T["entry"] - 1 - COST
for k in P:
    T[k] = [P[k].at[d, s] if d in P[k].index and s in P[k].columns else np.nan for d, s in zip(T["signal"], T["sym"])]
out = {"fingerprint_median_percentile": {}, "band": {}}
dev = T[T["signal"] < OOS]
for k in P:
    out["fingerprint_median_percentile"][k] = round(float(T[k].median() * 100), 1)
    lo, hi = dev[k].quantile(0.25), dev[k].quantile(0.75)                     # band from development only
    out["band"][k] = [round(float(lo), 3), round(float(hi), 3)]
print("Fingerprint (median percentile of VANTAGE picks):", out["fingerprint_median_percentile"])
print("Band (middle 50% of development picks):", out["band"])
# eligible (stock, day) cells that match the band on every fact
match = mem.copy()
for k, (lo, hi) in out["band"].items():
    match &= (P[k] >= lo) & (P[k] <= hi)
cells = np.argwhere(match.values)
dates = close.index
rng = np.random.default_rng(5)
o = opn.values
for per, m in (("dev", T["signal"] < OOS), ("holdout", T["signal"] >= OOS)):
    holds = np.maximum(1, T[m]["days"].fillna(1).astype(int).values)
    cut = np.searchsorted(dates, OOS)
    c = cells[(cells[:, 0] < cut) if per == "dev" else (cells[:, 0] >= cut)]
    c = c[c[:, 0] < len(dates) - 3]
    means = []
    for k in range(200):
        pick = c[rng.integers(0, len(c), size=len(holds))]
        a = pick[:, 0] + 1
        b = np.minimum(a + holds, len(dates) - 1)
        r = o[b, pick[:, 1]] / o[a, pick[:, 1]] - 1 - COST
        r = r[np.isfinite(r)]
        means.append(r.mean())
    means = np.array(means)
    out[per] = {"vantage_avg_pct": round(float(T[m]["net"].mean() * 100), 2),
                "fingerprint_random_avg_pct_median": round(float(np.median(means) * 100), 2),
                "matching_cells_per_day": round(len(c) / max(1, (cut if per == "dev" else len(dates) - cut)), 1),
                "vantage_beats_matched_random_pct": round(float((means < T[m]["net"].mean()).mean() * 100), 1)}
    print(per, out[per], flush=True)
json.dump(out, open("fingerprint.json", "w"), indent=1)
