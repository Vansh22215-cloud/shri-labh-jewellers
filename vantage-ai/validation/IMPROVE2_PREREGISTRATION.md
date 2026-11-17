# Improvement research, round 2: pre-registration (written 17 Nov 2026, BEFORE running)

**What it changes:** round 1 showed that filtering WHICH signals to take does not help on recent data. Round 2 changes HOW each trade is taken.

**Method:**
- Same base, data and costs as round 1.
- Holdout: signals from 1 Nov 2023. Development: before that.

| ID | Rule | Applies to |
|---|---|---|
| R1 | Gap guard: if the next open is more than 0.5 × ATR(signal day) above the signal close, the BUY is cancelled (no trade) | all types |
| R2 | Limit entry: buy limit at signal close − 0.25 × ATR, valid only on the next day. Filled at min(open, limit) if the day's low reaches it; otherwise no trade | all types |
| R3 | Scale-out: sell half at entry + 2R (at max(open, level)); the other half follows the normal exit | Breakout, RCP |
| R4 | Results guard: no BUY if the company's results (`data/events/earnings`) fall within the next 5 trading days. Stocks without results data are unaffected | all types |
| R5 | Slot selection (8 open positions at most): when signals compete for free slots, take Dip-buy A > Dip-buy B/C > RCP > Breakout, then the higher score. Compared with the round-1 approximation (alphabetical) | portfolio |

**Pass criteria (all after 0.35% costs):**
- **R1, R2, R4:** on the holdout,
  1. expectancy rises, and
  2. the win rate does not fall, and
  3. ≥ 50% of trades are kept.

  The same direction must hold in development.
- **R3:** on the holdout,
  1. expectancy is not lower, and
  2. drawdown at 1% risk improves or the profit factor rises.

  The same must hold in development.
- **R5:** holdout total R (sum of results in risk units) and expectancy of the 8-slot account both higher than with alphabetical selection; development the same direction.

Nothing goes live without the owner's approval.
