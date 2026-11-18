# Round 10: use the money where it earns the most (written 18 Nov 2026, BEFORE running)
## What we saw, in development data only
Per 100 days of money tied up:
- Dip-buy A: 61–73%
- Dip-buy B: 27–37%
- RCP (trend): 7–12%
- Breakout: 5–8%

Dip-buys last about 5 days, trend and breakout trades about 60–80 days. With ₹45,000 about 70% of signals are skipped for lack of cash (round 7), so a dip-buy that arrives while the money is busy is lost.

## Test
- The ₹45,000 account simulation from rounds 7–8: 1% risk, 25% cap per stock, 0.35% costs.
- Signals are taken in random order while cash allows; median of 15 runs.
- Development (< Nov 2023) and holdout.
- Both trade sets:
  - top-300 (`trades_FINAL.csv`, wider dips `improve_trades_D2.csv`)
  - all stocks (`improve_trades_U.csv`, wider dips `improve10_trades_U_D2.csv`, made by the same `improve.all_stocks` run with `dipRsi` = 10)

| ID | Rule |
|---|---|
| V0 | today |
| V1 | **cash kept for dip-buys:** trend and breakout trades may use at most 70% of the money; dip-buys may use all of it |
| V2 | **more dip-buys:** the wider dip rule (RSI(2) < 10 instead of < 2), trade set D2 |
| V3 | V1 + V2 |
| V4 | **no breakouts** (the type that earns least per day of money) |

## PASS, per variant
In BOTH periods and BOTH trade sets:
1. yearly growth ≥ V0 + 1.0 point, and
2. the worst fall is no more than 2.0 points deeper than V0.

Also reported: new trades a week, and dip-buys taken vs skipped.

## After the test
Nothing is applied without the owner's yes.
