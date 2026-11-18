"""E4 on OFFICIAL NSE daily files, every year 2013 -> 2026: per trade and Rs 45,000 account (5 a day, 0.2% slippage)."""
import glob
import numpy as np
import pandas as pd
parts = []
for f in sorted(glob.glob('/home/user/shri-labh-jewellers/swing-system/data/bhavcopy/*.csv')):
    try:
        d = pd.read_csv(f, parse_dates=['date'])
        if len(d):
            parts.append(d[d.series == 'EQ'][['symbol', 'date', 'open', 'close', 'value']])
    except Exception:
        pass
B = pd.concat(parts).sort_values(['symbol', 'date'])
cal = sorted(B.date.unique())
prev_day = {cal[i]: cal[i - 1] for i in range(1, len(cal))}
B['prev'] = B.groupby('symbol').close.shift()
B['pdate'] = B.groupby('symbol').date.shift()
B['turn'] = B.groupby('symbol').value.transform(lambda v: v.rolling(20, min_periods=20).mean().shift(1))
B = B[B.pdate == B.date.map(prev_day)]
B['gap'] = B.open / B.prev - 1
S = B[(B.gap <= -0.02) & (B.gap > -0.08) & (B.turn >= 1e8)].copy()
S['r'] = S.close / (S.open * 1.002) - 1 - 0.002
rng = np.random.default_rng(1)
S['k'] = rng.random(len(S))
rows = []
for y, x in S.groupby(S.date.dt.year):
    pick = x.sort_values('k').groupby('date').head(5)
    day = pick.groupby('date').r.sum() / 5
    eq = (1 + day).cumprod()
    rows.append(dict(year=y, trades=len(x), per_trade=round(x.r.mean() * 100, 2), win=round((x.r > 0).mean() * 100, 1),
                     account_year=round((eq.iloc[-1] - 1) * 100, 1), worst_fall=round((eq / eq.cummax() - 1).min() * 100, 1)))
R = pd.DataFrame(rows)
print(R.to_string(index=False))
R.to_csv('verify_e4_full.csv', index=False)
