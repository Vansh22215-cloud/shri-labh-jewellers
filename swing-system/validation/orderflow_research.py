"""D103 research: do ORDER-FLOW ideas (the Tredye 'Market Pulse' kind) improve the system's trades on NSE data?

Tested on 13 years of daily data, point-in-time top-300 liquidity universe, entry at the NEXT open, 0.35% costs,
development = before 2023-11, HOLDOUT = 2023-11 onwards (never used to choose). Ideas:
  * order blocks  - the last down candle before a strong up move (>= 1.5 ATR in 3 days that breaks the 10-day high);
                    its range is a 'demand zone'; first return of price into the zone = the 'call'
  * stock money flow (buy/sell pressure from daily bars) - Chaikin money flow (20 days)
  * sector money flow - the stock's sector's 20-day equal-weight return vs Nifty
  * market breadth   - share of the top-300 stocks above their 50-day average (risk-on / risk-off)
Bid/ask depth pressure (Kite's live buy/sell quantities) has no history anywhere, so it can only be recorded live
(shadow) - see swing/orderflow.py.
Usage: python validation/orderflow_research.py
"""
import json
import sys

import numpy as np
import pandas as pd

ROOT = "/home/user/shri-labh-jewellers/swing-system"
sys.path.insert(0, ROOT)
from swing import data_prices  # noqa: E402
from swing.orderflow import cmf, order_block_touches  # noqa: E402

COST, MAX_DAYS, STOP_ATR = 0.0035, 10, 4.0
HOLD = "2023-11-01"
u = pd.read_csv(f"{ROOT}/data/universe_history.csv")
u["asof"] = pd.to_datetime(u["asof"])
u = u[u["rank"] <= 300]
members = {a: set(g["symbol"]) for a, g in u.groupby("asof")}
months = sorted(members)
syms = sorted(set(u["symbol"]))


def rsi(c, n=2):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def member_mask(idx, s):
    m = np.zeros(len(idx), bool)
    for i, a in enumerate(months):
        b = months[i + 1] if i + 1 < len(months) else pd.Timestamp("2100-01-01")
        if s in members[a]:
            m |= (idx >= a) & (idx < b)
    return m


def sector_of(s):
    try:
        return json.load(open(f"{ROOT}/data/fundamentals/{s}.json")).get("sector") or None
    except Exception:
        return None


n = data_prices.load("NIFTY50")
NC = n["close"]
NIFTY_UP, NIFTY_R2, NIFTY_R20 = NC > NC.rolling(200).mean(), rsi(NC), NC.pct_change(20)

# ---- load everything once ---------------------------------------------------------------------------------------
D = {}
for s in syms:
    d = data_prices.load(s)
    if d is None or len(d) < 260:
        continue
    f = (d["adj_close"] / d["close"]).fillna(1.0)
    d = pd.DataFrame({"open": d["open"] * f, "high": d["high"] * f, "low": d["low"] * f, "close": d["adj_close"],
                      "volume": d["volume"]}).dropna()
    d = d[d.index >= "2012-06-01"]
    if len(d) >= 260:
        D[s] = d
print("stocks loaded:", len(D), file=sys.stderr)

closes = pd.DataFrame({s: d["close"] for s, d in D.items()})
MEM = pd.DataFrame({s: member_mask(closes.index, s) for s in D}, index=closes.index)
above50 = (closes > closes.rolling(50).mean()).where(MEM)
BREADTH = above50.sum(axis=1) / MEM.sum(axis=1).replace(0, np.nan)          # share of top-300 above 50-day avg
SECT = {s: sector_of(s) for s in D}
r20 = closes.pct_change(20).where(MEM)
SECT_R20 = pd.DataFrame(index=closes.index, columns=list(D), dtype=float)
for g in set(v for v in SECT.values() if v):
    cols = [s for s in D if SECT[s] == g]
    SECT_R20[cols] = np.repeat(r20[cols].mean(axis=1).to_numpy()[:, None], len(cols), 1)
SECT_RS = SECT_R20.sub(NIFTY_R20.reindex(closes.index), axis=0)              # sector 20-day return minus Nifty's


def trades(sym, d, ent, exit_rule, stop=None, target=None):
    """ent: bool array; exit_rule: bool array (exit at next open); stop/target: arrays of price levels (optional)."""
    o, h, l, c = (d[k].values for k in ("open", "high", "low", "close"))
    tr = pd.concat([d.high - d.low, (d.high - d.close.shift()).abs(), (d.low - d.close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean().values
    out, i, N = [], 0, len(d)
    while i < N - 2:
        if not ent[i]:
            i += 1
            continue
        e = o[i + 1]
        st = stop[i] if stop is not None else e - STOP_ATR * atr[i]
        tg = target[i] if target is not None else None
        if not (st < e) or (tg is not None and not tg > e):
            i += 1
            continue
        j, px = i + 1, None
        while j < N - 1:
            if l[j] <= st:
                px = min(st, o[j]); break
            if tg is not None and h[j] >= tg:
                px = max(tg, o[j]); break
            if exit_rule[j] or j - (i + 1) >= MAX_DAYS - 1:
                px = o[j + 1]; break
            j += 1
        if px is None:
            break
        out.append((d.index[i + 1], sym, px / e - 1 - COST, j - i))
        i = j + 1
    return out


R = {}


def add(name, rows):
    R.setdefault(name, []).extend(rows)


for s, d in D.items():
    c = d["close"]
    idx = d.index
    mm = MEM[s].reindex(idx).fillna(False).values
    nup = NIFTY_UP.reindex(idx).fillna(False).values
    nr2 = NIFTY_R2.reindex(idx).values
    s200, s5 = c.rolling(200).mean(), c.rolling(5).mean()
    hp = ((c >= 1.10 * s200) & (rsi(c) < 2)).values & nup & (nr2 < 20) & mm       # the live D98 rule
    ex5 = (c > s5).values
    ob_touch, ob_low, ob_high = order_block_touches(d)
    near_ob = pd.Series(ob_touch, index=idx).rolling(3).max().fillna(0).astype(bool).values   # touched in last 3 days
    flow = cmf(d).values
    srs = SECT_RS[s].reindex(idx).values
    br = BREADTH.reindex(idx).values

    add("A  HP dip-buy (live rule, baseline)", trades(s, d, hp, ex5))
    add("B  HP + at a bullish order block", trades(s, d, hp & near_ob, ex5))
    add("C  HP + NOT at an order block", trades(s, d, hp & ~near_ob, ex5))
    add("D  HP + stock money flow positive (CMF>0)", trades(s, d, hp & (flow > 0), ex5))
    add("E  HP + stock money flow negative", trades(s, d, hp & (flow <= 0), ex5))
    add("F  HP + sector stronger than Nifty (20d)", trades(s, d, hp & (srs > 0), ex5))
    add("G  HP + sector weaker than Nifty", trades(s, d, hp & (srs <= 0), ex5))
    add("H  HP + breadth risk-on (>50% above 50d)", trades(s, d, hp & (br > 0.5), ex5))
    add("I  HP + breadth risk-off", trades(s, d, hp & (br <= 0.5), ex5))
    # standalone order-block 'calls': buy the first return into a fresh demand zone, stop under it, target 2R
    up = (c > s200).values & nup & mm
    stop = ob_low * 0.995
    ent = ob_touch & up
    e_ref = c.values                                    # 2R measured from the signal close
    tgt = e_ref + 2 * (e_ref - stop)
    add("J  ORDER-BLOCK CALL alone: stop under zone, target 2R", trades(s, d, ent, np.zeros(len(d), bool), stop, tgt))
    add("K  ORDER-BLOCK CALL alone: stop under zone, exit >SMA5", trades(s, d, ent, ex5, stop))
    add("L  ORDER-BLOCK CALL + money flow + sector strong, target 2R",
        trades(s, d, ent & (flow > 0) & (srs > 0), np.zeros(len(d), bool), stop, tgt))


def stats(v):
    df = pd.DataFrame(v, columns=["date", "sym", "ret", "days"])
    if not len(df):
        return None
    dev, hold = df[df.date < HOLD], df[df.date >= HOLD]
    yrs = df.groupby(df.date.dt.year)["ret"].apply(lambda r: (r > 0).mean() * 100)
    w = lambda x: round((x.ret > 0).mean() * 100, 1) if len(x) else None
    a = lambda x: round(x.ret.mean() * 100, 2) if len(x) else None
    return {"trades": len(df), "win%": w(df), "avg%": a(df), "dev_n": len(dev), "dev_win%": w(dev), "dev_avg%": a(dev),
            "hold_n": len(hold), "HOLD_win%": w(hold), "HOLD_avg%": a(hold), "worst_yr_win%": round(yrs.min(), 1),
            "days": round(df.days.mean(), 1)}


rows = [dict(idea=k, **st) for k, v in R.items() if (st := stats(v))]
out = pd.DataFrame(rows)
print(out.to_string(index=False))
out.to_csv(f"{ROOT}/validation/orderflow_results.csv", index=False)
