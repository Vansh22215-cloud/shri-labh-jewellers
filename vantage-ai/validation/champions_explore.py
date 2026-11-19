"""Champions' rules vs our trades - EXPLORATION on development data only (signals before Nov 2023).
Features at the signal day's close: volume vs 50-day average, tightness (10-day high-low range / close before the
signal day), distance from 52-week high, 6-month strength rank. Writes champ_features.csv (both periods) for tests."""
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import improve as im  # noqa: E402
from improve import iv, OOS, COST  # noqa: E402


def feats(T, data, rs):
    rows = []
    for t in T.itertuples():
        d = data.get(t.sym)
        f = {"i": t.Index}
        if d is not None and t.signal in d.index:
            k = d.index.get_loc(t.signal)
            if k > 260:
                c, h, l, v = d["close"].values, d["high"].values, d["low"].values, d["volume"].values
                f["vol_ratio"] = v[k] / max(v[k - 50:k].mean(), 1)
                f["tight10"] = (h[k - 10:k].max() - l[k - 10:k].min()) / c[k - 1]
                f["dist52"] = c[k] / h[k - 251:k + 1].max() - 1
        f["rs"] = rs.get((t.signal, t.sym), np.nan)
        rows.append(f)
    return pd.DataFrame(rows).set_index("i")


if __name__ == "__main__":
    out = []
    for st, f, gen in (("top300", "trades_FINAL.csv", lambda: iv.universe(include_delisted=True)),
                       ("all", "improve_trades_U.csv", im.all_stocks)):
        T = pd.read_csv(f, parse_dates=["signal", "entry_date", "exit_date"])
        data = {s: d for s, d, m, src in gen()}
        close = pd.DataFrame({s: d["close"] for s, d in data.items()}).sort_index()
        R = (close / close.shift(126) - 1).rank(axis=1, pct=True).stack()
        F = feats(T, data, R.to_dict())
        T = T.join(F)
        T["set"] = st
        out.append(T)
    A = pd.concat(out, ignore_index=True)
    A["net"] = A["exit"] / A["entry"] - 1 - COST
    A["days"] = (A["exit_date"] - A["entry_date"]).dt.days.clip(lower=1)
    A.to_csv("champ_features.csv", index=False)
    D = A[A["signal"] < OOS]
    for st in ("top300", "all"):
        for setup in ("Breakout", "RCP", "Dip-buy"):
            x = D[(D["set"] == st) & (D["setup"] == setup)]
            print(f"\n=== {st} {setup} (development, n={len(x)}) per trade % | win % | per 100 days %")
            for col, bins in (("vol_ratio", [0, 1, 1.4, 2, 3, 100]), ("tight10", [0, .05, .08, .12, .2, 5]),
                              ("dist52", [-1, -.25, -.10, -.03, .001]), ("rs", [0, .5, .7, .85, .95, 1.01])):
                b = pd.cut(x[col], bins)
                g = x.groupby(b, observed=True).apply(lambda y: pd.Series({"n": len(y), "per_trade": y.net.mean() * 100,
                                                                         "win": (y.net > 0).mean() * 100,
                                                                         "per100d": y.net.sum() / y.days.sum() * 1e4}))
                print(f" {col}:", "; ".join(f"{i}: n{int(r.n)} {r.per_trade:+.1f}% w{r.win:.0f} d{r.per100d:.1f}" for i, r in g.iterrows()))
