"""High-probability swing strategies on 13 years of NSE data (point-in-time top-300 liquidity universe).
Entry at the NEXT open after the signal close; exit at the next open after the exit-rule close; charges 0.35% round
trip (delivery STT both sides + Zerodha charges + slippage). Holdout = 2023-11 onwards (never used to choose)."""
import sys, json
import numpy as np, pandas as pd
sys.path.insert(0, "/home/user/shri-labh-jewellers/swing-system")
from swing import data_prices

COST = 0.0035
u = pd.read_csv("/home/user/shri-labh-jewellers/swing-system/data/universe_history.csv")
u["asof"] = pd.to_datetime(u["asof"])
u = u[u["rank"] <= 300]
members = {}
for a, g in u.groupby("asof"):
    members[a] = set(g["symbol"])
months = sorted(members)
syms = sorted(set(u["symbol"]))

def rsi(c, n):
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=1/n, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))

def member_mask(idx, s):
    m = np.zeros(len(idx), bool)
    for i, a in enumerate(months):
        b = months[i + 1] if i + 1 < len(months) else pd.Timestamp("2100-01-01")
        if s in members[a]:
            m |= (idx >= a) & (idx < b)
    return m

_n = data_prices.load("NIFTY50")
NIFTY_UP = (_n["close"] > _n["close"].rolling(200).mean())
NIFTY_RSI2 = rsi(_n["close"], 2)
TOP100 = {a: set(g.nsmallest(100, "rank")["symbol"]) for a, g in u.groupby("asof")}
def top100_mask(idx, s):
    m = np.zeros(len(idx), bool)
    for i, a in enumerate(months):
        b = months[i + 1] if i + 1 < len(months) else pd.Timestamp("2100-01-01")
        if s in TOP100[a]:
            m |= (idx >= a) & (idx < b)
    return m
STRATS = {}
def strat(name):
    def deco(f): STRATS[name] = f; return f
    return deco

# each returns (entry_signal bool Series, exit_rule bool Series) on adjusted daily bars
def nup(d): return NIFTY_UP.reindex(d.index).fillna(False)
def base(d):
    c = d["close"]; return (c > c.rolling(200).mean()) & (rsi(c, 2) < 2) & nup(d)
@strat("D RSI2<2 + Nifty>200 | exit>SMA5 (best so far)")
def w0(d): return base(d), d["close"] > d["close"].rolling(5).mean()
@strat("H D + Nifty RSI2<20 (market dipped too)")
def w1(d): return base(d) & (NIFTY_RSI2.reindex(d.index) < 20), d["close"] > d["close"].rolling(5).mean()
@strat("I D + 10% above SMA200 (strong stock)")
def w2(d): c = d["close"]; return base(d) & (c > 1.10 * c.rolling(200).mean()), c > c.rolling(5).mean()
@strat("J D + 3 down days")
def w3(d):
    c = d["close"]; down3 = (c < c.shift(1)) & (c.shift(1) < c.shift(2)) & (c.shift(2) < c.shift(3))
    return base(d) & down3, c > c.rolling(5).mean()
@strat("K D | exit RSI2>70")
def w4(d): return base(d), rsi(d["close"], 2) > 70
@strat("L D + top100")
def w5(d): return base(d) & pd.Series(top100_mask(d.index, d.attrs["sym"]), index=d.index), d["close"] > d["close"].rolling(5).mean()
@strat("M D + Nifty RSI2<20 + 10% above SMA200")
def w6(d): c = d["close"]; return base(d) & (NIFTY_RSI2.reindex(d.index) < 20) & (c > 1.10 * c.rolling(200).mean()), c > c.rolling(5).mean()

def run(stop_atr=None, max_days=10):
    out = {k: [] for k in STRATS}
    for s in syms:
        d = data_prices.load(s)
        if d is None or len(d) < 260: continue
        f = (d["adj_close"] / d["close"]).fillna(1.0)
        d = pd.DataFrame({"open": d["open"]*f, "high": d["high"]*f, "low": d["low"]*f, "close": d["adj_close"], "volume": d["volume"]}).dropna()
        d = d[d.index >= "2012-06-01"]
        d.attrs["sym"] = s
        if len(d) < 260: continue
        mm = member_mask(d.index, s)
        tr = pd.concat([d.high-d.low, (d.high-d.close.shift()).abs(), (d.low-d.close.shift()).abs()], axis=1).max(axis=1)
        atr = tr.rolling(14).mean().values
        o, h, l, c = (d[k].values for k in ("open","high","low","close"))
        for name, fn in STRATS.items():
            ent, ex = fn(d); ent = (ent.fillna(False).values & mm); ex = ex.fillna(False).values
            i = 0; n = len(d)
            while i < n - 2:
                if ent[i]:
                    e = o[i+1]; stop = e - stop_atr*atr[i] if stop_atr else None
                    j = i + 1; px = None
                    while j < n - 1:
                        if stop is not None and l[j] <= stop: px = min(stop, o[j]) if o[j] < stop else stop; break
                        if ex[j] or j - (i+1) >= max_days - 1: px = o[j+1]; break
                        j += 1
                    if px is None: break
                    out[name].append((d.index[i+1], px/e - 1 - COST, j - i))
                    i = j + 1
                else:
                    i += 1
    return out

if __name__ == "__main__":
    stop = float(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1] != "none" else None
    res = run(stop_atr=stop)
    rows = []
    for k, v in res.items():
        df = pd.DataFrame(v, columns=["date","ret","days"])
        if not len(df): continue
        dev, hold = df[df.date < "2023-11-01"], df[df.date >= "2023-11-01"]
        yrs = df.groupby(df.date.dt.year)["ret"].apply(lambda r: (r > 0).mean()*100)
        rows.append({"strategy": k, "trades": len(df), "win%": round((df.ret>0).mean()*100,1),
                     "avg%": round(df.ret.mean()*100,2), "avg_win%": round(df.ret[df.ret>0].mean()*100,2),
                     "avg_loss%": round(df.ret[df.ret<=0].mean()*100,2), "days": round(df.days.mean(),1),
                     "dev_win%": round((dev.ret>0).mean()*100,1), "dev_avg%": round(dev.ret.mean()*100,2),
                     "HOLDOUT_win%": round((hold.ret>0).mean()*100,1), "HOLDOUT_avg%": round(hold.ret.mean()*100,2),
                     "worst_year_win%": round(yrs.min(),1)})
    print(pd.DataFrame(rows).to_string(index=False))
