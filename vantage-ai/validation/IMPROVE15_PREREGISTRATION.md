# Round 15: Minervini's trend template on VANTAGE signals (written 18 Nov 2026, BEFORE running)
**Rule as published by Minervini (not chosen from our data).** At the signal day's close:
- price ≥ 0.75 × 52-week high,
- price ≥ 1.30 × 52-week low,
- 50-day average > 150-day average > 200-day average,
- price above the 50-day average.

| ID | Rule |
|---|---|
| T1 | Breakout signals are taken only when the template holds. Other types are unchanged. |
| T2 | Breakout AND trend (RCP) signals are taken only when the template holds. Dip-buys are unchanged, because they buy weakness by design. |

## Test
- The ₹45,000 account (`improve10.sim`): random order, median of 15 runs.
- Both trade sets, development and holdout.

## PASS
In both periods and both sets:
1. yearly growth ≥ today + 1.0 point, and
2. the worst fall is no more than 2.0 points deeper.

## After the test
Nothing is applied without the owner's yes.
