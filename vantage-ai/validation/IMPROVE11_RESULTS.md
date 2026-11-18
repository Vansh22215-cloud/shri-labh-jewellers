# Round 11 results (18 Nov 2026): 0 of 4 passed
**Rules:** `IMPROVE11_PREREGISTRATION.md`. **Data:** `improve11_results.json`, `verify_e4*.py` / `verify_e4_full.csv`.

| # | Idea | Development | Holdout | Verdict |
|---|---|---|---|---|
| E1 | Pre-results run-up (buy 4 days before, sell the day before) | 10,585 trades, +0.01%, PF 1.00 | 4,346, +0.00%, PF 1.00 | ❌ |
| E3 | Bonus announcement (next open → 5 days) | 286, −1.48%, PF 0.57 | 157, −2.04%, PF 0.52 | ❌ the move is over by the time the news is public |
| E5 | Intraday short after a gap up of 2–8% | +0.52%, PF 1.45 | +0.27%, PF 1.23 | ❌ below +0.30% |
| E4 | Intraday buy after a gap down of 2–8% | Yahoo data: +0.52%, PF 1.43 | Yahoo +0.81%; **official NSE +0.73%**, PF 1.79 | ❌ **failed the full-history check** |

## E4: passed the pre-registered bar, then failed verification
**Holdout on official NSE daily files** (all listed stocks, so no survivorship gap):
- 14,228 trades, 58.6% won, +0.73% per trade, PF 1.79.
- Yahoo's events match NSE's events.
- **Price sensitivity:** each 0.1% paid above the open costs 0.1% per trade.

**Every year on official NSE files** (`verify_e4_full.csv`):
- Per-trade result **negative in 2015 and 2020–2023** (−0.32% to −0.63%).
- **₹45,000 account** (5 stocks a day, equal money, 0.2% over the open plus 0.2% costs): 2019 −2%, 2020 −21%, 2021 −25%, 2022 −28%, 2023 −11%, with worst falls of up to −34%. Large gains in 2013, 2017–18 and 2024–26.

**Verdict:** the edge comes and goes with the market regime, and in a real account it can lose for several years in a row. **Rejected.**

**Lesson:** Yahoo's opening prices before Nov 2023 made 2020–2023 look profitable. Intraday ideas must be checked on official NSE files for every year.
