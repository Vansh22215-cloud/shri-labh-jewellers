# Rounds 3–4 results (18 Nov 2026)
**Rules:** `IMPROVE3_PREREGISTRATION.md`. **Data:** `improve3_results.json`, `improve3_trades_C1.csv`.

## Round 3: buy at the close (C1): ✅ PASSED
| | Trades | Won | Profit per trade | Profit factor |
|---|---|---|---|---|
| Baseline, development | 5,745 | 46.7% | +4.08% | 1.82 |
| **C1, development** | 5,763 | 46.7% | **+4.31%** | 1.88 |
| Baseline, holdout | 1,519 | 42.5% | +2.91% | 1.57 |
| **C1, holdout** | 1,522 | **44.2%** | **+3.24%** | **1.65** |

**Holdout by type:**

| Type | Baseline | Buy at the close |
|---|---|---|
| Breakout | +1.08% | +1.68% |
| RCP | +3.30% | +3.60% |
| Dip-buy | +3.39% | +3.37% (unchanged) |

**Applied as D125:** a 3:15–3:29 pm "buy now, before the close" alert.

**Caveat:** the test buys at the official close. NSE's closing price is the average of the last 30 minutes, so a 3:20–3:29 pm purchase is close to it but not identical. A signal that disappears in the last minutes gets a "sell at the next open" message.

## Round 4: monthly strongest-stocks portfolio
| | Development: yearly growth / worst fall | **Holdout: yearly growth / worst fall** | Years beating NIFTY | Verdict |
|---|---|---|---|---|
| NIFTY 50 | 12.0% / −29.3% | 7.4% / −14.8% | — | |
| M1 (12-month, skip 1) | 29.3% / −41.8% | 24.3% / −33.0% | 64% | ❌ worst fall too deep |
| M2 (NSE momentum style) | 33.2% / −40.1% | 16.2% / −29.6% | 71% | ❌ worst fall too deep |
| **M3 (M2 + cash when NIFTY < 200-day average)** | **24.6% / −34.2%** | **19.5% / −8.9%** | **71%** | ✅ |

**M3 by year (basket vs NIFTY, %):**
- 2013: 18.5 vs 10.7
- 2014: 104.8 vs 31.4
- 2015: 1.3 vs −4.1
- 2016: −5.8 vs 3.0
- 2017: 66.0 vs 28.6
- 2018: −24.3 vs 3.2
- 2019: −10.0 vs 12.0
- 2020: 49.2 vs 14.9
- 2021: 109.1 vs 24.1
- 2022: −4.2 vs 4.3
- 2023: 60.8 vs 20.0
- 2024: 35.0 vs 8.8
- 2025: 12.9 vs 10.5
- 2026: −5.6 vs −8.9

**Applied as D126.** Bad years happen: 2018 −24% and 2019 −10% while NIFTY rose. It is a long-run, once-a-month basket.
