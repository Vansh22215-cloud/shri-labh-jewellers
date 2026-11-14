"""D105 part 3: combine the confirmations that helped the dip-buy into tiers - tested together, not stacked blindly."""
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd

ROOT = "/home/user/shri-labh-jewellers/swing-system"
sys.path.insert(0, ROOT)
sys.path.insert(0, f"{ROOT}/validation")
import indicator_confluence as C  # noqa: E402
import indicator_lab as L  # noqa: E402
from swing.orderflow import order_block_touches  # noqa: E402


def one(args):
    sym, d, m = args
    o, h, l, c, v = (d[k].values.astype(float) for k in ("open", "high", "low", "close", "volume"))
    cs = d["close"]
    idx = d.index
    hp = (cs >= 1.10 * cs.rolling(200).mean()).values & (C.rsi(c) < 2) & C.NUP.reindex(idx).fillna(False).values \
        & (C.NR2.reindex(idx).values < 20) & m
    if not hp.any():
        return []
    st = C.states(o, h, l, c, v, idx)
    t, _, _ = order_block_touches(d)
    ob = pd.Series(t).rolling(3, min_periods=1).max().fillna(0).astype(bool).values
    F = {"vix": st["Vix Fix spike (fear) in last 3 days"], "wt": st["WaveTrend oversold (< -53)"],
         "msb": st["Market Structure Break & Order Block - EmreKb = BUY in last 5 days"],
         "fvg": st["Smart Money Concepts - LuxAlgo: FVG retest = BUY in last 5 days"],
         "swing": st["Swing high/low support-resistance (5) - hold = BUY in last 5 days"], "ob": ob,
         "sqz": st["Squeeze ON (compression)"], "st": st["SuperTrend (10,3) - KivancOzbilgic = bullish"]}
    out = []
    for date, ret, bars in C.hp_trades(d, hp):
        i = idx.get_loc(date) - 1                       # signal bar
        out.append(dict(date=date, ret=ret, **{k: bool(x[i]) for k, x in F.items()}))
    return out


if __name__ == "__main__":
    rows = []
    with Pool(4) as p:
        for r in p.imap_unordered(one, list(L.daily_universe()), chunksize=2):
            rows += r
    df = pd.DataFrame(rows)
    df.to_csv(f"{ROOT}/validation/hp_trade_features.csv", index=False)
    strong = df.ob | df.wt | df.msb | df.swing
    tiers = {"ALL (current rule)": df.ret == df.ret,
             "A: fear spike + (order block / WaveTrend oversold / MSB-OB / swing-low hold)": df.vix & strong,
             "B: fear spike, no strong zone": df.vix & ~strong,
             "C: NO fear spike, strong zone": ~df.vix & strong,
             "D: NO fear spike, no strong zone": ~df.vix & ~strong,
             "B2: fear spike + FVG retest (no strong)": df.vix & ~strong & df.fvg,
             "x: Squeeze ON": df.sqz, "x: SuperTrend bullish": df.st,
             "A or B minus Squeeze ON": df.vix & ~df.sqz}
    H = "2023-11-01"
    res = []
    for k, msk in tiers.items():
        g = df[msk]
        dv, ho = g[g.date < H], g[g.date >= H]
        yrs = g.groupby(pd.to_datetime(g.date).dt.year)["ret"].apply(lambda r: (r > 0).mean() * 100)
        res.append({"tier": k, "trades": len(g), "win%": round((g.ret > 0).mean() * 100, 1),
                    "avg%": round(g.ret.mean() * 100, 2), "dev_win%": round((dv.ret > 0).mean() * 100, 1),
                    "HOLD_win%": round((ho.ret > 0).mean() * 100, 1), "HOLD_avg%": round(ho.ret.mean() * 100, 2),
                    "worst_year_win%": round(yrs.min(), 1)})
    pd.set_option("display.width", 250)
    pd.set_option("display.max_colwidth", 90)
    print(pd.DataFrame(res).to_string(index=False))
