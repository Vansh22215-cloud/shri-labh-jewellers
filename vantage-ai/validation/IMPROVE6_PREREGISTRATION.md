# Round 6: the market-weather rule for VANTAGE tips (written 18 Nov 2026, BEFORE running)
The monthly basket's cash rule (no new buys while NIFTY is below its 200-day average) cut its worst fall sharply. Does the same rule improve VANTAGE signals?
- **G1:** skip VANTAGE BUY signals on days when NIFTY closes below its 200-day average. This is applied to the existing baseline trades (`trades_FINAL.csv`) by signal date; exits are unchanged.
- **G2:** the same rule applied to Breakout and RCP signals only; dip-buys are kept, since they are meant for falls.
- **PASS, judged separately for each rule, requires all of the following:**
  1. In the holdout, profit per trade is higher and the win rate is not lower.
  2. At least 70% of the trades are kept.
  3. In development, profit per trade is higher.
  4. The worst run of losses (the `dd_1pct` measure) is not deeper in either period.
