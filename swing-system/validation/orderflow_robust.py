"""D103 robustness: the HP dip-buy at a bullish order block - other settings and year by year."""
import sys
import numpy as np, pandas as pd
sys.argv = ["x"]
exec(open("/home/user/shri-labh-jewellers/swing-system/validation/orderflow_research.py").read().split("R = {}")[0])
R = {}
for s, d in D.items():
    c = d["close"]; idx = d.index
    mm = MEM[s].reindex(idx).fillna(False).values
    nup = NIFTY_UP.reindex(idx).fillna(False).values; nr2 = NIFTY_R2.reindex(idx).values
    hp = ((c >= 1.10 * c.rolling(200).mean()) & (rsi(c) < 2)).values & nup & (nr2 < 20) & mm
    ex5 = (c > c.rolling(5).mean()).values
    for imp in (1.0, 1.5, 2.0):
        for look in (30, 60, 120):
            t, _, _ = order_block_touches(d, look=look, impulse_atr=imp)
            for win in (1, 3, 5):
                near = pd.Series(t, index=idx).rolling(win).max().fillna(0).astype(bool).values
                R.setdefault((imp, look, win), []).extend(trades(s, d, hp & near, ex5))
rows = []
for k, v in R.items():
    df = pd.DataFrame(v, columns=["date", "sym", "ret", "days"])
    dev, ho = df[df.date < HOLD], df[df.date >= HOLD]
    rows.append({"impulse_atr": k[0], "zone_life": k[1], "touch_within_days": k[2], "trades": len(df),
                 "win%": round((df.ret > 0).mean() * 100, 1), "avg%": round(df.ret.mean() * 100, 2),
                 "dev_win%": round((dev.ret > 0).mean() * 100, 1), "HOLD_win%": round((ho.ret > 0).mean() * 100, 1),
                 "HOLD_avg%": round(ho.ret.mean() * 100, 2)})
    if k == (1.5, 60, 3):
        y = df.groupby(df.date.dt.year)["ret"].agg(["size", lambda r: round((r > 0).mean() * 100, 1), "mean"])
        print("year by year (chosen setting):\n", y.round(4).to_string())
print(pd.DataFrame(rows).to_string(index=False))
