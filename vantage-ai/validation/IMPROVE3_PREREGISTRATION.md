# Rounds 3 and 4: pre-registration (written 17 Nov 2026, BEFORE running)

## Round 3: buy at the close instead of the next open (C1)
- **Rule:** the BUY is filled at the signal day's close; live alerts make a 3:25 pm purchase possible. Stops and exits start the next day. Everything else is unchanged. Same data, costs and periods as rounds 1–2.
- **PASS if,** on the holdout:
  1. profit per trade rises, and
  2. the win rate does not fall, and
  3. at least 90% of trades are kept.

  The same direction must hold in development.

## Round 4: monthly "strongest stocks" portfolio (separate from the signals)
**Setup:**
- **Universe:** point-in-time top-300, delisted stocks included.
- **Rebalance:** on the last trading day of each month. Buy at the next open, equal weight, 20 stocks.
- **Costs:** 0.35% on every replaced holding.

**Variants:**
| ID | Ranking |
|---|---|
| M1 | 12-month return, skipping the last month |
| M2 | NSE-momentum-index style: the average of the 6- and 12-month returns, each divided by 1-year daily volatility |
| M3 | M2, and hold cash (no stocks) for the month when NIFTY is below its 200-day average at the rebalance |

**Compared with** NIFTY 50 (price index) over the same months.

**PASS if, in BOTH development (2013 – Oct 2023) and holdout (Nov 2023+):**
1. yearly growth ≥ NIFTY's + 3 points, and
2. the worst fall (max drawdown) is no more than 10 points deeper than NIFTY's,

and it beats NIFTY in ≥ 60% of calendar years.
