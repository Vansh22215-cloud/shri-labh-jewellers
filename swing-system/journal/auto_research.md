> **INVALID FOR DECISIONS (marked 20 Nov 2026):** this run (19 Nov, 8:39 pm) used MIXED data - 91% of stocks Kite + Yahoo gap-filling, 9% Yahoo only, 0% Kite only - before the strict-Kite rule reached the research job. Kept for the record; its numbers are not used. The next run is strict Kite only, once Kite history is complete.

# Automatic research (2026-11-19 20:39 IST)

Runs every week on GitHub by itself (vantage-ai/validation/autoresearch.py, rulebook AUTO_LAB_PROTOCOL.md).

**Data used: daily prices of 2,645 stocks - Kite only 0 (0%), Kite + Yahoo for missing days 2,401 (91%), Yahoo only 244 (9%; Kite history not downloaded yet or not on Kite). Delisted stocks: NSE official bhavcopies.**

- Trades rebuilt from today's prices: 33,227 (fresh top-300 trades since 20 Nov 2026: 0; step 5 starts at 150)
- Possibilities tested: 238; passed the older years: 6; passed in luck worlds (facts shuffled): [3, 2, 4]
- Passed every step: 0; new proposals sent to the owner: 0
- Current system, recent years: top-300 8.7% a year, all stocks 1.5%

## Step-1 survivors and their later steps

| Rule | Recent top-300 | Recent all | Years | Placebo | Fresh | Live-ready | Verdict |
|---|---|---|---|---|---|---|---|
| LAB-05DF Skip VANTAGE buys when the distance from the 52-week high is below -0.086 | 8.6% | 4.4% | 9 of 14 | 19 of 20 | needs 150 | yes | fail |
| LAB-42DC When money is short, take the VANTAGE buys with the highest distance from the 52-week high first | 11.9% | 1.4% | 9 of 14 | - | needs 150 | yes | fail |
| LAB-5880 When money is short, take the VANTAGE buys with the highest volume vs normal first | 11.3% | -4.4% | 10 of 14 | - | needs 150 | yes | fail |
| LAB-5EE9 Skip VANTAGE buys when the share price (₹) is above 976.5 | 10.3% | 1.3% | 9 of 14 | 19 of 20 | needs 150 | yes | fail |
| LAB-2566 When money is short, take the VANTAGE buys with the highest stock past win first | 10.0% | 2.7% | 8 of 14 | - | needs 150 | no | fail |
| LAB-DA8D Skip VANTAGE buys when setup = Breakout | 8.1% | 1.4% | 8 of 14 | 20 of 20 | needs 150 | yes | fail |

## Rules and their status (strategies/lab_rules.json)
- none yet

## Earlier runs
- 2026-11-19 11:33: 230 tested, 3 passed step 1, 0 passed all, 7.5 min
- 2026-11-19 13:02: 238 tested, 2 passed step 1, 0 passed all, 9.7 min
- 2026-11-19 20:39: 238 tested, 6 passed step 1, 0 passed all, 22.3 min
