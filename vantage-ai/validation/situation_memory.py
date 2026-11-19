"""MARKET MEMORY (Project ALPHA input): for every kind of market day in 13 years - NIFTY rising/falling (vs 200-day
average), calm/jumpy (20-day swings vs the past year, top 20% = jumpy), breadth (share of the top-300 above their
200-day average: weak < 40%, middle 40-60%, strong > 60%) - how VANTAGE tips sent on such days did.
-> situation_memory.json {situation key: {type: {n, avg_pct, win_pct}, all: {...}}} + daily situations."""
import json
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from improve import iv, COST  # noqa: E402


def situations():
    n = iv.nifty()["close"]
    vol = n.pct_change().rolling(20).std()
    data = list(iv.universe(include_delisted=True))
    close = pd.DataFrame({s: d["close"] for s, d, m, src in data}).sort_index()
    mem = pd.DataFrame({s: pd.Series(m, index=d.index) for s, d, m, src in data}).reindex(close.index).fillna(False).astype(bool)
    above = (close > close.rolling(200, min_periods=200).mean()).where(mem)
    breadth = above.sum(axis=1) / above.notna().sum(axis=1).replace(0, np.nan)
    S = pd.DataFrame({"trend": np.where(n > n.rolling(200).mean(), "rising", "falling"),
                      "mood": np.where(vol > vol.rolling(250, min_periods=120).quantile(0.8), "jumpy", "calm")}, index=n.index)
    S["breadth"] = pd.cut(breadth.reindex(S.index), [-1, 0.4, 0.6, 2], labels=["weak", "middle", "strong"]).astype(str)
    S["key"] = S["trend"] + " | " + S["mood"] + " | breadth " + S["breadth"]
    return S


if __name__ == "__main__":
    S = situations()
    T = pd.read_csv("trades_FINAL.csv", parse_dates=["signal"])
    T["net"] = T["exit"] / T["entry"] - 1 - COST
    T["kind"] = np.where(T["setup"] == "Dip-buy", "Dip-buy", T["setup"])
    T["key"] = T["signal"].map(S["key"])
    out = {}
    for k, g in T.dropna(subset=["key"]).groupby("key"):
        out[k] = {"days_in_13y": int((S["key"] == k).sum()),
                  "all": {"n": int(len(g)), "avg_pct": round(g.net.mean() * 100, 2), "win_pct": round((g.net > 0).mean() * 100, 1)}}
        for kind, h in g.groupby("kind"):
            out[k][kind] = {"n": int(len(h)), "avg_pct": round(h.net.mean() * 100, 2), "win_pct": round((h.net > 0).mean() * 100, 1)}
    json.dump(out, open("situation_memory.json", "w"), indent=1)
    S[["key"]].to_csv("situation_days.csv")
    for k, v in sorted(out.items(), key=lambda z: -z[1]["all"]["avg_pct"]):
        print(f"{k:42s} days {v['days_in_13y']:4d} | tips {v['all']['n']:4d} avg {v['all']['avg_pct']:+6.2f}% won {v['all']['win_pct']:5.1f}%")
