# Round 10 results: use the money where it earns the most (18 Nov 2026): 0 of 4 passed
**Rules:** `IMPROVE10_PREREGISTRATION.md`. **Data:** `improve10_results.json`.

**Implementation note (bug found and fixed before judging):** the first run capped trend and breakout trades at 70% of the *starting* ₹45,000 for the whole run. That is not "70% of the money" once the account has grown. The cap now uses the account's value at that moment (cash plus open trades at cost). The first run is kept in `improve10_results_v1bug.json`. It made V1 look worse in development (10.9% a year) and better in the holdout (16.0%, worst fall −7.7%).

## ₹45,000 account, median of 15 random-order runs
Each cell: yearly growth / worst fall.

| | V0 today | V1 cash kept for dips | V2 more dips | V3 V1+V2 | V4 no breakouts |
|---|---|---|---|---|---|
| Top-300, development | 19.0% / −17.1% | 15.4% / **−12.3%** | 19.2% / −17.8% | 15.2% / −14.5% | 18.7% / −15.6% |
| Top-300, holdout | 14.7% / −20.1% | 12.5% / **−13.2%** | 14.7% / −18.6% | 11.1% / −15.2% | 12.4% / −18.5% |
| All stocks, development | 34.7% / −17.0% | 28.5% / **−12.4%** | 40.5% / −19.1% | 31.9% / −23.5% | 33.9% / −15.4% |
| All stocks, holdout | 11.5% / −24.1% | 11.4% / **−17.1%** | 6.3% / −21.3% | 4.5% / −20.0% | 9.4% / −23.6% |

## Verdicts
- **V1:** the worst fall is 5–7 points smaller everywhere, but yearly growth is 2–6 points lower in 3 of 4 cases. The money kept free often waits idle, because dip-buys are rare. It is **less risk, less profit**: a trade-off, not a pass.
- **V2:** more dip-buys help in older all-stock data, but hurt badly in the recent years (6.3% vs 11.5%). ❌
- **V3:** ❌
- **V4:** dropping breakouts lowers growth. ❌ Breakouts are weak per day of money, but they still add to the account.
