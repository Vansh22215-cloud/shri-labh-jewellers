# Automatic research (2026-11-19 11:33 IST)

Runs every week on GitHub by itself (vantage-ai/validation/autoresearch.py, rulebook AUTO_LAB_PROTOCOL.md).

- Trades rebuilt from today's prices: 36,413 (fresh top-300 trades since 20 Nov 2026: 0; step 5 starts at 150)
- Possibilities tested: 230; passed the older years: 3; passed in luck worlds (facts shuffled): [0, 0, 1]
- Passed every step: 0; new proposals sent to the owner: 0
- Current system, recent years: top-300 16.2% a year, all stocks 11.6%

## Step-1 survivors and their later steps

| Rule | Recent top-300 | Recent all | Years | Placebo | Fresh | Live-ready | Verdict |
|---|---|---|---|---|---|---|---|
| LAB-73E5 When money is short, take the VANTAGE buys with the lowest money traded a day (₹ cr) first | 15.8% | 9.2% | 8 of 14 | - | needs 150 | yes | fail |
| LAB-70BC When money is short, take the VANTAGE buys with the highest 6-month return first | 18.6% | 8.8% | 11 of 14 | - | needs 150 | yes | fail |
| LAB-6B46 Skip VANTAGE buys when the share price (₹) is above 980.1 | 17.6% | 8.3% | 9 of 14 | 20 of 20 | needs 150 | yes | fail |

## Rules and their status (strategies/lab_rules.json)
- none yet

## Earlier runs
- 2026-11-19 11:33: 230 tested, 3 passed step 1, 0 passed all, 7.5 min
