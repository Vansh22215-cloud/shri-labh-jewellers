# Per-signal "likely win %" (written 18 Nov 2026, BEFORE running)
**Owner, 18 Nov:** almost every VANTAGE tip shows 46%, which is not specific to the company. Today the % is one number per signal type, and RCP covers ~75% of signals.

**Question:** can the facts known on the signal day give each signal its own honest win %?

## Data
`trades_FINAL.csv` (7,264 trades, point-in-time top-300, delisted stocks included). A trade is a win when its result after 0.35% costs is above 0.

## Features (all known at the signal day's close)
1. Signal type (RCP, Breakout, Dip-buy A/B/C)
2. Stop distance % (how far the stop-loss is)
3. The company's own past VANTAGE record: wins and trades among its signals that **closed before** this signal day, shrunk toward the type's average with weight 10 trades
4. Distance from the 52-week high
5. 20-day return
6. 6-month return rank in the universe that day
7. Volume on the signal day vs its 50-day average
8. Market regime (BULLISH / SIDEWAYS / BEARISH)
9. 20-day average traded value (log)
10. Breakout score

## Model
Logistic regression, standardised features. It is trained ONLY on signals before 1 Nov 2023 and applied unchanged to the holdout (Nov 2023+).

## PASS (holdout) requires all three
1. **Calibration:** in each of 5 equal-size groups of predicted %, the actual win % is within 6 points of the group's average predicted %.
2. **Spread:** the actual win % of the highest group exceeds the lowest group by ≥ 12 points.
3. **Better than today's table:** Brier score below that of today's type table (trained on dev only).

## Then
- **If it passes:** each tip shows its own %, retrained on all data with the same model. The message also says how many of that company's own past signals won.
- **If it fails:** keep the type table, and the message says plainly that the % is the average for that signal type, plus the company's own past record (count) as information.
