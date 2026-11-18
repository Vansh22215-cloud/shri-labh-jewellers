# Round 23: the Prosecutor, robustness of the live ₹2 cr/day liquidity rule (written 18 Nov 2026, BEFORE running)
**ATLAS input:** a rule that works only at its exact setting is likely luck.

## Test
- Trade set: all stocks (`improve_trades_U2.csv`).
- Each trade's 20-day average traded value is computed on its signal day from the price files.
- The ₹45,000 account (`improve10.sim`), random order, median of 15 runs, development, holdout and all years.

| Floor | Value |
|---|---|
| L0 | no floor |
| L1 | ₹1 cr |
| L2 | ₹2 cr (live) |
| L3 | ₹3 cr |
| L5 | ₹5 cr |

## Robust if
1. L1, L3 and L5 all stay within 2 points of L2's yearly growth in both periods, and
2. L0 (no floor) is not better than L2 in the holdout.

If it is fragile, the owner is told.
