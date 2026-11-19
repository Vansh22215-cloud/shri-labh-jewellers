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

---

# Run 2 (19 Nov 2026): real costs + 20% tax, and every way of understanding stocks side by side

| View | Top-300 spread / years + | All stocks spread / years + | Matters (both) |
|---|---|---|---|
| sector | 0.89 / 6 of 11 | 0.08 / 7 of 11 | no |
| size | 0.4 / 8 of 11 | 2.18 / 7 of 11 | no |
| swing | 0.92 / 9 of 11 | 0.84 / 7 of 11 | yes |
| setup | -0.12 / 4 of 11 | 0.64 / 10 of 11 | no |
| market | -0.45 / 3 of 11 | -0.21 / 3 of 11 | no |
| behaviour6 | 0.15 / 6 of 11 | 2.5 / 8 of 11 | no |
| behaviour10 | 1.73 / 7 of 11 | 2.37 / 8 of 11 | yes |
| behaviour10 x market | 1.29 / 8 of 11 | 2.03 / 8 of 11 | yes |
| sector x market | -1.16 / 4 of 11 | -0.95 / 5 of 11 | no |
| size x swing | 1.01 / 7 of 11 | 2.94 / 10 of 11 | yes |
| behaviour10 x setup | 1.99 / 9 of 11 | 2.39 / 8 of 11 | yes |
| behaviour6 x market x setup | 0.01 / 5 of 11 | 2.1 / 9 of 11 | no |
| company | -0.66 / 5 of 11 | -0.06 / 5 of 11 | no |
| company x setup | -1.07 / 1 of 11 | -0.23 / 4 of 11 | no |
| sector x setup | 1.34 / 8 of 11 | 2.01 / 9 of 11 | yes |
| sector x behaviour10 | 1.0 / 5 of 11 | 2.96 / 9 of 11 | no |
| market x setup | -0.81 / 5 of 11 | 0.07 / 7 of 11 | no |
| size x sector | 1.46 / 7 of 11 | 2.69 / 10 of 11 | yes |
| discovered tree (all facts) | 0.62 / 6 of 11 | 1.27 / 7 of 11 | no |

Findings:
- **The company's own past record does NOT predict** its next trades (top-300 -0.66 points, 5 of 11 years; company x setup 1 of 11). The 'X of Y past VANTAGE signals won' line in tips is information, not an edge.
- **Sector alone does not, but sector x setup and size x sector do** (a combination explains more than either part).
- Behaviour groups (alone, x setup, x market) keep mattering. The discovered tree matters only for all stocks.

| Rule (real costs + tax) | Top-300 dev | Top-300 holdout | All dev | All holdout | Years (top / all) | Luck (top-300 holdout) | Verdict |
|---|---|---|---|---|---|---|---|
| C-ORDER by behaviour10 x setup | 13.9% vs 12.8% | 8.1% vs 6.9% | 35.3% vs 30.7% | 6.3% vs 1.9% | 4 of 13 / 11 of 13 | [7.3, 7.6, 9.3] | fail |
| C-SKIP by behaviour10 x setup | 12.9% vs 12.8% | 6.9% vs 6.9% | 30.5% vs 30.7% | 1.9% vs 1.9% | 12 of 13 / 13 of 13 | [6.9, 6.9, 6.9] | fail |
| C-ORDER by behaviour10 | 13.3% vs 12.8% | 8.0% vs 6.9% | 34.7% vs 30.7% | 8.0% vs 1.9% | 6 of 13 / 7 of 13 | [6.1, 7.8, 10.4] | fail |
| C-SKIP by behaviour10 | 12.5% vs 12.8% | 6.9% vs 6.9% | 30.7% vs 30.7% | 1.9% vs 1.9% | 13 of 13 / 13 of 13 | [6.9, 6.9, 6.9] | fail |
| C-ORDER by size x sector | 13.9% vs 12.8% | 8.8% vs 6.9% | 35.5% vs 30.7% | -0.9% vs 1.9% | 7 of 13 / 9 of 13 | [6.1, 9.2, 13.9] | fail |
| C-SKIP by size x sector | 12.8% vs 12.8% | 6.9% vs 6.9% | 30.7% vs 30.7% | 1.9% vs 1.9% | 13 of 13 / 13 of 13 | [6.9, 6.9, 6.9] | fail |

None passes. Note: these trade sets are the plain next-open VANTAGE trades with fixed ₹51,000 sizing (the lab's common base), so the levels are lower than the live setup (3:20 pm + ADD MORE + dip-buys: 12.0% recent / 15.1% older after costs and tax, costs_real_results.json).
