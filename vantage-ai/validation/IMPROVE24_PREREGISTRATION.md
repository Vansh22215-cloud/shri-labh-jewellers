# Round 24 (pre-registered 19 Nov 2026): crash scenario for the stress lab (ATLAS)

Question: what happens to the ₹51,000 account if the whole market opens sharply lower one morning, on the worst
possible day (the day the most VANTAGE trades are open)?

Method (written before running):
- Setups B (trades_FINAL.csv) and C+A (3:20 pm buy + ADD MORE, the live setup), as in round 21; 15 random orders, median.
- Crash day = the trading day with the most overlapping trades in each period (development, holdout).
- On that day every open trade is sold at the open = previous close x (1 - stock gap). Stock gap = 1.5 x market gap
  (small and mid caps fall more). Market gaps: 5%, 10%, 20% (2020 worst day was about -13%).
- Every trade still exits there, even if its stop-loss was lower (worst case: the owner sells everything in panic).

Reported: yearly growth and worst fall vs no crash. This is a risk measurement, not a rule test. Nothing changes live.
"Survives" = yearly growth still positive and worst fall no deeper than 40%, in both periods, for the 10% gap.
