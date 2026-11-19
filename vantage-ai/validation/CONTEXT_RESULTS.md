# ATLAS Context Engine - results, run 1 (19 Nov 2026)

Protocol: CONTEXT_PROTOCOL.md (committed before the run). Script: context_engine.py.

## Which similarities matter (walk-forward: each year predicted from earlier years only)

| Grouping | Top-300: spread / years positive | All stocks: spread / years positive | Matters (both) |
|---|---|---|---|
| sector | 0.89 pts / 6 of 11 | 0.08 pts / 7 of 11 | no |
| size | 0.4 pts / 8 of 11 | 2.18 pts / 7 of 11 | no |
| swing | 0.92 pts / 9 of 11 | 0.84 pts / 7 of 11 | yes |
| setup | -0.12 pts / 4 of 11 | 0.64 pts / 10 of 11 | no |
| market | -0.45 pts / 3 of 11 | -0.21 pts / 3 of 11 | no |
| behaviour6 | 0.15 pts / 6 of 11 | 2.5 pts / 8 of 11 | no |
| behaviour10 | 1.73 pts / 7 of 11 | 2.37 pts / 8 of 11 | yes |
| behaviour10 x market | 1.29 pts / 8 of 11 | 2.03 pts / 8 of 11 | yes |
| sector x market | -1.16 pts / 4 of 11 | -0.95 pts / 5 of 11 | no |
| size x swing | 1.01 pts / 7 of 11 | 2.94 pts / 10 of 11 | yes |
| behaviour10 x setup | 1.99 pts / 9 of 11 | 2.39 pts / 8 of 11 | yes |
| behaviour6 x market x setup | 0.01 pts / 5 of 11 | 2.1 pts / 9 of 11 | no |

Spread = result per trade of the third of trades whose group had the best past record, minus the worst third.

**Finding:** groups ATLAS discovered from trading behaviour (swing, beta, trend persistence, gaps, falls, size) predict the next year; **sector does not** (top-300 6 of 11 years, all stocks +0.08 points), and neither does market type alone. Stocks that trade alike matter more than stocks in the same industry.

## Rules tested on the account (only past data at every date; re-learned every year)

| Rule | Top-300 dev | Top-300 holdout | All dev | All holdout | Years better (top-300 / all) | Luck worlds (top-300 holdout) | Verdict |
|---|---|---|---|---|---|---|---|
| C-ORDER by behaviour10 x setup | 19.5% vs 18.4% | 16.6% vs 14.6% | 42.6% vs 40.0% | 11.9% vs 8.2% | 4 of 13 / 10 of 13 | [13.5, 12.4, 16.6] | fail |
| C-SKIP by behaviour10 x setup | 18.3% vs 18.4% | 14.6% vs 14.6% | 40.8% vs 40.0% | 8.2% vs 8.2% | 11 of 13 / 12 of 13 | [14.6, 14.6, 14.6] | fail |
| C-ORDER by behaviour10 | 19.4% vs 18.4% | 15.4% vs 14.6% | 42.0% vs 40.0% | 16.5% vs 8.2% | 8 of 13 / 9 of 13 | [14.7, 13.4, 17.5] | fail |
| C-SKIP by behaviour10 | 17.8% vs 18.4% | 14.6% vs 14.6% | 40.0% vs 40.0% | 8.2% vs 8.2% | 12 of 13 / 13 of 13 | [14.6, 14.6, 14.6] | fail |

- **C-ORDER by behaviour10** (take the best-behaving groups first when money is short) is the strongest lead: all stocks holdout 16.5% vs 8.2% with a smaller fall, development +2 points in both sets. It fails on the top-300 (holdout +0.8, and one luck world reached 17.5%), so it is not proposed.
- C-SKIP almost never acts (few groups have a negative shrunk past) - no effect.
- The engine re-runs every week (autoresearch) and proposes a context rule to the owner the first time it passes every step.
