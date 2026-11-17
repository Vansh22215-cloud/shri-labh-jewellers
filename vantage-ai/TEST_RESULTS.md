# VANTAGE AI — Test results

## Version 2 (current): Breakout + Dip-buy + Rolling Candle Profile (17 Nov 2026)
Same method as below: point-in-time top-300 NSE stocks, 2013–2026, delisted stocks included, next-open fills, 0.35% costs. The rules for the new types were written before the run (`validation/backtest.py`, addendum).

| Measure | v1 (Breakout only) | **v2 (all types)** |
|---|---|---|
| Trades | 3,225 | 7,264 |
| Trades that won | 37% | **46%** |
| Average win / loss | +28% / −11% | +19% / −9% |
| **Average per trade (after costs)** | +3.87% | **+3.84%** (+3.59% at 0.60% costs) |
| Profit factor | 1.58 | **1.77** |
| **Last 3 years (held out)** | +0.51% | **+2.92%** |
| Years beating the average stock | 9 of 14 | **14 of 14** |
| Losing years (average trade) | 6 | **3** (2015, 2018, 2022) |
| Average holding | 52 days | 42 days |

**By signal type.** "Likely win" is the share of past signals of that type that ended in profit after costs; it is the number shown on the chart.

| Type | Trades | Won | Avg/trade | Last 3 years | Verdict |
|---|---|---|---|---|---|
| Dip-buy A (fear spike + support zone) | 171 | **80%** | +3.34% | 84% won | |
| Dip-buy B (fear spike) | 254 | **75%** | +2.26% | 75% won | |
| Dip-buy C (support zone only) | 25 | 80% | +1.48% | 5 trades | |
| **Dip-buy total** | 450 | **77%** | +2.62% | 78% won, +3.39% | Passes every check except the holdout sample size (90 trades vs 100 required). ON because the owner asked for it |
| **Rolling Candle Profile** | 5,510 | 46% | **+4.00%** | +3.30% | ✅ PASS (beat the average stock in 93% of years) |
| Breakout | 1,304 | 36% | +3.57% | +1.08% | ✅ PASS |

- **The setup score does not predict breakout success:** score 70–79 won 36%, 80–89 37%, 90+ 36%. The likely % is therefore not raised for higher scores.
- **By market:** NIFTY BULLISH / SIDEWAYS / BEARISH at entry: +3.66% / +4.23% / +5.68% per trade (the BEARISH entries are mostly dip-buys and RCP).
- **By size and volatility:** large-caps +2.83%, mid-caps +4.36%; low / medium / high volatility +3.47% / +3.64% / +4.83%.
- **By year** (average per trade): 2013 +2.2 · 2014 +9.4 · 2015 −2.3 · 2016 +3.7 · 2017 +5.1 · 2018 −4.3 · 2019 +1.2 · 2020 +10.2 · 2021 +4.9 · 2022 −1.6 · 2023 +10.3 · 2024 +1.5 · 2025 +0.4 · 2026 +0.9

**A ₹50,000 account** (1% risk per trade, not compounded, costs included; for reference only):

| Account | Per year | Worst drawdown | Last 3 years |
|---|---|---|---|
| Max 4 positions | ≈ +₹3,060 (6.1%) | −₹3,469 | +₹4,770 |
| Max 8 positions | ≈ +₹5,270 (**10.5%**, about the same as NIFTY) | −₹6,606 (much smaller than NIFTY's falls) | +₹4,970 |

The longest losing streak was 11. On a single stock that rose 5×, buy-and-hold still wins.

---

## Version 1 (history)

## How it was tested
- **What was tested:** `validation/replica.py`, a line-by-line Python copy of the Pine core (`src/core.pine`), run on real NSE data.
- **Universe:** the point-in-time top-300 NSE stocks by turnover, monthly, Jan 2013 to Nov 2026.
  - Includes **228 delisted or renamed stocks** rebuilt from NSE's own daily files, so there is no survivorship bias.
  - ETFs excluded.
  - A stock can get a new BUY only while it is in that month's top 300.
- **Fills:** the BUY is decided at the close and **filled at the next day's open**. A stop fills at the stop, or at the open if the price gaps below it.
- **Costs:** 0.35% per round trip (STT, exchange charges, stamp, GST, slippage), with a stress test at 0.60%.
- **Pre-registration:** the defaults and the pass bar were **written and committed before the first run** (`validation/backtest.py`, commit "pre-registered validation rules"). The only changes after seeing results were the ones those rules prescribed.
- **Re-run:**
  ```
  python3 validation/backtest.py            # all exit modes
  python3 validation/backtest.py --final    # published defaults
  ```

**The pass bar** (all after costs):
1. Expectancy above 0, with the 95% confidence interval also above 0.
2. The untouched holdout (Nov 2023 onwards) above 0 on at least 100 trades.
3. Beats the average stock in at least 55% of years.
4. Profit factor at least 1.3.
5. Still positive at 0.60% costs.

## Step 1: all exit modes (breakout and pullback entries on)
| Exit mode | Trades | Win% | Avg/trade | Holdout | Years beating avg stock | Verdict |
|---|---|---|---|---|---|---|
| Combined (planned default) | 4,680 | 29.4 | +0.54% | **−0.20%** | 21% | ❌ |
| ATR trailing stop | 3,893 | 35.9 | +1.64% | −0.04% | 43% | ❌ |
| **Fixed risk/reward** | 3,497 | 36.9 | **+3.66%** | +0.78% | 57% | ✅ |

**Why Combined failed:**
- Its "failed breakout" exit fired on 2,344 of 4,680 trades, averaging −2.05%. It cuts breakouts that wobble before they run.
- Trades exited on a bearish CHoCH averaged +8.0%, and trailing-stop exits +4.6%.
- This was **not re-tuned after seeing it**. Doing so would be curve fitting. A future version must test any change on new data.

**Entry types under Fixed risk/reward:**
| Entry type | Trades | Win% | Avg/trade | Holdout | Years beating avg stock | Verdict |
|---|---|---|---|---|---|---|
| Breakout | 3,100 | 37.5 | +3.93% | +0.90% | 64% | ✅ |
| Pullback | 397 | 32.7 | +1.52% (CI includes 0) | −0.10% | 14% | ❌ → **OFF by default** |

## Step 2: published defaults (Breakout only, Fixed risk/reward, everything else as designed)
| Measure | Result |
|---|---|
| Trades | 3,225 (≈ 232 a year across 300 stocks; 368 from delisted stocks) |
| Win rate | **37.3%** |
| Average win / loss | +28.3% / −10.7% |
| **Expectancy per trade** | **+3.87%** (95% CI +3.20 to +4.55); before costs +4.22%; at 0.60% costs +3.62% |
| Profit factor | 1.58 |
| Average holding | 52 trading days |
| vs the average stock (same days, before costs) | +0.62% per trade; beat it in **64% of years** (9 of 14) |
| vs NIFTY 50 (same days) | +2.11% per trade |
| Development 2013 – Oct 2023 | 2,551 trades, 39.6% win, +4.76% |
| **Holdout Nov 2023 – Nov 2026** | 674 trades, **28.9% win, +0.51%, profit factor 1.07: weak** |
| Market regime at entry: NIFTY BULLISH / SIDEWAYS | +3.67% (2,992) / +6.47% (233). No entries in a BEARISH market (filter) |
| Volatility at entry (NIFTY 20-day): low / medium / high | +2.27% / +4.63% / +6.71% |
| Large-cap (top 100) / mid-cap (101–300) | +2.00% (1,049) / +4.78% (2,176) |
| Losing years (average trade) | 6 of 14: 2015, 2018, 2019, 2022, 2024, 2026 |

**By year** (trades, win%, average per trade): 2013 111/43%/+6.3 · 2014 350/54%/+11.4 · 2015 163/23%/−1.9 · 2016 213/35%/+2.5 · 2017 377/38%/+3.6 · 2018 143/18%/−3.8 · 2019 133/25%/−1.1 · 2020 226/50%/+9.6 · 2021 354/41%/+5.7 · 2022 188/24%/−1.1 · 2023 378/55%/+9.8 · 2024 346/24%/−1.9 · 2025 176/30%/+1.2 · 2026 67/12%/−4.5

## Step 3: what a ₹50,000 account would have done
These use the indicator's own sizing (1% risk, at most 25% of capital per stock), are not compounded, and include costs. Ties were taken alphabetically, not by any ranking.

| Account | Per year | Worst drawdown | Longest losing streak | Holdout (Nov 2023+) |
|---|---|---|---|---|
| Max 4 open positions | **≈ +₹1,490 (≈ 3.0%)** | −₹11,683 | 14 | −₹4,475 |
| Max 8 open positions | **≈ +₹4,100 (≈ 8.2%)** | −₹14,738 | 15 | +₹8,543 |
| Buy and hold NIFTY 50 (2013–2026) | **≈ 10.5% a year** | (deeper in 2020) | — | — |

**Single stocks.** The rule: the 5 largest and the stocks ranked 151–155 in Jan 2014 (no hand-picking). Indicator profit vs ₹50,000 bought and held:

| Stock | Trades | Indicator | Buy & hold |
|---|---|---|---|
| SBIN | 8 | +₹1,366 | +₹2,67,304 |
| ICICIBANK | 9 | +₹3,287 | +₹3,98,281 |
| INFY | 10 | +₹1,494 | +₹1,38,435 |
| AXISBANK | 12 | −₹418 | +₹1,97,344 |
| MCDOWELL-N | 10 | −₹1,378 | +₹71,554 |
| INDIACEM | 7 | +₹347 | +₹2,22,987 |
| GSKCONS | 1 | +₹928 | +₹70,331 |
| CHAMBLFERT | 17 | −₹864 | +₹5,94,507 |
| SYNDIBANK (merged) | 2 | +₹914 | **−₹42,018** |
| DISHMAN | 3 | −₹1,643 | +₹2,44,928 |

The indicator uses only a small part of the capital (1% risk per trade) and is in a stock only a fraction of the time. So on one stock that rose 5×, **buy-and-hold wins by a mile**. It helped on the stock that collapsed (SYNDIBANK).

## Honest conclusion
1. **Real edge, per trade.** BUY signals have a statistically clear positive expectancy after costs over 13 years: +3.9% per trade, and they beat the average stock in 9 of 14 years. That is the evidence that the logic is not random.
2. **Not a "beat the market" machine.** As a ₹50k account with 1% risk per trade, it **earned less than holding NIFTY 50**, and **2024–2026 were weak** (holdout profit factor 1.07). Its strengths:
   - stock **selection and timing with a defined maximum loss on each trade**
   - staying out of bearish markets
3. **It works best in volatile and sideways markets and on mid-caps.** It is weakest in calm bull markets on large-caps, where simply holding is hard to beat.
4. **Low win rate by design: 37%.** Most of the gain comes from a third of the trades. Following it means accepting long losing streaks; 14 in a row happened.
5. **Past results do not guarantee future results.**
