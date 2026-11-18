# The Learner (18 Nov 2026)

Every idea tracked by swing/tracker.py, with its situation and journey (swing/learning.py). Lessons go to research; live tips change only after a passed test and the owner's yes.

## 1. Live vs the 13-year test
- VANTAGE Breakout: 0 closed of 1 (need 20 to judge); 0 of 1 open tips are deeper than 90% of tested trades -> too early
- VANTAGE Rolling Candle Profile: 0 closed of 16 (need 20 to judge); 0 of 16 open tips are deeper than 90% of tested trades -> too early

## 2. When it works and when not (bought ideas; open ones at today's value)
| Source | Situation | Value | Ideas | Average | Won |
|---|---|---|---|---|---|
| VANTAGE | market | rising | 17 | +0.20% | 18% |
| VANTAGE | market mood | calm | 17 | +0.20% | 18% |
| VANTAGE | liquidity | 10-50 cr | 4 | -0.05% | 25% |
| VANTAGE | liquidity | over 50 cr | 8 | +0.64% | 25% |
| VANTAGE | liquidity | under 10 cr | 5 | -0.31% | 0% |
| VANTAGE | from 52w high | 5-15% below | 12 | +0.63% | 17% |
| VANTAGE | from 52w high | within 5% | 5 | -0.83% | 20% |
| VANTAGE | results week | no | 17 | +0.20% | 18% |
| VANTAGE | weekday | Tue | 9 | +0.38% | 33% |
| VANTAGE | weekday | Wed | 8 | +0.00% | 0% |
| hourly scan | market | rising | 18 | -1.07% | 39% |
| hourly scan | market mood | calm | 9 | -1.48% | 33% |
| hourly scan | market mood | jumpy | 9 | -0.66% | 44% |
| hourly scan | liquidity | 10-50 cr | 4 | +0.72% | 50% |
| hourly scan | liquidity | over 50 cr | 14 | -1.58% | 36% |
| hourly scan | from 52w high | 15%+ below | 13 | -1.10% | 46% |
| hourly scan | from 52w high | 5-15% below | 5 | -1.00% | 20% |
| hourly scan | results week | no | 18 | -1.07% | 39% |
| hourly scan | weekday | Fri | 2 | -0.73% | 0% |
| hourly scan | weekday | Mon | 8 | -0.79% | 38% |
| hourly scan | weekday | Tue | 4 | -1.78% | 50% |
| hourly scan | weekday | Wed | 4 | -1.08% | 50% |
| strategy tip | market | rising | 16 | -1.75% | 44% |
| strategy tip | market mood | calm | 9 | -0.47% | 44% |
| strategy tip | market mood | jumpy | 7 | -3.40% | 43% |
| strategy tip | liquidity | 10-50 cr | 4 | -3.56% | 50% |
| strategy tip | liquidity | over 50 cr | 12 | -1.15% | 42% |
| strategy tip | from 52w high | 15%+ below | 12 | -1.92% | 50% |
| strategy tip | from 52w high | 5-15% below | 4 | -1.25% | 25% |
| strategy tip | results week | no | 16 | -1.75% | 44% |
| strategy tip | weekday | Fri | 3 | -0.46% | 33% |
| strategy tip | weekday | Mon | 3 | -1.57% | 33% |
| strategy tip | weekday | Thu | 2 | +1.00% | 100% |
| strategy tip | weekday | Tue | 1 | -0.13% | 0% |
| strategy tip | weekday | Wed | 7 | -3.40% | 43% |
| strategy tip (retired list) | market | falling | 5 | +10.72% | 100% |
| strategy tip (retired list) | market | rising | 10 | -0.49% | 30% |
| strategy tip (retired list) | market mood | jumpy | 15 | +3.24% | 53% |
| strategy tip (retired list) | liquidity | 10-50 cr | 8 | +2.67% | 50% |
| strategy tip (retired list) | liquidity | over 50 cr | 7 | +3.90% | 57% |
| strategy tip (retired list) | from 52w high | 15%+ below | 9 | +3.09% | 56% |
| strategy tip (retired list) | from 52w high | 5-15% below | 5 | +1.55% | 40% |
| strategy tip (retired list) | from 52w high | within 5% | 1 | +13.13% | 100% |
| strategy tip (retired list) | results week | no | 14 | +3.68% | 57% |
| strategy tip (retired list) | results week | yes | 1 | -2.79% | 0% |
| strategy tip (retired list) | weekday | Fri | 2 | -4.45% | 0% |
| strategy tip (retired list) | weekday | Mon | 7 | +1.19% | 43% |
| strategy tip (retired list) | weekday | Thu | 2 | +1.29% | 50% |
| strategy tip (retired list) | weekday | Tue | 1 | +13.13% | 100% |
| strategy tip (retired list) | weekday | Wed | 3 | +11.18% | 100% |

## 3. Lessons to research (evidence: weak = 2-4 cases, medium = 5-9, strong = 10+)
- [weak] hourly scan: when liquidity = 10-50 cr, ideas averaged +0.7% (n=4) vs -1.6% when over 50 cr (n=14)
- [weak] strategy tip: when liquidity = over 50 cr, ideas averaged -1.1% (n=12) vs -3.6% when 10-50 cr (n=4)
- [medium] strategy tip: when market mood = calm, ideas averaged -0.5% (n=9) vs -3.4% when jumpy (n=7)
- [weak] strategy tip: when weekday = Fri, ideas averaged -0.5% (n=3) vs -3.4% when Wed (n=7)
- [medium] strategy tip (retired list): when market = falling, ideas averaged +10.7% (n=5) vs -0.5% when rising (n=10)
- [weak] strategy tip (retired list): when weekday = Wed, ideas averaged +11.2% (n=3) vs +1.2% when Mon (n=7)
- [weak] strategy tip: 2 of 3 losing ideas - Gave back a profit - it was up 3%+ and then turned into a loss (an exit mistake)

## 4. Mistakes: why each losing idea lost (plain diagnosis)
| Mistake | Ideas | Average | Sources |
|---|---|---|---|
| Gave back a profit - it was up 3%+ and then turned into a loss (an exit mistake) | 3 | -9.1% | hourly scan, strategy tip |
| Never worked - it never rose meaningfully above the buy price (a selection mistake) | 2 | -6.7% | hourly scan, strategy tip (retired list) |
| Drifted down slowly (no clear cause) | 4 | -7.0% | hourly scan, strategy tip, strategy tip (retired list) |

- AVALON (strategy tip, recorded only, 2026-11-11): -12.4%, best point +6.1%, market -0.3% -> Gave back a profit - it was up 3%+ and then turned into a loss (an exit mistake)
- RPTECH (strategy tip, recorded only, 2026-11-11): -9.8%, best point +2.3%, market -0.3% -> Drifted down slowly (no clear cause)
- EMIL (strategy tip, recorded only, 2026-11-11): -6.3%, best point +3.6%, market -0.3% -> Gave back a profit - it was up 3%+ and then turned into a loss (an exit mistake)
- CYIENT (strategy tip (retired list), recorded only, 2026-11-05): -3.8%, best point +1.2%, market +0.8% -> Drifted down slowly (no clear cause)
- ANTELOPUS (strategy tip (retired list), 2026-11-06): -7.0%, best point +0.8%, market +0.7% -> Never worked - it never rose meaningfully above the buy price (a selection mistake)
- JAYNECOIND (strategy tip (retired list), 2026-11-09): -3.1%, best point +2.1%, market -0.1% -> Drifted down slowly (no clear cause)
- SHANTIGOLD (hourly scan, 2026-11-09): -11.2%, best point +1.6%, market -0.1% -> Drifted down slowly (no clear cause)
- EBGNG (hourly scan, recorded only, 2026-11-11): -8.6%, best point +4.4%, market -0.3% -> Gave back a profit - it was up 3%+ and then turned into a loss (an exit mistake)
- SHANTIGOLD (hourly scan, recorded only, 2026-11-17): -6.4%, best point +0.0% -> Never worked - it never rose meaningfully above the buy price (a selection mistake)

**Normal mix in the 13-year test (all stocks, Nov 2023+), share of money lost:** Gave back a profit 38%; The whole market fell 3%+ during the trade (not the stock's fault) 21%; Drifted down slowly (no clear cause) 13%; Never worked 12%; Company results came during the trade and hit the price 7%; Opened below the stop-loss 7%; Stopped out within 3 days (timing / normal noise) 1%

## 5. Repeat stocks (sent 3+ times)
- None.

## 6. Skipped ideas (opened outside the buy zone): missed winners or avoided losses?
- RAIN (strategy tip (retired list)): -14.5% since that open
- BHARTIHEXA (hourly scan): +0.1% since that open
- TCS (hourly scan): -0.1% since that open
- In total: 1 of 3 would be up, average -4.8%
