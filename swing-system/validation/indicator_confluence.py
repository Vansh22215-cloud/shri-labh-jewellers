"""D105 part 2: the indicators as CONFIRMATION on the system's two proven daily strategies.
  HP  - high-probability dip-buy (D98): exit first close above the 5-day average, 4 ATR stop, 10 days
  POS - positional Rolling Candle Profile BUY within 10% of the 52-week high (D104): exit on its SELL, 5 ATR, 60 days
For each indicator, the trades are split by the indicator's state on the signal day:
  trend indicators - 'bullish' = their last signal was a BUY;  event indicators - a BUY event in the last 5 days;
  extra states: Vix Fix spike (fear) in the last 3 days, WaveTrend oversold (< -53), Squeeze ON (compression).
An indicator is useful only if the confirmed trades beat the unconfirmed ones in BOTH development and holdout.
"""
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd

ROOT = "/home/user/shri-labh-jewellers/swing-system"
sys.path.insert(0, ROOT)
sys.path.insert(0, f"{ROOT}/validation")
import indicator_lab as L  # noqa: E402
from rolling_profile_research import run_trades  # noqa: E402
from swing import data_prices  # noqa: E402

HOLD = "2023-11-01"
COST = 0.0035
nf = data_prices.load("NIFTY50")["close"]
NUP = nf > nf.rolling(200).mean()
NR2 = None


def rsi(c, n=2):
    c = pd.Series(c)
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return (100 - 100 / (1 + up / dn.replace(0, np.nan))).values


NR2 = pd.Series(rsi(nf.values), index=nf.index)
SKIP = {"ICT Killzones & Pivots (TFO) - NSE first-hour high/low sweep"}


def states(o, h, l, c, v, idx):
    out = {}
    for nm, (f, kind) in L.IND.items():
        if nm in SKIP:
            continue
        try:
            s = f(o, h, l, c, v, idx)
        except Exception:
            continue
        le = np.asarray(s["le"], bool)
        se = np.asarray(s["se"], bool) if s["se"] is not None else np.zeros(len(c), bool)
        if kind in ("trend", "momentum"):
            st = np.zeros(len(c))
            cur = 0
            for t in range(len(c)):
                cur = 1 if le[t] else -1 if se[t] else cur
                st[t] = cur
            out[nm + " = bullish"] = st == 1
        else:
            out[nm + " = BUY in last 5 days"] = pd.Series(le).rolling(5, min_periods=1).max().fillna(0).astype(bool).values
    # extra states
    hc = pd.Series(c).rolling(22).max().values
    wvf = (hc - l) / hc * 100
    up = L.sma(wvf, 20) + 2 * pd.Series(wvf).rolling(20).std(ddof=0).values
    green = (wvf >= up) | (wvf >= pd.Series(wvf).rolling(50).max().values * 0.85)
    out["Vix Fix spike (fear) in last 3 days"] = pd.Series(green).rolling(3, min_periods=1).max().fillna(0).astype(bool).values
    ap = (h + l + c) / 3
    esa = L.ema(ap, 10)
    d = L.ema(np.abs(ap - esa), 10)
    wt1 = L.ema(np.nan_to_num((ap - esa) / (0.015 * np.where(d == 0, np.nan, d))), 21)
    out["WaveTrend oversold (< -53)"] = wt1 < -53
    basis = L.sma(c, 20)
    dev = 2 * pd.Series(c).rolling(20).std(ddof=0).values
    rng = L.sma(L.true_range(h, l, c), 20)
    out["Squeeze ON (compression)"] = (basis - dev > basis - 1.5 * rng) & (basis + dev < basis + 1.5 * rng)
    return out


def hp_trades(d, ent):
    """D98 rule exits: next open after the first close above SMA5, 4 ATR stop, 10 days."""
    c = d["close"]
    ex5 = (c > c.rolling(5).mean()).values
    return run_trades(d, ent, ex5, stop_atr=4.0, max_bars=10)


def one(args):
    sym, d, m = args
    o, h, l, c, v = (d[k].values.astype(float) for k in ("open", "high", "low", "close", "volume"))
    idx = d.index
    cs = d["close"]
    nup = NUP.reindex(idx).fillna(False).values
    nr2 = NR2.reindex(idx).values
    hp = (cs >= 1.10 * cs.rolling(200).mean()).values & (rsi(c) < 2) & nup & (nr2 < 20) & m
    from swing.rolling_profile import signals
    rs = signals(d, "price")
    pos = rs["buy"].values & (c >= 0.9 * cs.rolling(250).max().values) & m
    st = states(o, h, l, c, v, idx)
    res = []
    for strat, ent, fn in (("HP", hp, lambda e: hp_trades(d, e)),
                           ("POS", pos, lambda e: run_trades(d, e, rs["sell"].values, stop_atr=5.0, max_bars=60))):
        if not ent.any():
            continue
        res += [(strat, "ALL", True, x) for x in fn(ent)]
        for k, s in st.items():
            res += [(strat, k, True, x) for x in fn(ent & s)]
            res += [(strat, k, False, x) for x in fn(ent & ~s)]
    return res


if __name__ == "__main__":
    data = list(L.daily_universe())
    rows = []
    with Pool(4) as p:
        for r in p.imap_unordered(one, data, chunksize=2):
            rows += r
    df = pd.DataFrame([(a, b, c_, x[0], x[1]) for a, b, c_, x in rows], columns=["strat", "ind", "conf", "date", "ret"])
    out = []
    for (s, k), g in df.groupby(["strat", "ind"]):
        y, nn = g[g.conf], g[~g.conf]
        dv = lambda x: x[x.date < HOLD]
        ho = lambda x: x[x.date >= HOLD]
        w = lambda x: round((x.ret > 0).mean() * 100, 1) if len(x) else None
        a = lambda x: round(x.ret.mean() * 100, 2) if len(x) else None
        out.append({"strategy": s, "confirmation": k, "n_conf": len(y), "win_conf%": w(y), "avg_conf%": a(y),
                    "n_not": len(nn), "win_not%": w(nn), "avg_not%": a(nn),
                    "dev_conf%": a(dv(y)), "dev_not%": a(dv(nn)), "HOLD_conf%": a(ho(y)), "HOLD_not%": a(ho(nn)),
                    "HOLD_win_conf%": w(ho(y)), "HOLD_win_not%": w(ho(nn))})
    o = pd.DataFrame(out)
    o["helps_both"] = (o["dev_conf%"] > o["dev_not%"]) & (o["HOLD_conf%"] > o["HOLD_not%"])
    pd.set_option("display.width", 260)
    pd.set_option("display.max_colwidth", 60)
    o = o.sort_values(["strategy", "avg_conf%"], ascending=[True, False])
    print(o.to_string(index=False))
    o.to_csv(f"{ROOT}/validation/indicator_confluence.csv", index=False)
