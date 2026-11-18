# Round 18 results: tighter stop for trend trades (18 Nov 2026): ❌ both
**Rules:** `IMPROVE18_PREREGISTRATION.md`. **Data:** `improve18_results.json`, `rebuild_u_baseline.json`.

**All-stocks baseline correction:** `improve_trades_U.csv` (round 1) was made before 1,480 more stocks were downloaded on 18 Nov. Variant runs made after that download contain more stocks. The baseline was rebuilt on the current data (`improve_trades_U2.csv`, 29,144 trades), and the all-stock cells of rounds 10, 16 and 18 were re-scored against it.

## ₹45,000 account
Each cell: yearly growth / worst fall.

| | Top-300, development | Top-300, holdout | All stocks (U2), development | All stocks (U2), holdout |
|---|---|---|---|---|
| Today (5 ATR) | 19.0 / −17.1 | **14.7 / −20.1** | 40.5 / −18.1 | **11.8 / −20.7** |
| Z1 (4 ATR) | 20.7 / −15.6 | 13.1 / −20.1 | 41.3 / −18.8 | 4.6 / −30.2 |
| Z2 (3 ATR) | 18.6 / −20.5 | 13.0 / −17.4 | 41.4 / −20.8 | −3.7 / −34.5 |

- **Tighter stops get hit by normal swings.** In the recent years that cost a lot of growth and deepened the falls.
- The 5 ATR stop stays.

## Re-scored all-stock cells of earlier rounds (against U2)
| | Development | Holdout | Verdict |
|---|---|---|---|
| Baseline U2 | 40.5 / −18.1 | 11.8 / −20.7 | |
| Round 10 V2 (wider dips) | 40.5 / −19.1 | 6.3 / −21.3 | still ❌ |
| Round 16 D1 (RSI < 5 dips) | 40.3 / −21.1 | 8.7 / −23.1 | still ❌ |

All verdicts are unchanged, and the numbers are clearer: no gain in development and a loss in the holdout.

**From now on, all-stock comparisons use `improve_trades_U2.csv`.**
