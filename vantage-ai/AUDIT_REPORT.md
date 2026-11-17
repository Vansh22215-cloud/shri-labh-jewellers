# VANTAGE AI — Audit report

## What was verified, and how
| # | Check | Method | Result |
|---|---|---|---|
| 1 | Indicator and strategy use **identical** logic | Both files are generated from one `src/core.pine`; `build.py` asserts the core text is byte-identical | ✅ identical |
| 2 | **No look-ahead** in the signal logic | Python replica run on 8 stocks, history cut at 18 dates each (144 cuts). Every trade closed before the cut must be identical with and without later data | ✅ 0 differences |
| 3 | Higher-timeframe data is **confirmed only** | The only `lookahead_on` is on `close[1]` / `ema[1]` / `ema[2]` of the **weekly** timeframe, i.e. the previous completed week | ✅ by code inspection |
| 4 | **No negative offsets**, no back-dated pivots | grep for `offset = -`: none. Swings are used only from their confirmation bar (`ta.pivothigh(L, L)` returns the value on the confirming bar) | ✅ |
| 5 | Signals only on **closed candles** | Every state change is inside `if barstate.isconfirmed and warm` | ✅ |
| 6 | **No duplicate BUY**: one position at a time, minimum gap after an exit | State machine (`inPos`, `pendingEntry`, `lastExitBar`) | ✅ by inspection + replica |
| 7 | **SELL only when a position is open** | `sellNow` is set only inside `if inPos` branches | ✅ |
| 8 | **Stop never moves down** | `stopLvl := math.max(stopLvl, …)`; it is only ever assigned that way after entry | ✅ |
| 9 | Position sizing | `floor(risk ₹ ÷ risk/share)`, capped by `floor(capital × max% ÷ price)`; zero/negative stop distance gives qty 0, so no BUY; stop more than 15% away gives no BUY | ✅ by inspection; worked example in USER_GUIDE §6 |
| 10 | Missing benchmark | `ignore_invalid_symbol = true` returns na, so the RS / market modules score neutral and the market filter does not block; the dashboard warns | ✅ by inspection |
| 11 | Non-standard chart (Heikin-Ashi, Renko…) | `chart.is_standard` is false, so the dashboard shows a warning | ✅ by inspection |
| 12 | Alerts fire once, at the bar close | Events are edge-triggered (true on one bar). `alertcondition` plus `alert(..., alert.freq_once_per_bar_close)` | ✅ by inspection |
| 13 | Performance claims are backed by tests | TEST_RESULTS.md: 13 years, pre-registered pass bar, survivorship-free universe | ✅; weaknesses reported |

## Issues found and fixed during development
- **Planned default exit failed the test.** "Combined" was the planned default. Its failed-breakout exit cut winners: holdout −0.20%.
  - The pre-registered rule switched the default to "Fixed risk/reward", which passed.
  - Combined is still available but documented as failing.
- **Pullback entries failed the test** (CI includes 0, holdout −0.1%), so they default to OFF by the pre-registered rule.
- **Room-to-resistance vs the "near 52-week high" breakout rule conflicted** in the design draft: a breakout just under the 52-week high could never pass a 1.5R room rule. Resolved before testing: a breakout is allowed either at a new 52-week high (no overhead resistance) or with ≥ 1.5R of room.
- **Strategy stop price:** the stop must be known when the entry order is placed. So stop and targets are based on the **signal close** (the plan), while the fill is the next open. The indicator, the strategy and the replica all use this same convention.

## NOT verified (needs you in TradingView)
| Item | Why it is not verified | How to verify |
|---|---|---|
| **The scripts compile** | No Pine compiler is available outside TradingView. The code follows Pine v6 syntax rules and was reviewed line by line, but a typo-level error is possible | Paste into the Pine Editor. Any error shows a line number; fix it or report it |
| TradingView numbers equal the replica's | Different data vendors (TradingView vs NSE files), EMA seeding on the first bars, tie handling in pivots | Run the strategy on 3–5 stocks; compare trade dates with `validation/trades_FINAL.csv` (most should match exactly) |
| Broker-emulator details | When a stop and a target are both inside one candle, the indicator assumes the **stop first** (conservative). TradingView's emulator guesses the intrabar path from the open and may pick the target | Check the "Core trades vs strategy trades" box on the strategy chart: the counts should match or differ by very few |
| Realtime behaviour | Signals are confirmed-bar only. The dashboard values move during the day; the arrows do not | Watch one live session; arrows appear only after 3:30 pm |
| Data-feed revisions | If TradingView later corrects a historical candle (splits, bad ticks), a signal on that candle can change. That is a data change, not repainting | Expected and rare |

## Differences between simulated and real execution
- **Fills:**
  - Simulation buys exactly at the next open. Real orders get the open auction price or worse, especially on gap-up breakout days.
  - Stops are simulated at the stop price. Real stop orders can fill lower in fast markets, and a gap below the stop fills at the open; this is modelled.
  - Circuit limits can make exits impossible for a day; this is not modelled.
- **Costs:** 0.35% per round trip is an estimate (delivery STT 0.1% each side + charges + slippage). DP charges per sell, and taxes on profits (STCG/LTCG), are **not** included.
- **Not compounded:** sizing uses the fixed capital input, not a growing balance.
- **Strategy Tester settings:** TradingView's `commission_value` (0.12% per side) and `slippage` (2 ticks) are approximations. Change them in Properties.

## Score honesty
- The 0–100 score counts how many independent conditions agree. Each module is capped at its own weight, so related indicators cannot inflate it. **It is not a probability.**
- The thresholds 70 / 80 are the brief's starting values. They were **not optimised**, and the tests used them unchanged.
