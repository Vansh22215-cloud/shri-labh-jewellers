# Round 12: FII positioning in index futures as market weather (written 18 Nov 2026, BEFORE running)
**Data:** NSE participant-wise open interest, daily from 2013 (`swing-system/data/participant_oi`).

**Measure:** FII long share = FII index-futures long ÷ (long + short), at the close of the signal day. It is known that evening, because NSE publishes the file after the close. It is compared with its own previous 250 trading days, as a percentile.

| ID | Rule |
|---|---|
| F1 | Skip VANTAGE BUYs when the FII long share is in the bottom 20% of its past year (FIIs unusually bearish) |
| F2 | Skip VANTAGE BUYs when it is in the top 20% (FIIs unusually bullish: the contrarian reading) |

## PASS, per rule
In both trade sets (top-300, all stocks) and both periods (development < Nov 2023, holdout):
1. the skipped signals earn ≥ 1.0 point per trade LESS than the kept signals, and
2. there are ≥ 100 skipped signals.

Also reported: the ₹45,000 account result (random order, median of 15 runs) with the rule applied.

## After the test
Nothing is applied without the owner's yes.
