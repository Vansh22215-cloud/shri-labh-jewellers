# Round 9 results: event signals from NSE disclosures (18 Nov 2026): 0 of 7 passed, 1 near miss
**Rules:** `IMPROVE9_PREREGISTRATION.md`. **Data:** `improve9_results.json`, `improve9_events_*.csv`.

## Standalone trades (buy the next open, sell 5 days later, 0.35% costs, stocks ≥ ₹2 cr/day)
| # | Event | Development | Holdout | Verdict |
|---|---|---|---|---|
| 4 | Promoter market purchase ≥ ₹10 lakh | 2,881 trades, 52% won, **+0.88%**, PF 1.42 | 862 trades, 52% won, **+0.81%**, PF 1.40 | ❌ **near miss** |
| 5 | Bulk-deal buy ≥ ₹1 cr | 2,363, −0.11%, PF 0.97 | 1,708, −0.13%, PF 0.96 | ❌ |
| 9 | Buyback announcement | 370, −1.08%, PF 0.56 | 85, +0.21%, PF 1.11 | ❌ |
| 8 | Index inclusion (announcement → day before effective, ~22 days) | 397, −0.78%, PF 0.87 | 348, −0.68%, PF 0.85 | ❌ |

- **#4 (near miss):** below the +1.0% bar, but steady. It was positive in 10 of 12 years, and the holdout matches development.
- **#8:** 2020 lost heavily (inclusions announced just before the COVID crash), and 2026 too. The years in between are mixed.

## Boosts and flags on VANTAGE BUYs
| # | Rule | Development | Holdout | Verdict |
|---|---|---|---|---|
| 4b | Promoter buy in the prior 20 days | **better:** top-300 +8.5% vs +4.0%, all stocks +8.6% vs +6.9% | **mixed:** top-300 +0.5% vs +2.9% (12 trades), all stocks +3.5% vs +2.9% | ❌ |
| 5b | Bulk-deal buy in the prior 10 days | **mixed:** top-300 +5.7% vs +4.1%, all stocks +6.4% vs +6.9% | **mixed:** top-300 −3.0% (11 trades), all stocks +5.1% vs +2.8% | ❌ |
| 10 | Promoter pledge in the prior 60 days (warning) | **not worse:** +5.5% vs +4.0% (top-300) | **not worse:** +3.8% vs +2.9% | ❌ no warning |

## Conclusion
- Nothing is adopted.
- **The one candidate is #4,** a 5-day "promoter is buying" trade: a small, steady edge of about +0.8% per trade with ~2 trades a week.
- A live shadow record would show whether it reaches the bar.
