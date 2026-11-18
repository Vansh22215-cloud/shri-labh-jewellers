# Round 8: four research-backed ideas (written 18 Nov 2026, BEFORE running)
**Owner, 18 Nov:** "Yes, test #1, #2, #3 and #6." The ideas come from published research on Indian stocks.

**Shared conditions** (same data, costs and periods as rounds 1–7):
- **Trade sets:**
  - `trades_FINAL.csv`: VANTAGE signals in the point-in-time top-300, delisted stocks included.
  - `improve_trades_U.csv`: all NSE stocks with data. This is what the live scanner sees.
- **Development** = signals before 1 Nov 2023. **Holdout** = 1 Nov 2023 onward.
- **Costs:** 0.35% per trade.

## #1 Turn of the month (TOM)
- **TOM window:** a signal whose entry day falls between the last 2 trading days of a month and the 10th trading day of the next month. All other signals are "outside".
- **PASS requires all of the following:**
  - In BOTH trade sets and BOTH periods, profit per trade inside the window exceeds outside by ≥ 1.0 point.
  - The win rate inside is not lower.
  - Each group has ≥ 150 trades in each period.
- **If it passes, the use is ranking:** inside-window signals get ⭐ priority when money is short. Nothing is blocked.

## #2 Upper-circuit continuation (new tip type)
- **Signal (day t):**
  - The stock closes at its day's high (close ≥ 99.9% of the high).
  - Its close-to-close gain is within ±0.15 points of a price band: 5%, 10% or 20%.
  - Its 20-day average traded value is ≥ ₹2 cr.
  - It has at least 260 days of history.
  - It is not already in a #2 trade.
- **Entry:** next day's open. You cannot buy at the circuit itself.
- **Exit:**
  - At the open after 5 trading days held.
  - Or earlier, at the signal day's low (gap-adjusted: at the open if the open is below it).
- **Universes:** the top-300 point-in-time membership and all stocks (`improve.all_stocks`).
- **PASS (all-stock universe, the live use) requires all of the following:**
  - Holdout profit per trade ≥ +1.0% after costs.
  - Profit factor ≥ 1.3 in both periods.
  - At least 2 trades a week in the holdout.
  - Development profit per trade > 0.
- The top-300 result is reported alongside.

## #3 Results-day reaction
- **Results dates:** `data/events/earnings/*.csv` (506 companies).
- **Reaction** R = close(next trading day after the date) / close(trading day before the date) − 1.
- **3a. Drift:** the return from the close of the reaction day to the close 5 trading days later, minus the equal-weight average of all universe stocks over the same days.
  - **PASS "avoid after bad results"** if, after R ≤ −5%, the average adjusted drift ≤ −1.0% in both periods, with ≥ 100 events each.
  - **PASS "ride good results"** if, after R ≥ +5%, a 5-day trade (buy at the next open, sell at the open 5 days later, 0.35% costs, raw not adjusted) earns ≥ +1.0% per trade with profit factor ≥ 1.3 in both periods.
- **3b. Guard for VANTAGE BUYs:**
  - **Rule:** no BUY within 10 trading days after a results reaction ≤ −5%.
  - **PASS** if those signals earn ≥ 1.0 point less per trade than the other signals of the same companies (the 506 with dates), in both periods and both trade sets, with ≥ 50 such trades each.

## #6 Smaller positions when the market is in panic
- **Panic:** NIFTY's 20-day realised volatility is above the 90th percentile of its own previous 500 trading days. This uses only past data (the "conditional" form that holds up in the research).
- **Rule:** new entries on panic days use HALF the normal risk (0.5% instead of 1%).
- **Test:** the ₹45,000 account simulation (random order while cash allows, median of 15 runs) on both trade sets.
- **PASS requires both:**
  - In both periods, the worst fall is at least 2 points smaller.
  - Yearly growth is no more than 1 point lower.

## After the test
Nothing is applied without the owner's yes.
