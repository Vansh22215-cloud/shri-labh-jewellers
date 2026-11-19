# AUTO-LAB protocol (pre-registered 19 Nov 2026, before any run)

Owner, 19 Nov: "learn from everything, every move, every result ... find the entire list of possibilities, run the
test of all those ... situation, time, stock, history ... if at last it gives us better results come to me for approval."

## What is tested
Every VANTAGE trade of the 13-year test, in both trade sets (top-300 `trades_FINAL.csv`, all stocks
`improve_trades_U2.csv`), described at the signal close with data known then (`lab_features.py` -> `lab_features.csv.gz`):
- **Stock:** liquidity, distance from the 52-week high, 6-month, 1-month and 1-week return, volume surge, daily swing
  (ATR %), 10-day range, distance from the 200-day average, the signal-day move, price level, up-days in 10, sector.
- **Stock history:** the number of its earlier VANTAGE trades and their win rate (only trades closed before the signal).
- **Market:** NIFTY 1-month return, NIFTY vs its 200-day average, NIFTY swing, trend / mood / breadth day type.
- **Time:** weekday, month, day of the month, results within 14 days.
- **Signal:** setup type, signal score, stop distance.

## The possibilities (generated automatically, all of them)
- For each number: buckets = fifths of the development trades (Q1 lowest ... Q5 highest). Rules:
  skip Q1, skip Q5, skip Q1+Q2, skip Q4+Q5, half quantity Q1, half quantity Q5,
  and "when money is short, take the highest first" / "lowest first" (an order among same-day signals).
- For each category with at least 3% of development trades: skip it, half quantity on it.
- No rule may raise risk: the 1% limit and 25% cap stay. Doubling is not a possibility.

## The bar (same as every round)
Account simulation, ₹51,000, 1% risk, 25% cap, 0.35% costs.
- **Step 1, development only (signals before 1 Nov 2023), 7 random orders:** yearly growth +1 point or more and the
  worst fall no more than 2 points deeper, in BOTH trade sets.
- **Luck count:** step 1 is repeated on data where each situation column is shuffled within each year. The number of
  rules that pass there is the number expected by luck. It is reported next to the real number.
- **Step 2, holdout (Nov 2023+), 15 random orders, only for step-1 survivors:** the same bar in both trade sets.
- **Step 3, year by year (top-300 set):** better than the current system in at least 60% of the years.
- **Step 4, placebo:** a skip rule must beat at least 90% of 20 random skips of the same number of trades
  (development, top-300).
- A rule that clears all four is a **candidate for the owner's approval**. Nothing changes live without his yes.
- The survivors of step 1 are written to `auto_lab_step1.json` and committed BEFORE step 2 looks at the holdout.

## Honest limits
- The holdout has been used for about 80 earlier tests; a pass here is weaker evidence than a first look.
- Live tips feed the same situation columns. Every live lesson is matched to its lab result in `AUTO_LAB_RESULTS.md`.
