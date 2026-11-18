# Research backlog: targeted (owner, 18 Nov 2026)
**Owner's direction:**
- "R&D in a targeted, focused area, not blind."
- "Find insights from our system, where we are weak, where there is still space."
- "Remember our goal": better trades, less risk, more profit, a good number of trades a week.

**Method:**
- Explore on development data only (signals before Nov 2023).
- Write a pre-registration.
- Judge once on the holdout, in the ₹45,000 account simulation.
- The PASS bar: yearly growth +1 point, with the worst fall no more than 2 points deeper, in both periods and both trade sets.
- The 1% risk limit is never raised.
- Apply only with the owner's yes. Talk to the owner in plain words.

## Known facts (from rounds 1–15)
- Money is the binding limit: about 70% of signals are skipped with ₹45,000.
- Dip-buys earn 5–10× more per day of money tied up, but they are rare.
- Within a signal type, no fact known on the signal day picks winners in a way that lasts (rounds 1, 9, 12, 14, 15, calibration).
- Filters that worked before 2023 often stop working afterwards. Always check the holdout and every year.
- Winning trend trades keep winning: add-to-winners is live (D133).
- The trend SELL is not leaving money behind (round 14 post-exit study).
- Yahoo opening prices before Nov 2023 are unreliable. Intraday ideas must be checked on official NSE daily files (`swing-system/data/bhavcopy`, daily 2012–2026).

## Queue (targeted)
1. ~~**Breakouts that tie up money:**~~ done: inconsistent across sets (top-300 yes, all stocks no), no test. path study of breakout trades, like the round-13 exploration. Is a breakout that has made no progress after N days dead money compared with a fresh signal?
2. ~~**More dip-buys of the same quality in all stocks:**~~ done (round 16): failed in the holdout. the per-day value of dip-buys is huge. Test RSI(2) < 5 (D1) at the account level in both trade sets. D2 (< 10) failed.
3. ~~**Add-to-winners, second step:**~~ done (round 17): near miss. Holdout +1.8 / +2.6 points, development +0.8 / −0.4. Re-check with live records later. a third lot at day 30 if up ≥ 15%. Turtles add up to 4 units. Always within the 1% limit per lot.
4. **Trades in results weeks:** do open trend trades that cross a results date behave differently? Exit-before-results test.
5. **Live record review**, weekly once tips exist:
   - tips vs the tested numbers
   - the R2 limit-entry record
   - the promoter shadow record
   - the close-call (3:20 pm) fills
6. **Kite intraday candles:** the archive stores 5-minute data daily (`archive.run_daily`). After about 3 months, test the real fill price at 3:20 pm vs the close, and 9:15 vs the open.
