"""Rolling Candle Profile (exact port) as a POSITIONAL tool: which filters / safety stops help? Daily, 13 years,
point-in-time top-300, next-open entry, exit at the next open after its SELL signal (cap 60 days), 0.35% costs.
Filters are chosen on development (< 2023-11) and must hold on the untouched holdout."""
import sys

import numpy as np
import pandas as pd

ROOT = "/home/user/shri-labh-jewellers/swing-system"
sys.path.insert(0, ROOT)
sys.path.insert(0, f"{ROOT}/validation")
from rolling_profile_exact import signals  # noqa: E402
from rolling_profile_research import run_trades  # noqa: E402
from swing import data_prices  # noqa: E402

HOLD = "2023-11-01"
u = pd.read_csv(f"{ROOT}/data/universe_history.csv")
u["asof"] = pd.to_datetime(u["asof"])
u = u[u["rank"] <= 300]
members = {a: set(g["symbol"]) for a, g in u.groupby("asof")}
top100 = {a: set(g.nsmallest(100, "rank")["symbol"]) for a, g in u.groupby("asof")}
months = sorted(members)
nf = data_prices.load("NIFTY50")["close"]
NUP = nf > nf.rolling(200).mean()
N50 = nf > nf.rolling(50).mean()


def mask(idx, s, m):
    out = np.zeros(len(idx), bool)
    for i, a in enumerate(months):
        b = months[i + 1] if i + 1 < len(months) else pd.Timestamp("2100-01-01")
        if s in m[a]:
            out |= (idx >= a) & (idx < b)
    return out


R = {}
for sym in sorted(set(u["symbol"])):
    d0 = data_prices.load(sym)
    if d0 is None or len(d0) < 300:
        continue
    f = (d0["adj_close"] / d0["close"]).fillna(1.0)
    d = pd.DataFrame({"open": d0.open * f, "high": d0.high * f, "low": d0.low * f, "close": d0.adj_close,
                      "volume": d0.volume}).dropna()
    d = d[d.index >= "2012-01-01"]
    if len(d) < 300:
        continue
    s = signals(d, "price")
    mm, t100 = mask(d.index, sym, members), mask(d.index, sym, top100)
    c = d.close
    s200, s50 = c.rolling(200).mean().values, c.rolling(50).mean().values
    hi52 = c.rolling(250).max().values
    nup, n50 = NUP.reindex(d.index).fillna(False).values, N50.reindex(d.index).fillna(False).values
    b, sell, cv = s.buy.values & mm, s.sell.values, c.values
    F = {"all BUY signals": b,
         "+ Nifty above 200d": b & nup,
         "+ stock above 200d": b & (cv > s200),
         "+ stock above 50d > 200d": b & (cv > s50) & (s50 > s200),
         "+ stock within 10% of 52w high": b & (cv >= 0.9 * hi52),
         "+ stock above 50d>200d + Nifty above 200d": b & (cv > s50) & (s50 > s200) & nup,
         "+ within 10% of 52w high + Nifty above 200d": b & (cv >= 0.9 * hi52) & nup,
         "+ top-100 liquidity + Nifty above 200d": b & t100 & nup,
         "+ Nifty above 50d and 200d": b & nup & n50}
    for k, e in F.items():
        for stop in (None, 3.0, 5.0):
            R.setdefault((k, stop), []).extend(run_trades(d, e, sell, stop_atr=stop, max_bars=60))

rows = []
for (k, stop), v in R.items():
    df = pd.DataFrame(v, columns=["date", "ret", "bars"])
    if not len(df):
        continue
    dev, ho = df[df.date < HOLD], df[df.date >= HOLD]
    yrs = df.groupby(df.date.dt.year)["ret"].mean() * 100
    rows.append({"filter": k, "safety_stop_ATR": stop or "-", "trades": len(df),
                 "win%": round((df.ret > 0).mean() * 100, 1), "avg%": round(df.ret.mean() * 100, 2),
                 "avg_win%": round(df.ret[df.ret > 0].mean() * 100, 1), "avg_loss%": round(df.ret[df.ret <= 0].mean() * 100, 1),
                 "dev_avg%": round(dev.ret.mean() * 100, 2), "HOLD_win%": round((ho.ret > 0).mean() * 100, 1),
                 "HOLD_avg%": round(ho.ret.mean() * 100, 2), "losing_years": int((yrs < 0).sum()),
                 "days": round(df.bars.mean(), 1)})
out = pd.DataFrame(rows)
print(out.to_string(index=False))
out.to_csv(f"{ROOT}/validation/rolling_profile_positional.csv", index=False)
