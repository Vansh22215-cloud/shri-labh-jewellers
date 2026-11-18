# Round 11: new short-term ideas from research (written 18 Nov 2026, BEFORE running)
**Owner, 18 Nov:** "hunt for other ones across the internet... run tests... do whatever it takes."

**Periods:** development = before 1 Nov 2023, holdout = 1 Nov 2023 →.

## E1 Pre-results run-up (earnings announcement premium)
**Research:** Sehgal & Bijoy 2015 and Kundu et al. 2021 find stocks rise before results in India.

- **Data:** results dates in `data/events/earnings` (506 companies). R = the first trading day on or after the results date.
- **Trade:** buy at the open 4 trading days before R; sell at the close of the trading day before R. The results reaction itself is avoided.
- **Costs:** 0.35%.
- **Filter:** ≥ ₹2 cr/day.
- **Caveat:** in live use the date must be known ≥ 4 trading days ahead (NSE board-meeting intimations; the system already reads the NSE event calendar).
- **PASS requires all of:**
  - holdout ≥ +1.0% per trade after costs,
  - profit factor ≥ 1.3 in both periods,
  - ≥ 100 holdout trades,
  - development > 0.

## E3 Bonus-share announcement
**Research:** the most consistent positive announcement effect in Indian event studies.

- **Event:** the first NSE announcement in 90 days for a company that mentions "bonus" (`data/events/history/bonus`).
- **Trade:** buy at the next open; sell at the open 5 trading days later.
- **Costs and filter:** 0.35%, ≥ ₹2 cr/day.
- **PASS:** the same as E1, but with ≥ 40 holdout trades.

## E4 / E5 Opening-gap reversal, intraday (bought or sold at the open, closed at the close the same day)
**Research:** Li & Wolfe (the opening reversal is concentrated after negative overnight returns); Kudryavtsev (big opening gains lead to weak open-to-close).

- **Stocks:** all NSE stocks (`improve.all_stocks`) with ≥ ₹10 cr/day average traded value, because intraday needs liquidity.
- **Gap** = raw open ÷ previous raw close − 1.
- **E4 (buy):**
  - **Signal:** gap ≤ −2% and > −8%.
  - **Trade:** buy at the open, sell at the close.
- **E5 (intraday short):**
  - **Signal:** gap ≥ +2% and < +8%.
  - **Trade:** sell short at the open, buy back at the close. This is allowed intraday in India.
- **Costs:** 0.20% per round trip (intraday charges plus slippage).
- **PASS, each judged separately, requires all of:**
  - holdout ≥ +0.30% per trade after costs,
  - profit factor ≥ 1.2 in both periods,
  - ≥ 5 trades a week in the holdout,
  - development > 0.

## After the test
Nothing is applied without the owner's yes.
