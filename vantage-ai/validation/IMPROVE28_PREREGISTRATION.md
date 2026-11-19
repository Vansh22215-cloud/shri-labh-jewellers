# Round 28 (pre-registered 19 Nov 2026): which tips to take first when money is short

Money, not ideas, is the limit (fingerprint: ~7 matching stocks a day; the account is 90-98% invested). Today the
order among same-day tips is random. Five orders from published research (not from our data):
- P1 momentum: highest 6-month return first (Jegadeesh-Titman)
- P2 52-week-high: closest to the 52-week high first (George-Hwang)
- P3 low volatility: smallest daily swing (ATR %) first (low-volatility anomaly)
- P4 VANTAGE score: highest signal score first
- P5 fingerprint: average of the day's percentile ranks of P1 and P2
Live setup: top-300, buy at the 3:20 pm close (C1) + ADD MORE (adds inherit their signal's rank). ₹51,000, 1% risk,
25% cap, 0.35% costs, 15 random orders for ties. Fixed and monthly-updated capital.
Honest note: the auto-lab already saw development results of P1-P4 on the next-open set (B), and the holdout of
P1 on B (top-300 18.6% vs 16.2%). This round is on the live setup C+A, judged by:
PASS = +1 point a year and a worst fall no more than 2 points deeper in BOTH periods (fixed capital), AND better in
at least 60% of years. One passing order at most is proposed (the best in the holdout); nothing changes without yes.
