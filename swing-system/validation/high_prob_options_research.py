import sys, numpy as np, pandas as pd
sys.path.insert(0, "/home/user/shri-labh-jewellers/swing-system")
from swing import data_prices
from swing.high_prob import rsi, adjusted
from swing.options_check import bs
u = pd.read_csv("data/universe_history.csv"); u["asof"] = pd.to_datetime(u["asof"])
top = {a: set(g.nsmallest(150, "rank")["symbol"]) for a, g in u.groupby("asof")}   # ~F&O-sized stocks
months = sorted(top)
n = data_prices.load("NIFTY50"); nc = n["close"]; nok = (nc > nc.rolling(200).mean()) & (rsi(nc) < 20)
def member(idx, s):
    m = np.zeros(len(idx), bool)
    for i, a in enumerate(months):
        b = months[i+1] if i+1 < len(months) else pd.Timestamp("2100-01-01")
        if s in top[a]: m |= (idx >= a) & (idx < b)
    return m
def next_expiry(d):
    # last Thursday of the month, at least 15 days away
    for k in range(0, 3):
        m = (d + pd.offsets.MonthBegin(k)).to_period("M")
        last = pd.Timestamp(m.end_time.date()); 
        while last.weekday() != 3: last -= pd.Timedelta(days=1)
        if (last - d).days >= 15: return last
rows = []
for s in sorted(set(u[u["rank"] <= 150]["symbol"])):
    d = data_prices.load(s)
    if d is None or len(d) < 260: continue
    a = adjusted(d); a = a[a.index >= "2012-06-01"]
    if len(a) < 260: continue
    c = a["close"]; s200, s5, r2 = c.rolling(200).mean(), c.rolling(5).mean(), rsi(c)
    vol = np.log(c).diff().rolling(20).std() * np.sqrt(252)
    ent = ((c >= 1.10*s200) & (r2 < 2) & nok.reindex(a.index).fillna(False)).values & member(a.index, s)
    ex = (c > s5).values; o = a["open"].values; lo = a["low"].values
    tr = pd.concat([a.high-a.low, (a.high-c.shift()).abs(), (a.low-c.shift()).abs()], axis=1).max(axis=1).rolling(14).mean().values
    i = 0
    while i < len(a) - 2:
        if ent[i] and a.index[i] >= pd.Timestamp("2013-01-01"):
            e = o[i+1]; stop = e - 4*tr[i]; j = i+1; px = None
            while j < len(a)-1:
                if lo[j] <= stop: px = stop; xj = j; break
                if ex[j] or j-(i+1) >= 9: px = o[j+1]; xj = j+1; break
                j += 1
            if px is None: break
            d0, d1 = a.index[i+1], a.index[xj]; exp = next_expiry(d0)
            iv = max(0.15, float(vol.iloc[i]) * 1.15) if np.isfinite(vol.iloc[i]) else 0.3
            K = e * 0.98                                    # ~2% in the money call
            t0, t1 = (exp - d0).days/365, max(1/365, (exp - d1).days/365)
            c0, c1 = bs(e, K, t0, iv, "CE"), bs(px, K, t1, iv, "CE")
            opt = c1/c0 - 1 - 0.015                         # ~1.5% of premium: option charges + spread
            rows.append({"date": d0, "stock": s, "stock_ret": px/e - 1 - 0.0035, "opt_ret": opt})
            i = j + 1
        else: i += 1
df = pd.DataFrame(rows); dev, ho = df[df.date < "2023-11-01"], df[df.date >= "2023-11-01"]
for nm, g in (("ALL", df), ("dev 2013-2023", dev), ("HOLDOUT 2023-11..", ho)):
    print(f"{nm:18s} trades {len(g):5d} | STOCK win {(g.stock_ret>0).mean()*100:4.1f}% avg {g.stock_ret.mean()*100:+.2f}% "
          f"| CALL OPTION win {(g.opt_ret>0).mean()*100:4.1f}% avg {g.opt_ret.mean()*100:+.1f}% of premium, "
          f"avg win {g.opt_ret[g.opt_ret>0].mean()*100:+.0f}% loss {g.opt_ret[g.opt_ret<=0].mean()*100:+.0f}%")
