# VANTAGE AI — User guide (for beginners)

VANTAGE AI is a TradingView indicator for **NSE stocks on the daily chart**. It does the analysis for you and shows one decision: **BUY, HOLD, SELL or WAIT**.
- **Long-only.** BUY means buy shares. SELL means sell the shares you hold. It never means short-selling.
- It is a decision-support tool, not a guarantee. Read "What the numbers really mean" below.

---

## 1. Install (5 minutes)
1. Open **TradingView → Pine Editor** (bottom of the chart).
2. Delete everything, paste the whole of `VANTAGE_AI_Indicator.pine`, and click **Save** (name it "VANTAGE AI"), then **Add to chart**.
3. For backtesting (optional): open a **new** Pine Editor tab, paste `VANTAGE_AI_Strategy.pine`, save it, and add it to the chart. Results appear in the **Strategy Tester** tab.
4. Use a **standard candlestick chart** on the **1D (daily)** timeframe, for example `NSE:RELIANCE`.
   - Heikin-Ashi, Renko and similar charts give wrong prices. The dashboard shows a warning on them.

*Note: these scripts were written and checked outside TradingView. If the Pine Editor shows an error, it most likely needs a small syntax fix. Note the line number and the message.*

## 2. Reading the chart
| You see | Meaning | What you do |
|---|---|---|
| 🟢 green arrow + **BUY** label (signal type, **"Likely win: X%"**, how many past signals that is based on, this stock's own record) | All conditions met at today's close | Consider buying at **tomorrow's open**. Quantity and stop are on the dashboard |
| Blue / red / green lines | Entry, **stop-loss** (red, only moves up) and targets | Place your stop-loss order at the red line. Raise it when the line rises |
| 🔴 red arrow + **SELL** label (reason, result %) | Exit the position | Sell at the next open (or immediately if the stop was hit) |
| Nothing new | WAIT | Do nothing |
| Faint orange / teal steps | Last confirmed resistance / support | For context only |

**Signals never move.** A BUY or SELL appears only after the daily candle has closed, and it stays on that candle forever. During the trading day the dashboard can change, but no arrow is drawn until the close.

## 3. The dashboard (top right)
- **Market regime (NIFTY 50):**
  - BULLISH: above its 200-day average, and the 50-day average is above the 200-day.
  - BEARISH: the opposite.
  - SIDEWAYS: in between.
  - With the market filter on, no new BUY is given while the market is BEARISH.
- **Stock trend:** BULLISH if price > 50-day average > 200-day average.
- **Momentum:** RSI, MACD and ADX combined (STRONG = 12 or more of 20 points).
- **Relative strength:** OUTPERFORMING if the stock beat NIFTY over 3 months and its strength line is above its own average.
- **Volume:** CONFIRMED if buyers' volume dominated recently and today's move had volume.
- **Market structure:** BULLISH after the price breaks a confirmed swing high; BEARISH after it breaks a confirmed swing low.
- **Setup score (0–100):** the "why" rows show how many points each part gave.
- **Trade status:** BUY / HOLD / SELL / WAIT.
- **During a trade:** entry, initial stop, current stop, targets, quantity, money at risk and open profit/loss.
- **No trade:** what a trade would look like if bought now (shares, stop, maximum loss, reward).

## 4. The 3 kinds of BUY (each one was tested on 13 years of NSE data)
| Signal | What it is | Likely win* | Exit |
|---|---|---|---|
| **Dip-buy A / B / C** | A strong stock (≥ 10% above its 200-day average) has a sharp 2-day dip while NIFTY is in an uptrend. Confirmed by a fear spike (Vix Fix) and/or a support zone (order block, WaveTrend oversold, structure-break order block, swing-low hold). Never during a Squeeze | **A 80% · B 75% · C 80%** | First close above the 5-day average; 4 ATR stop; 10 days at most |
| **Rolling Candle Profile** | Zeiierman's profile shows buyers in control, price above a rising 21-EMA, within 10% of the 52-week high | **46%** (big winners) | Its own SELL signal; 5 ATR stop; 60 days at most |
| **Breakout** | Uptrend + close above the 50-day high on ≥ 1.5× volume + momentum + strength vs NIFTY + room to resistance + score ≥ 70 | **36%** (big winners) | Stop 3 ATR or Target 2 (3R) |
| Pullback | OFF by default: it failed the test | 33% | — |

\* **"Likely win" = how often similar past signals ended in profit** in the 13-year NSE test, after costs. It is a past frequency, **not a promise**. A 46% signal can still be more profitable than an 80% one, because its winners are bigger.

Every BUY also needs a closed candle, no open position, at least 5 bars since the last exit, and a valid stop. The 0–100 score is shown for information. It gates breakouts, but the tests show it does **not** change the odds.

## 5. What SELL means
Each signal type uses the exit that was tested with it. The SELL label shows the reason and the result.
- **Dip-buy:**
  - the first daily close above the 5-day average (usually 2–5 days), or
  - 10 days, or
  - the 4 ATR stop.
- **Rolling Candle Profile:**
  - the profile's own SELL signal, or
  - 60 days, or
  - the 5 ATR stop.
- **Breakout:** the 3 ATR stop, or Target 2 (3 × risk). Target 1 is only an alert.
  - Other breakout exit modes (ATR trailing, Combined) are in Settings → Exits. They failed the test.

## 6. Position size (your ₹50,000)
- **Formula:**
  ```
  Risk amount      = capital × risk %                 (₹50,000 × 1% = ₹500)
  Risk per share   = entry − stop
  Shares by risk   = floor(₹500 ÷ risk per share)
  Shares by money  = floor(₹50,000 × 25% ÷ entry)     (max ₹12,500 in one stock)
  Suggested shares = the smaller of the two
  ```
- **Example:** entry ₹500, ATR ₹10, so the stop is ₹470 (3 ATR) and the risk per share is ₹30.
  - By risk: ₹500 ÷ 30 = 16 shares.
  - By money: ₹12,500 ÷ 500 = 25 shares.
  - **Buy 16 shares (₹8,000).** If the stop is hit you lose about ₹480, plus costs.
- **Targets:** T1 = entry + 2R = ₹560, T2 = entry + 3R = ₹590 (R = ₹30).
- **Real loss can be bigger:** brokerage, STT and taxes are extra. If a stock **opens below your stop** (bad news, results), you are filled at that lower price.
- If the stop is 0 or the stock is too expensive for even 1 share within your limits, **no BUY is shown.**

## 7. What the numbers really mean
- **The score measures how many things line up. It is not a probability of profit.** A score of 90 does not mean a 90% chance.
- **Tested result** (TEST_RESULTS.md, all signal types together, 13 years):
  - **46% of trades won**, average +3.8% per trade after costs.
  - The last 3 years: +2.9% per trade.
  - It beat the average stock in **every one of the 14 years**.
- **Losing streaks still happen** (11 in a row in testing), and past results do not guarantee the future.

## 8. Alerts
1. Open the stock's chart with VANTAGE AI on it, then click ⏰ **Alert**.
2. **Condition:** "VANTAGE AI", then choose one of these:
   - `1 · VANTAGE BUY`
   - `2 · VANTAGE SELL`
   - `3 · Stop-loss warning`
   - `4 · Target 1 reached`
   - `5 · Target 2 reached`
   - `6 · Strong bullish setup`
   - `7 · Bearish deterioration`

   Or choose **"Any alert() function call"** for one alert that sends every event with full numbers: price, score, stop, targets, quantity and risk.
3. **Trigger: "Once per bar close"**. Then pick a notification method (app, e-mail, webhook) and click **Create**.
4. An alert works for **one symbol**. Make one per stock you follow, or use a watchlist alert if your TradingView plan offers it.
5. Each event fires **once**, at the daily close: no repeats.

## 9. Recommended default settings (NSE positional)
These are the defaults. They were fixed **before** testing and **not** tuned to past results.

| Setting | Default |
|---|---|
| Timeframe | 1D |
| Capital / risk / max per trade | ₹50,000 / 1% / 25% |
| Minimum score / strong | 70 / 80 |
| Breakout lookback / volume | 50 bars / 1.5× |
| Initial stop | 3 ATR |
| Targets | 2R (alert) / 3R (exit) |
| Breakout exit mode | Fixed risk/reward (the only one that passed the test). Dip-buy and RCP always use their own tested exits |
| Entry types | Dip-buy ON · Rolling Candle Profile ON · Breakout ON · Pullback OFF (failed the test) |
| Market filter | NIFTY 50, on |
| Minimum gap between trades | 5 bars |

## 10. Daily routine (5 minutes, after 3:30 pm)
1. Check the stocks you follow (or your alerts). A **BUY**? Note the quantity and stop.
2. Next morning:
   - Buy at the open.
   - Immediately place a **stop-loss order (GTT)** at the red line.
3. Keep the stop order in place until the stop or Target 2 is hit. You get a SELL arrow and alert.
   - If you switched to a trailing exit mode, move your stop up each evening when the red line rises.
