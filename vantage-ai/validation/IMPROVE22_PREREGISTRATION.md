# Round 22: the swap, using opportunity cost to free money for dip-buys (written 18 Nov 2026, BEFORE running)
## Why
- Dip-buys earn 5–10× more per day of money tied up than trend trades (round 10).
- With limited money they are often skipped because the cash is in slow trend trades.
- Reserving cash (round 10 V1) failed because the reserved money sat idle.
- **The swap frees money only at the moment a dip-buy arrives,** by selling one open trend (RCP) or breakout trade.

## Variants
When a dip-buy cannot be bought for lack of cash, sell ONE open trend or breakout trade at that day's open and buy the dip with the money.

| ID | Which trade to sell |
|---|---|
| SW1 | the weakest (lowest result so far) |
| SW2 | the oldest |
| SW3 | the strongest (take its profit) |

## Test
- The account simulation (₹45,000, 1% risk, 25% cap, 0.35% costs on both trades): random order, median of 15 runs.
- Trade sets: top-300 (`trades_FINAL.csv`) and all stocks (`improve_trades_U2.csv`).
- Development, holdout, AND every calendar year 2013–2026 (the owner asked for all years).

## PASS
In both periods and both sets:
1. yearly growth ≥ today + 1.0 point, and
2. the worst fall is no more than 2.0 points deeper.

**Also reported:** the number of years in which the swap beat today.
