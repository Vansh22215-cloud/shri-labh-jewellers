# Round 6 results: the market-weather rule for VANTAGE signals (18 Nov 2026): ❌ not adopted
| | Development | Holdout |
|---|---|---|
| Baseline | 5,745 trades, +4.08%/trade, worst run −155 | 1,519, +2.91%, −127 |
| G1/G2 (skip BUYs while NIFTY < 200-day average) | 5,188, **+4.02%**, worst run **−173** | 1,263, +2.95%, −125 |

- G1 and G2 are identical: dip-buys never fire when NIFTY is below its 200-day average.
- **Why it fails:** the rule barely changes the holdout and makes the older years worse. VANTAGE already has its own market checks, so the cash rule only helps the monthly basket.
