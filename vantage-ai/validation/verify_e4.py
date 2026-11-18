"""E4 check on OFFICIAL NSE daily files (swing-system/data/bhavcopy): 2019 and Oct 2023 -> today."""
import glob
import pandas as pd
fs = sorted(glob.glob('/home/user/shri-labh-jewellers/swing-system/data/bhavcopy/*.csv'))
parts = []
for f in fs:
    if f.split('/')[-1][:4] in ('2018', '2019', '2023', '2024', '2025', '2026'):
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
B['intr'] = B.close / B.open - 1
S = B[(B.gap <= -0.02) & (B.gap > -0.08) & (B.turn >= 1e8)].copy()
S['net'] = S.intr - 0.002
out = {}
for p, m in (('2019', S.date.dt.year == 2019), ('holdout', S.date >= '2023-11-01')):
    x = S[m]
    D = x.groupby('date').net.mean()
    out[p] = dict(trades=len(x), per_trade=round(x.net.mean() * 100, 3), win=round((x.net > 0).mean() * 100, 1),
                  pf=round(x.net[x.net > 0].sum() / -x.net[x.net <= 0].sum(), 2), days=len(D),
                  avg_day=round(D.mean() * 100, 3), without_best5pct_days=round(D[D < D.quantile(.95)].mean() * 100, 3))
    print(p, out[p])
Y = pd.read_csv('improve11_gaps.csv', parse_dates=['day'])
Y = Y[(Y.gap < 0) & (Y.day >= '2023-11-01')]
M = Y.merge(B[['symbol', 'date', 'gap', 'intr']], left_on=['sym', 'day'], right_on=['symbol', 'date'], how='left', suffixes=('_y', '_nse'))
M = M.dropna(subset=['gap_nse'])
print('Yahoo holdout gap-down events found in NSE files:', len(M), 'of', len(Y))
real = M[M.gap_nse <= -0.02]
fake = M[M.gap_nse > -0.02]
print('  real gaps (NSE also <= -2%):', len(real), ' Yahoo result', round((real.intraday - .002).mean() * 100, 3), ' NSE result', round((real.intr - .002).mean() * 100, 3))
print('  not a gap in NSE data:', len(fake), ' Yahoo result', round((fake.intraday - .002).mean() * 100, 3), ' NSE result', round((fake.intr - .002).mean() * 100, 3))


# ---- robustness (post-hoc checks of the passed rule, not a new search)
print('\nSlippage: buying above the open (per trade %, after 0.2% costs):')
for p, m in (('2019', S.date.dt.year == 2019), ('holdout', S.date >= '2023-11-01')):
    x = S[m]
    print(' ', p, {f'+{s:.1f}%': round(((x.close / (x.open * (1 + s / 100)) - 1 - .002).mean()) * 100, 3) for s in (0, .1, .2, .3, .5)})
import numpy as np
nifty = B[B.symbol.isin(['NIFTYBEES'])][['date', 'gap']].set_index('date').gap
S['mkt_gap'] = S.date.map(nifty)
x = S[S.date >= '2023-11-01']
print('\nMarket also gapped down (NIFTYBEES gap <= -0.5%):', round(x[x.mkt_gap <= -0.005].net.mean() * 100, 3), len(x[x.mkt_gap <= -0.005]),
      '| market flat or up:', round(x[x.mkt_gap > -0.005].net.mean() * 100, 3), len(x[x.mkt_gap > -0.005]))
print('\nRs 45,000 account, no leverage, N stocks a day (equal money), slippage 0.2%:')
rng = np.random.default_rng(0)
for p, m in (('2019', S.date.dt.year == 2019), ('holdout', S.date >= '2023-11-01')):
    x = S[m].copy()
    x['r'] = x.close / (x.open * 1.002) - 1 - .002
    for N, how in ((3, 'biggest gaps'), (5, 'biggest gaps'), (5, 'random')):
        if how == 'random':
            x['k'] = rng.random(len(x))
            pick = x.sort_values('k').groupby('date').head(N)
        else:
            pick = x.sort_values('gap').groupby('date').head(N)
        day = pick.groupby('date').r.sum() / N          # unused slots stay in cash
        eq = (1 + day).cumprod()
        yrs = len(day) / 248
        cal_days = len(set(B[(B.date.dt.year == 2019) if p == '2019' else (B.date >= '2023-11-01')].date))
        print(f'  {p} N={N} {how}: trading days with a signal {len(day)} of {cal_days}, growth {((eq.iloc[-1]) ** (248 / cal_days) - 1) * 100:.0f}%/yr, '
              f'worst fall {((eq / eq.cummax() - 1).min()) * 100:.1f}%, worst day {day.min() * 100:.1f}%, winning days {(day > 0).mean() * 100:.0f}%')
