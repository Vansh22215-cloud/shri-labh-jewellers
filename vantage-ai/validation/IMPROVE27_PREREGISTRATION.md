# Round 27 (pre-registered 19 Nov 2026): is "top 300" a lucky number? (prosecutor test of D144)

Same VANTAGE rules, point-in-time universe of the top N by money traded (data/universe_history.csv, monthly), N = 100,
200, 300, 400, 500. ₹51,000, 1% risk, 25% cap, 0.35% costs, 15 random orders. Development / holdout / every year.
Verdict written now:
- ROBUST if top-200 and top-400 are both within 2 points a year of top-300 in the holdout AND both beat all stocks
  >= ₹2 cr (7.2%) in the holdout.
- FRAGILE otherwise (then D144 is reported back to the owner).
- If another N is better than 300 by 2+ points in BOTH periods, it is proposed to the owner (no change without yes).
