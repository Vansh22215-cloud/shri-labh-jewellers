# Round 5: new short-term setups for more trades a week (written 18 Nov 2026, BEFORE running)

**Owner, 18 Nov:** the push is now 24 hours. Each family is tested on its own.

**Shared test conditions:**
- Same point-in-time top-300 universe, delisted stocks included.
- Only stocks trading ≥ ₹2 cr/day over 20 days.
- Signal at the close, bought at the next open.
- 0.35% costs.
- If the opening price is already through the stop, the trade exits at the open.
- One open trade per stock at a time.

| ID | Setup | Entry rule (all known at the signal close) | Exit |
|---|---|---|---|
| P1 | Pocket pivot | up day (close > open and > prior close); volume > highest down-day volume of the prior 10 days; close > 50-day average, and the 50-day average is above its value 10 days ago; close within 15% of the 52-week high | stop = entry − 2×ATR14 (signal day); exit at the next open after a close below the 10-day average; at most 30 days |
| P2 | NR7 breakout in an uptrend | day t has the narrowest high−low of the last 7 days; close > 50-day > 200-day average. Buy only if the next day trades above day t's high, filled at max(open, high_t + 0.05%) | stop = low of day t; exit as P1 |
| P3 | 3-day pullback in leaders (Connors style) | close > 200-day average; 3 lower closes in a row; 6-month return in the top 30% of the universe that day | stop = entry − 3×ATR14; exit at the next open after a close above the 5-day average; at most 10 days |

**PASS, per family:** a family passes only if all four hold.
1. **Holdout (signals from 1 Nov 2023):** profit per trade ≥ +1.0% after costs.
2. **Profit factor:** ≥ 1.3 in BOTH development and holdout.
3. **Trade count:** ≥ 2 trades a week on average in the holdout.
4. **Development:** profit per trade > 0.

**If a family passes:** it may be added as a separate tip type behind its own settings switch, using the same risk per trade as other tips (no increase in risk).
