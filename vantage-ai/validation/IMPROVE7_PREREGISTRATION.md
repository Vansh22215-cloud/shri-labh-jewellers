# Round 7: how the trend-follow (RCP) trades end (written 18 Nov 2026, BEFORE running)
**What we saw on 18 Nov, in exploration of `trades_FINAL.csv`:**
- 2,550 RCP trades ended on the RCP SELL signal, averaging −5.1%.
- 2,334 trades ran to the 60-day limit, averaging +19.1%.

**Question:** does the SELL signal cut trades that would have recovered, and does the 60-day limit cut winners?

## Variants (only RCP exits change; everything else as live)
| ID | Exit rule |
|---|---|
| X1 | No RCP SELL; exit at the stop or after 60 days |
| X2 | RCP SELL kept; time limit 120 days |
| X3 | No RCP SELL; time limit 120 days |
| X4 | RCP SELL counts only after 20 days in the trade |
| X5 | RCP SELL kept, 120 days, and the stop trails 5 ATR below the highest price since entry |

Implementation: "no RCP SELL" is `rcpSellMinDays` = 10,000.

## Measures
On RCP trades: profit per trade, win %, profit per day held (capital is limited), and the worst run of losses.

## PASS requires all of the following
1. In the holdout, profit per trade AND profit per day held are both higher than today's.
2. The worst run of losses is not more than 10% deeper.
3. Profit per trade is also higher in development.

A pass is only reported to the owner. Nothing changes without his yes.
