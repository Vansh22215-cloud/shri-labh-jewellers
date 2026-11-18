# Round 16: slightly more dip-buys (RSI(2) < 5) at the account level (written 18 Nov 2026, BEFORE running)
## Why
- Dip-buys earn 5–10× more per day of money than other types (round 10).
- The wider D2 rule (RSI < 10) added too many weak dips and failed.
- D1 (RSI < 5) is the nearer step. In round 1 its added trades won 71% (development) and 62% (holdout) at +1.47% / +0.65% each, but it was judged per trade, never in the account.

## Also recorded (exploration, not tested)
`breakout_paths.csv`: stalled breakouts (down ≥ 5% at days 15–30) are near dead money in the top-300 set (0.07–0.45× a fresh signal per day), but not in all stocks (0.8–1.0×). They are inconsistent across sets, so no rule is tested.

## Rule D1
The dip-buy trigger uses RSI(2) < 5 instead of < 2. Everything else is as live.

**Trade sets:**
- top-300: `improve_trades_D1.csv` (round 1)
- all stocks: `improve16_trades_U_D1.csv` (the same `improve.all_stocks` run with `dipRsi` = 5)

## Test
- The ₹45,000 account (`improve10.sim`): random order, median of 15 runs.
- Development and holdout.

## PASS
In both periods and both sets:
1. yearly growth ≥ today + 1.0 point, and
2. the worst fall is no more than 2.0 points deeper.
