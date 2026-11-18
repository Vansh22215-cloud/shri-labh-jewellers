# Round 19: limit open trades per sector (written 18 Nov 2026, BEFORE running)
## Exploration that led here (development and holdout utilisation only, no returns compared)
- Money in trades averages 90–98%; idle money is not a weak spot.
- The next weak spot is the size of the worst fall (about −20%). Concentration in one sector is a likely cause.

## Rule
- Sector = the industry in NSE's Nifty 500 list (`swing-system/data/events/nifty500.csv`).
- A new trade is skipped when that sector already has the maximum number of open trades:

| ID | Maximum open trades per sector |
|---|---|
| K3 | 3 |
| K2 | 2 |

- Stocks outside the Nifty 500 list (no sector) are not capped.

## Test
- The ₹45,000 account, the same logic as `improve10.sim` plus the sector check.
- Random order, median of 15 runs.
- Trade sets: top-300 (`trades_FINAL.csv`) and all stocks (`improve_trades_U2.csv`). Development and holdout.

## PASS
In both periods and both sets:
1. the worst fall is ≥ 2.0 points SMALLER, and
2. yearly growth is no more than 1.0 point lower.

This is a risk rule, so it is judged on falls.
