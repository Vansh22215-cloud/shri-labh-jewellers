# ATLAS Context Engine - protocol (pre-registered 19 Nov 2026, before any run)

Owner, 19 Nov: "Don't search for one rule that works everywhere. Discover which rule works, on which kind of stock,
under which market conditions, and continuously verify that it still works. Discover which similarities matter;
discover new groups itself."

## 1. Behaviour of every stock at every signal (only the 250 days BEFORE the signal)
Daily swing (ATR %), beta and correlation to NIFTY, trend persistence (share of up-weeks; lag-1 autocorrelation of
weekly returns), gap frequency (share of days opening 2%+ away from the previous close), worst fall in the past
year, distance from the 52-week high, 6-month return, money traded a day.

## 2. Groups ATLAS discovers itself
K-means on the standardized behaviour (k = 6 and 10), fitted on DEVELOPMENT trades only (signals before Nov 2023),
then every trade is assigned to its nearest group. Predefined groupings are compared with them:
sector, size fifth, swing fifth, setup, market type (trend x mood), and the pairs cluster x market,
sector x market, size x swing, cluster x setup.

## 3. Which similarities matter (walk-forward, no future data)
For every year Y from 2016: each group's average result per trade is estimated from trades CLOSED before Y,
shrunk to the overall average (weight n / (n + 50)), and used to predict the trades signalled in Y.
Score of a grouping = average over years of (actual result of the top-third predicted trades - bottom third).
The groupings are ranked by this score. A grouping "matters" if its score is above 0.5 points per trade and
positive in at least 60% of years.

## 4. Conditional rules (only from groupings that matter, best two), tested on the account
- C-ORDER: when money is short, take the trades whose context (group) has the best past record first.
- C-SKIP: skip trades whose context has a past average below 0 (shrunk), with at least 50 past trades behind it.
Both use only the past at every date (they re-learn every year: when a context stops working, its score falls).
Bar (as always): +1 point a year and the worst fall no more than 2 points deeper in BOTH periods (development and
holdout), in the top-300 set and the all-stocks set; better in at least 60% of years; and luck worlds: the same
rule with group labels shuffled within each year (3 worlds) must do clearly worse (the real rule beats all 3).
Passing rules go to the owner for a yes. Nothing changes live without it.
