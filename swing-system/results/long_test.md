# Long test of the practice rules (21 Nov 2026 19:46 IST)

**Data: Kite 5-minute candles only - 2,772 stocks, 2,910 trading days, 2015-02-02 to 2026-11-20. Settings chosen on days before Jan 2024; 'recent' = Jan 2024 onwards, not used for the choice.**

| Rule | Setting | Period | Avg / day | Days in profit | Days ₹10k+ | Worst day | Worst fall |
|---|---|---|---|---|---|---|---|
| Stocks | now live: vol 1.5, last 11:30, sides both, stop 0.01, target 0.02 | before 2024 | ₹-644 | 33.5% | 0.0% | ₹-3,271 | ₹-1,412,351 |
| Stocks | now live: vol 1.5, last 11:30, sides both, stop 0.01, target 0.02 | recent | ₹-560 | 37.4% | 0.0% | ₹-3,259 | ₹-412,106 |
| Stocks | best: stop 0.01, target 0.03, vol 1.5, last 11:30, sides both + beyond yesterday's high/low; NIFTY moving the same way; stronger than NIFTY today; India VIX below 20; no resistance within 1% | before 2024 | ₹-473 | 36.4% | 0.0% | ₹-3,394 | ₹-826,833 |
| Stocks | best: stop 0.01, target 0.03, vol 1.5, last 11:30, sides both + beyond yesterday's high/low; NIFTY moving the same way; stronger than NIFTY today; India VIX below 20; no resistance within 1% | recent | ₹-465 | 38.2% | 0.0% | ₹-3,284 | ₹-327,286 |
| NIFTY options (estimate) | now live: stop 0.3, target 0.6, last 14:30 | before 2024 | ₹+136 | 46.2% | 2.8% | ₹-7,675 | ₹-168,954 |
| NIFTY options (estimate) | now live: stop 0.3, target 0.6, last 14:30 | recent | ₹+29 | 44.0% | 0.7% | ₹-6,211 | ₹-86,671 |
| NIFTY options (estimate) | best: stop 0.3, target 1.0, last 14:30 + India VIX below 20 | before 2024 | ₹+255 | 39.9% | 1.9% | ₹-6,219 | ₹-95,050 |
| NIFTY options (estimate) | best: stop 0.3, target 1.0, last 14:30 + India VIX below 20 | recent | ₹+135 | 39.2% | 1.0% | ₹-6,211 | ₹-53,284 |

**Switched on for the practice trader:** NIFTY options

**Size (goal ₹10,000 a day):** risk per trade x1.0 stocks (₹1,500), x2.08 NIFTY options (₹6,240); expected average ≈ ₹281 a day from the recent years (goal ₹10,000); day loss limit ₹12,500

- nifty: averaging ₹10,000 a day would need 74.1x today's risk per trade; ₹50,800 allows at most ~4.8x (and losses grow by the same factor).

## Extra factors on the live stock setting (stop 1%, target 2%)

| Factors | Before 2024 avg/day | Recent avg/day | Recent worst fall |
|---|---|---|---|
| beyond yesterday's high/low | ₹-644 | ₹-659 | ₹-481,220 |
| NIFTY moving the same way | ₹-562 | ₹-507 | ₹-373,575 |
| stronger than NIFTY today | ₹-653 | ₹-551 | ₹-405,843 |
| India VIX below 20 | ₹-633 | ₹-563 | ₹-390,279 |
| no resistance within 1% | ₹-634 | ₹-584 | ₹-424,694 |
| beyond yesterday's high/low; NIFTY moving the same way | ₹-528 | ₹-488 | ₹-354,222 |
| NIFTY moving the same way; stronger than NIFTY today | ₹-576 | ₹-476 | ₹-354,146 |
| beyond yesterday's high/low; stronger than NIFTY today | ₹-646 | ₹-649 | ₹-474,234 |
| NIFTY moving the same way; India VIX below 20 | ₹-531 | ₹-495 | ₹-344,093 |
| beyond yesterday's high/low; NIFTY moving the same way; stronger than NIFTY today | ₹-539 | ₹-481 | ₹-352,067 |
| NIFTY moving the same way; stronger than NIFTY today; no resistance within 1% | ₹-886 | ₹-472 | ₹-353,635 |
| beyond yesterday's high/low; NIFTY moving the same way; stronger than NIFTY today; India VIX below 20 | ₹-504 | ₹-500 | ₹-344,490 |
| beyond yesterday's high/low; NIFTY moving the same way; stronger than NIFTY today; India VIX below 20; no resistance within 1% | ₹-496 | ₹-500 | ₹-346,299 |

## Scaling out - stocks (book part at 1R, stop to entry, rest to 2R/3R)

| Stop | Booked at 1R | Rest to | Before 2024 avg/day | Recent avg/day | Recent worst fall |
|---|---|---|---|---|---|
| 0.01 | (now: all at 0.02) | - | ₹-644 | ₹-560 | ₹-412,106 |
| 0.0075 | 50% | 2R | ₹-691 | ₹-657 | ₹-474,957 |
| 0.0075 | 50% | 3R | ₹-682 | ₹-618 | ₹-450,622 |
| 0.0075 | 67% | 2R | ₹-693 | ₹-661 | ₹-476,996 |
| 0.0075 | 67% | 3R | ₹-683 | ₹-632 | ₹-459,687 |
| 0.01 | 50% | 2R | ₹-681 | ₹-603 | ₹-439,552 |
| 0.01 | 50% | 3R | ₹-668 | ₹-594 | ₹-432,893 |
| 0.01 | 67% | 2R | ₹-683 | ₹-619 | ₹-450,481 |
| 0.01 | 67% | 3R | ₹-669 | ₹-616 | ₹-447,319 |
| 0.015 | 50% | 2R | ₹-744 | ₹-541 | ₹-392,040 |
| 0.015 | 50% | 3R | ₹-721 | ₹-511 | ₹-377,472 |
| 0.015 | 67% | 2R | ₹-740 | ₹-555 | ₹-401,200 |
| 0.015 | 67% | 3R | ₹-721 | ₹-528 | ₹-382,910 |

## Scaling out - NIFTY options (estimate)

| Stop | Booked at 1R | Rest to | Before 2024 avg/day | Recent avg/day | Recent worst fall |
|---|---|---|---|---|---|
| 0.3 | (now: all at 0.6) | - | ₹+136 | ₹+29 | ₹-86,671 |
| 0.2 | 50% | 2R | ₹-261 | ₹-262 | ₹-268,718 |
| 0.2 | 50% | 3R | ₹-208 | ₹-215 | ₹-246,394 |
| 0.2 | 67% | 2R | ₹-278 | ₹-262 | ₹-268,718 |
| 0.2 | 67% | 3R | ₹-224 | ₹-215 | ₹-246,394 |
| 0.3 | 50% | 2R | ₹+34 | ₹-4 | ₹-83,228 |
| 0.3 | 50% | 3R | ₹+75 | ₹-57 | ₹-109,234 |
| 0.3 | 67% | 2R | ₹+9 | ₹-4 | ₹-83,228 |
| 0.3 | 67% | 3R | ₹+32 | ₹-57 | ₹-109,234 |
| 0.4 | 50% | 2R | ₹+51 | ₹-72 | ₹-118,083 |
| 0.4 | 50% | 3R | ₹+67 | ₹-105 | ₹-105,208 |
| 0.4 | 67% | 2R | ₹+46 | ₹-72 | ₹-118,083 |
| 0.4 | 67% | 3R | ₹+55 | ₹-105 | ₹-105,208 |
