# Automatic research (2026-11-19 13:02 IST)

Runs every week on GitHub by itself (vantage-ai/validation/autoresearch.py, rulebook AUTO_LAB_PROTOCOL.md).

- Trades rebuilt from today's prices: 36,413 (fresh top-300 trades since 20 Nov 2026: 0; step 5 starts at 150)
- Possibilities tested: 238; passed the older years: 2; passed in luck worlds (facts shuffled): [0, 0, 0]
- Passed every step: 0; new proposals sent to the owner: 0
- Current system, recent years: top-300 14.6% a year, all stocks 8.2%

## Step-1 survivors and their later steps

| Rule | Recent top-300 | Recent all | Years | Placebo | Fresh | Live-ready | Verdict |
|---|---|---|---|---|---|---|---|
| LAB-FE5A When money is short, take the VANTAGE buys with the highest daily swing first | 18.9% | 6.7% | 11 of 14 | - | needs 150 | yes | fail |
| LAB-6B46 Skip VANTAGE buys when the share price (₹) is above 980.1 | 16.6% | 5.1% | 8 of 14 | 20 of 20 | needs 150 | yes | fail |

## Rules and their status (strategies/lab_rules.json)
- none yet

## Earlier runs
- 2026-11-19 11:33: 230 tested, 3 passed step 1, 0 passed all, 7.5 min
- 2026-11-19 13:02: 238 tested, 2 passed step 1, 0 passed all, 9.7 min
