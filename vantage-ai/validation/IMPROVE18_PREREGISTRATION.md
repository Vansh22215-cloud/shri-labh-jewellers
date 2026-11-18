# Round 18: a tighter stop-loss for trend trades (written 18 Nov 2026, BEFORE running)
## Also recorded (backlog item 4, exploration only, `results_cross.csv`)
Open trades crossing a results date moved on average **+0.1% to +0.3%** over the 2-day reaction, in development data:
- standard deviation ≈ 5%
- worst 5% ≈ −7%
- the rest of the trade after results: +2.5% to +7.6%

Selling before results would give that up and pay costs. **No exit-before-results rule is tested.**

## Weak spot
Trend (RCP) trades that hit the stop-loss lose about −15% each, because the stop sits 5 ATR (≈ 16%) below entry. Champions (O'Neil, Minervini) use much tighter stops.

With 1% risk sizing, a tighter stop gives a bigger quantity (within the 25% cap). The risk per trade stays the same, more money is used per trade, and stop-outs happen more often.

## Variants
Only `rcpStopMult` changes; everything else is as live.

| ID | Stop |
|---|---|
| Z1 | 4 ATR |
| Z2 | 3 ATR |
| Today | 5 ATR |

New replica runs are made on both trade sets: top-300 via `iv.universe` and all stocks via `improve.all_stocks`.

## Test
The ₹45,000 account (`improve10.sim`): random order, median of 15 runs, development and holdout.

## PASS
In both periods and both sets:
1. yearly growth ≥ today + 1.0 point, and
2. the worst fall is no more than 2.0 points deeper.
