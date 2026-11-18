# Round 20: protect profits so winners don't turn into losers (written 18 Nov 2026, BEFORE running)
## Why (the Learner's mistake census, `mistake_census.py` / `.json`, all 13 years)
- **Biggest fixable cause of lost money:** "gave back a profit" (trades up ≥ 3% that then lost). It accounts for 37–38% of all money lost (all stocks) and 20–25% (top-300), in development AND holdout.
- **Earlier test:** E1 (round 1, break-even at +1R ≈ +16% for trend trades) was judged per trade only and failed.

## Variants
Uses the replica's `beAtR` (stop raised to the entry price once the high reaches entry + k × the initial risk). It applies to trend, breakout and pullback trades, as in E1.

| ID | k | Trend trades | Breakouts |
|---|---|---|---|
| G1 | 0.3 | ≈ +5% | ≈ +3% |
| G2 | 0.5 | ≈ +8% | ≈ +5% |

New replica runs are made on both trade sets (top-300 `iv.universe`, all stocks `improve.all_stocks` = the U2 universe).

## Test
- The ₹45,000 account (`improve10.sim`): random order, median of 15 runs.
- Compared against `trades_FINAL.csv` / `improve_trades_U2.csv`.

## PASS
In both periods and both sets:
1. yearly growth ≥ today + 1.0 point, and
2. the worst fall is no more than 2.0 points deeper.
