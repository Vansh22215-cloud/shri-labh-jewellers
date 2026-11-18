# Round 13: add to winning trend trades (pyramiding) (written 18 Nov 2026, BEFORE the holdout was looked at)
## Why (exploration on development data only, `recycle_explore.py`)
- **Losing trend trades are not dead money.** At days 10–40, their remaining profit per day is about the same as a fresh trend signal's (0.6–1.1×). Cutting them early cannot help, which matches the earlier time-stop failure (E2).
- **Winning trend trades keep winning.** A trade up ≥ 8% earns more per day for the rest of its life than a fresh signal:
  - top-300: 1.43× at day 10, 1.43× at day 15, 1.22× at day 20, 1.51× at day 30, 1.29× at day 40
  - all stocks: 1.26×, 1.17×, 1.16×, 1.08×, 1.04×
- **Conclusion:** with limited money, adding to a winner is a better use of cash than a new signal.

## Rule P1
- **Trigger:** at the close of trading day 15 of a trend (RCP) trade, the trade is up ≥ 8% and still open.
- **Add-on:** buy a second lot at the next open.
  - It exits together with the original trade.
  - Its stop-loss distance (%) is the same as the original's, measured from the add-on price. This is used for sizing only (1% risk, 25% cap).
- **Priority:** the add-on competes for cash like any other signal on its day, in random order.
- One add-on per trade.

## Test
- The ₹45,000 account simulation (`improve10.sim`): random order, median of 15 runs.
- Both trade sets (top-300, all stocks), development and holdout.

## PASS
In BOTH periods and BOTH sets:
1. yearly growth ≥ today + 1.0 point, and
2. the worst fall is no more than 2.0 points deeper.

## After the test
Nothing is applied without the owner's yes.
