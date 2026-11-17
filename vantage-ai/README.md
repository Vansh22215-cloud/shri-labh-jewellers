# VANTAGE AI — NSE positional decision engine for TradingView (Pine Script v6)

A long-only, daily-timeframe indicator for NSE stocks. It gives **BUY / HOLD / SELL / WAIT**, a transparent 0–100 setup score, stop-loss, targets and position size. It comes with a backtesting strategy that uses identical logic.

| File | What it is |
|---|---|
| `VANTAGE_AI_Indicator.pine` | **The indicator.** Paste into TradingView's Pine Editor |
| `VANTAGE_AI_Strategy.pine` | The companion backtest strategy (same core, plus orders) |
| `USER_GUIDE.md` | Beginner's guide: install, read the chart, sizing, alerts, defaults, daily routine |
| `TEST_RESULTS.md` | 13-year NSE validation, including the weaknesses |
| `AUDIT_REPORT.md` | What was verified, what was fixed, what still needs TradingView |
| `src/core.pine` | The single source of all signal logic (both scripts are built from it: `python3 build.py`) |
| `validation/` | Python replica of the core + backtest scripts + every simulated trade |

> ⚠️ **Not yet compiled in TradingView.** It was written and reviewed for Pine v6 rules, but there is no Pine compiler outside TradingView. See the testing checklist below.

## Phase 1: Architecture
```
Daily candle closes
  ├─ Trend module        EMA20/50/200 alignment, EMA50/200 slope, previous completed weekly candle vs weekly EMA20
  ├─ Momentum module     RSI zone (healthy 50-70, extended >78 scores less), MACD histogram level + acceleration,
  │                      ADX ≥ 20 with DI+ > DI-
  ├─ Structure module    confirmed swing highs/lows (pivots used only after confirmation), BOS / CHoCH, higher
  │                      lows, failed breakouts, rejection wicks, OHLC-derived demand zone
  ├─ Relative strength   stock ÷ NIFTY 50: 3-month performance, RS above its 50-SMA, RS 10-EMA rising
  ├─ Volume module       up-volume ÷ down-volume (20 days), relative volume on up days, volume fading in a rise
  └─ Market regime       NIFTY 50 vs its EMA50/EMA200 → BULLISH / SIDEWAYS / BEARISH
        │
        ▼
  Score 0-100 (each module capped at its weight) ─┐
  Setup detector: Breakout | Pullback             ├─► BUY only if ALL pass ─► fill next open
  Mandatory filters: trend, not extended, stop ≤ ─┘        │
  15%, room ≥ 1.5R, market not bearish, no rejection,      ▼
  not in a trade, gap since last exit              Position state machine → stop / targets / exits → SELL
                                                           │
                                         Dashboard · labels · alerts · position sizing
```
Each module has one job and a capped contribution, so no module can dominate.
- **High volume alone never creates a BUY:** volume is at most 10 points, and a setup is mandatory.
- **The score alone never creates a BUY:** the setup and every filter are mandatory.

## Phase 2: Exact conditions and score
All formulas are in `src/core.pine`, sections 2–9, written to be readable.

**Score.**
- `score = round(Σ weightᵢ × pointsᵢ / maxᵢ)`, with the weights normalised to 100.
- Trend 25 · Momentum 20 · Structure 20 · RS 15 · Volume 10 · Market 10.
- When data is missing (no benchmark, too little weekly history), the module scores half rather than 0 or full.

**Breakout setup** (all of these):
- Close above the highest high of the previous 50 bars, after closing at or below it the day before.
- Close > EMA50 > EMA200.
- Volume ≥ 1.5 × the 20-day average.
- MACD histogram > 0 or RSI > 55.
- RS 3-month performance > 0, or RS above its 50-SMA.

**Pullback setup** (default OFF):
- EMA20 > EMA50 > EMA200, with EMA50 rising.
- The 5-day low touched EMA20 (or the demand zone).
- Every close in the last 5 days ≥ 0.98 × EMA50.
- The 5-day RSI low was between 38 and 55.
- 3-day volume below average.
- Today closes above yesterday's high, is a green candle, and is above EMA20.
- RS above its 50-SMA.

**Filters:**
- (close − EMA20) ≤ 3 ATR, and RSI ≤ 80.
- Stop = close − 3 ATR, no more than 15% away.
- Room to the nearest overhead resistance (52-week high or confirmed swing high) ≥ 1.5R.
- NIFTY not BEARISH.
- No rejection wick.
- Score ≥ 70.
- Quantity ≥ 1.
- ≥ 5 bars since the last exit.

**Exits** (Fixed risk/reward, default):
- Stop fills at min(open, stop).
- Target 2 = signal close + 3R, fills at max(open, T2).
- If both fall inside one candle, the stop is assumed first.

## Phase 7: Install and testing checklist
- **Install:** see `USER_GUIDE.md` §1.
- **Checklist:**
  1. [ ] Indicator compiles in the Pine Editor (v6). If not, note the error line.
  2. [ ] Strategy compiles. Strategy Tester → Properties shows ₹50,000, commission 0.12%, slippage 2.
  3. [ ] On `NSE:RELIANCE` 1D: BUY / SELL arrows appear only on closed candles. Reload the chart: the arrows are on the same candles.
  4. [ ] Compare the strategy's trade list on RELIANCE and TCS with `validation/trades_FINAL.csv` (columns `sym`, `signal`, `entry_date`, `exit_date`). Most should match. Data differences explain a few.
  5. [ ] The "Core trades vs Strategy trades" box (bottom right of the strategy) shows equal or nearly equal counts.
  6. [ ] Switch to Heikin-Ashi: the dashboard shows the chart-type warning. Switch the benchmark to an invalid symbol: "Benchmark: no data", with no crash.
  7. [ ] Create a "Once per bar close" alert using "Any alert() function call". It arrives after the close on the next signal.
  8. [ ] Try a stock with a high price (MRF, PAGEIND): "size < 1 share" and no BUY when ₹50k can't buy one share within 25%.
