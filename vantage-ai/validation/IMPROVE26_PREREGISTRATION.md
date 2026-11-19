# Round 26 (written 19 Nov 2026): which stocks should VANTAGE scan? Top-300 vs all stocks >= ₹2 cr/day

Honest status: NOT a clean pre-registration. The holdout numbers of both universes were already seen in earlier rounds
(round 23: all stocks >= ₹2 cr 10.5% a year / -26.8% fall; top-300 14.8% / -20.6%). Development favoured all stocks,
but round 23 found development is inflated for small stocks (delisted small caps missing = survivorship bias).
So this round is judged by year-by-year consistency, by the fact that the reason is known in advance (survivorship),
and then by the live record.

Universes (same VANTAGE signal rules, ₹51,000, 1% risk, 25% cap, 0.35% costs, 15 random orders):
- U-all: all stocks >= ₹2 cr/day (what the live system scans now)
- U-300: point-in-time top 300 (trades_FINAL)
- U-mix: all stocks >= ₹2 cr/day, but when money is short the top-300 signals are taken first
Reported per year 2012-2026, per period, with fixed and with current-value sizing.
Decision rule written now: propose a change to the owner only if the winner is better in at least 60% of the years
since 2018 (where delisted data is most complete) AND in the holdout on both growth and worst fall.
