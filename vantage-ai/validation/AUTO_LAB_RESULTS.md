# AUTO-LAB results, run 1 (19 Nov 2026)

Protocol: AUTO_LAB_PROTOCOL.md (committed before the run). Scripts: lab_features.py, auto_lab.py. Data: auto_lab_step1.json, auto_lab_results.json.

## In plain words
- Every past VANTAGE trade of 13 years (36,387 trades in two sets) was described by **40 facts** at the moment of the signal: the stock, its own past VANTAGE record, the market, the sector, results dates and the time.
- From those facts the lab built **230 possible rules** (skip, half quantity, or 'take these first when money is short') and tested every one in the ₹51,000 account.
- **Step 1 (older years only):** 2 of 230 passed. In 5 'luck worlds' (the facts shuffled so they mean nothing) 0, 0, 0, 0, 0 passed. So the 2 were probably not pure luck.
- **Step 2 (recent years, Nov 2023+):** both failed in the all-stocks set, which is the one the live system trades.
  - *Take the strongest last-week movers first when money is short:* worse in both sets (top-300 14.8% vs 15.6% a year; all stocks 7.6% vs 9.3%).
  - *Skip stocks priced above about ₹980:* helped the top-300 set (17.0% vs 15.6%, smaller fall) and beat 20 of 20 random skips, but hurt all stocks (6.8% vs 9.3%). A near miss, linked to the small ₹51,000 account (costly shares give odd quantities). Kept as a watch item, not a rule.
- **Result: no candidate for your approval in this run.** The current VANTAGE rules already beat every one of the 230 alternatives in the recent years.

## What this teaches (kept as lessons)
- 22 of 230 rules were a little better in both sets in the older years, but only 2 by the full +1 point. The edge is not hiding in one simple fact about the stock, market or time; it is already in VANTAGE's stock choice (fingerprint.json).
- Market-weather facts (trend, mood, breadth, NIFTY swing) again gave nothing, as in rounds 1, 6, 8 and 12.
- The live Learner's lessons (for example 'calm days better', 'Friday better', 'liquidity 10-50 cr') map to these columns: all were tested here on 13 years and none passed. Live lessons will now show this lab verdict.

## The 25 closest possibilities (older years, gain in the weaker set)

| Rule | Top-300 growth / fall | All stocks growth / fall |
|---|---|---|
| *current system* | 19.1% / -19.4% | 40.3% / -20.0% |
| prefer high stop_dist | 20.7% / -18.1% | 42.2% / -22.1% |
| prefer high ret_1w | 20.3% / -18.7% | 41.8% / -18.9% |
| skip turnover_cr 52.89.. | 20.4% / -20.8% | 41.5% / -22.3% |
| skip price_rs 979.8.. | 20.4% / -17.6% | 41.5% / -18.6% |
| prefer high ret_6m | 19.8% / -21.7% | 42.8% / -18.3% |
| prefer high vs_200d | 19.6% / -16.6% | 41.2% / -19.6% |
| half setup = Breakout | 19.6% / -16.0% | 40.9% / -18.4% |
| prefer high atr_pct | 20.2% / -16.6% | 40.8% / -21.1% |
| half price_rs 979.8.. | 19.8% / -16.7% | 40.8% / -18.2% |
| prefer low turnover_cr | 19.4% / -17.4% | 42.9% / -14.8% |
| half from_52w_high ..-0.08657 | 19.7% / -18.1% | 40.6% / -15.0% |
| skip from_52w_high ..-0.08657 | 19.7% / -17.6% | 40.5% / -13.6% |
| prefer high from_52w_high | 19.8% / -17.3% | 40.5% / -18.6% |
| half stock_past_win 0.6667.. | 19.2% / -16.7% | 40.5% / -18.3% |
| half sector = Information Technology | 19.7% / -15.6% | 40.4% / -21.3% |
| half vol_surge 3.471.. | 19.8% / -14.7% | 40.3% / -16.8% |
| skip results_soon = yes | 19.8% / -18.8% | 40.3% / -21.8% |
| prefer high signal_day_move | 19.1% / -17.4% | 41.4% / -19.0% |
| prefer low price_rs | 19.1% / -16.5% | 44.0% / -18.2% |
| prefer low score | 19.1% / -19.8% | 41.3% / -15.5% |
| prefer low nifty_vs_200d | 19.1% / -19.4% | 40.7% / -19.9% |
| half weekday = Thu | 19.1% / -16.3% | 40.5% / -18.1% |
| half stock_past_trades ..1 | 19.0% / -15.4% | 40.7% / -20.4% |
| prefer high nifty_vs_200d | 19.1% / -19.4% | 40.2% / -20.7% |
| prefer low day_of_month | 19.1% / -19.4% | 40.2% / -20.4% |

All 230 are in auto_lab_step1.json.

## Next runs
- New facts are added as columns (for example delivery %, promoter holding, option data once collected) and the whole lab is re-run with the same protocol. Exits were tested separately in 12 earlier rounds (all failed).
- Any rule that clears all 4 steps is sent to the owner for a yes/no. Nothing changes live without it.
