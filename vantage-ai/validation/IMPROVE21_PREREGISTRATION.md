# Round 21: stress test of the live setup (written 18 Nov 2026, BEFORE running)
**Question:** do the live rules still work when execution is imperfect?

**Account:** the owner's real capital, ₹51,000, with 1% risk and a 25% cap. Random order, median of 15 runs. Top-300 trade set (where every live rule was tested); holdout and development.

## Setups
| ID | Setup |
|---|---|
| B | buy at the next open (`trades_FINAL.csv`) |
| C | buy at the 3:20 pm close (C1, `improve3_trades_C1.csv`) |
| C+A | C plus the ADD MORE second lot (day 15, +8%, sized to the real stop; the same add-on rows as round 13, on the C1 entries) |

## Stress
| ID | Condition |
|---|---|
| S0 | normal (0.35% costs) |
| S1 | costs 0.6% |
| S2 | every buy 0.3% worse |
| S3 | 30% of tips missed at random |
| S4 | S1 + S2 + S3 |

## Reported, no pass/fail
Yearly growth and worst fall for each setup and stress.

**Flag:** any stress under which C or C+A is worse than B. That would mean a live rule depends on perfect execution.
