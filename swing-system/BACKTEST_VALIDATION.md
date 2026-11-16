# Backtest validation (independent re-test, 17 Nov 2026)

## Method
- **Script:** `validation/independent_validation.py`. It is one trade simulator, written separately from the original research. It uses the **production rules** and does no parameter search.
- **Re-run:**
  ```
  python3 validation/survivorship_data.py
  python3 validation/independent_validation.py
  NO_DELISTED=1 python3 validation/independent_validation.py
  ```
- **Outputs:** `validation/independent_validation*.json` and `validation/independent_trades_*.csv`, with every trade listed.

**Universe and survivorship**
- Point-in-time top-300 by turnover, rebuilt each month from data before that month, 2013 to Nov 2026.
- ETFs and funds are excluded, as in the live engine.
- 228 delisted or renamed stocks were rebuilt from NSE's own daily files (`survivorship_data.py`): 583k rows.
  - NSE's old files left many splits, bonuses and demergers unadjusted. These are corrected: standard split/bonus ratios, and any opening gap of more than 25% (impossible within the price bands without a corporate action).
  - Real one-day crashes are kept, such as DHFL in 2018 and Infibeam in 2018.

**Entries, exits and costs**
- Entry at the **next day's open** after the signal. If a day opens below the stop, the exit is at that open (gap loss).
- Costs: 0.35% per round trip, with a stress case of 0.60%.
- Development period: up to Oct 2023. Out-of-sample: Nov 2023 onwards.

**Benchmarks:** the equal-weight average of all universe stocks, and Nifty, held over each trade's exact days.

**"Production account":** the same signals, but a signal is taken only while the strategy has a free slot under the live limits (dip-buy 10, positional 4, AI 3, discovered 2 open tips). Ties are broken alphabetically, not by the live ranking, so treat it as an approximation. This is the realistic drawdown. The "every signal" drawdown adds up overlapping trades with no limit and is **not** achievable.

## Results (after 0.35% costs, survivorship-corrected universe)
| | Dip-buy (tiered) | Positional (RCP) | AI picks (top 5) | Discovered S1 (awaiting approval) |
|---|---|---|---|---|
| Trades | 1,351 | 6,983 | 5,167 | 4,801 |
| Win rate | **76.5%** | **45.3%** | 53.3% | 52.2% |
| Average win / loss | +4.34% / −3.93% | +19.3% / −9.1% | +6.25% / −5.58% | +10.5% / −8.5% |
| Expectancy per trade (95% CI) | **+2.39%** (2.11 to 2.67) | **+3.76%** (3.27 to 4.25) | +0.73% (0.50 to 0.95) | +1.41% (1.03 to 1.78) |
| Before costs / cost stress 0.60% | +2.74% / +2.14% | +4.11% / +3.51% | +1.08% / +0.48% | +1.76% / +1.16% |
| Profit factor | 3.59 | 1.76 | 1.28 | 1.35 |
| Average days held | 3.4 | 42.5 | 9.7 | 18.7 |
| Development (to Oct 2023) | 76.8%, +2.29% | 46.1%, +3.95% | 53.5%, +0.68% | 52.4%, +1.40% |
| **Out-of-sample** (Nov 2023 on) | **75.3%, +2.79%** (267) | **42.9%, +3.12%** (1,570) | 52.9%, +0.84% (1,445) | 51.4%, +1.44% (1,040) |
| Nifty above / below 200-day | 76.8% +2.42% / 52.6% +0.63% (19 trades) | +3.74% / +3.92% | +0.74% / +0.68% | +1.54% / +1.03% |
| Best / worst year (average trade) | 2020 +4.2% / 2016 −2.0% | 2023 +10.8% / 2018 −4.0% | 2017 +1.9% / 2022 −0.5% | 2014 +4.7% / 2018 −2.3% |
| Losing years | 1 of 14 | 3 of 14 | 2 of 11 | 2 of 14 |
| Excess over the average stock, same days (before costs) | +1.64% | +1.08% | +0.48% | +0.65% |
| Excess over Nifty, same days (before costs) | +2.14% | +2.36% | +0.58% | +0.96% |
| **Years beating the average stock after costs** | **12 of 14** | **14 of 14** | **6 of 11** | 9 of 14 |
| Longest losing streak (every signal) | 14 | 43 | 27 | 40 |
| Stop exits that gapped through | 0.4% | 1.2% | 0.9% | 1.9% |
| **Production account** (slots): trades, win%, expectancy | 919, 71.4%, +1.78% | 307, 43.6%, +3.31% | 815, 54.0%, +0.57% | 362, 48.9%, +0.76% |
| Production account: max drawdown at 1% risk / longest losing streak | **−7.2% / 8** | −12.0% / 10 | −9.0% / 8 | −12.6% / 8 (5 losing years) |

**Survivorship effect** (the same tests on the Yahoo-only universe, which lacks delisted stocks):
- Dip-buy: 76.3%, +2.40%
- Positional: 45.3%, +3.59%
- AI: unchanged. Its walk-forward predictions exist only for stocks with Yahoo data, so **survivorship is not tested for the AI picks**.
- Discovered S1: 52.7%, +1.50%

Adding the delisted stocks did **not** weaken the dip-buy or positional results. It slightly weakened S1: its 2-slot production account fell from +2.16% to +0.76% per trade.

## Claims vs. independent result
| Claim (DECISIONS.md) | Independent result | Verdict |
|---|---|---|
| Dip-buy with tiers: 1,040 trades, 76% in profit, +2.5% average (holdout 75%, +2.8%) | 1,351 trades, 76.5%, +2.39% (out-of-sample 75.3%, +2.79%) | ✅ **REPRODUCED.** More trades because of the larger universe (delisted stocks and the full period) |
| Positional: 6,340 trades, 45% in profit, +5.4% average, wins +21% / losses −9% (holdout 43%, +3.2%) | 6,983 trades, 45.3%, **+3.76%** after costs, wins +19.3% / losses −9.1% (out-of-sample 42.9%, +3.12%) | ⚠️ **MOSTLY REPRODUCED.** Win rate, loss size and holdout match. The average return is lower (+3.8%, not +5.4%), mainly because entry here is at the next open with gap-adjusted stops. The claim is corrected in DECISIONS.md |
| AI picks: +0.82% per 10 days net vs +0.34% for the average stock, "better in 8 of 11 years" | +0.73% net per trade with the live 4-ATR stop. **Before costs** it beats the average stock by +0.48% (the claim's gap was the same, 0.48%). **After costs** it beats the average stock in only **6 of 11 years** | ❌ **NOT REPRODUCED as stated.** The "8 of 11" compared returns *after* the picks' costs with the average stock's return without the extra trading. After paying costs, the margin over simply holding the average stock is about **+0.1% per 10 days**: not reliably above zero. Corrected in DECISIONS.md |
| Discovered S1 (in-sample discovery result) | 52.2%, +1.41%; beats the average stock after costs in 9 of 14 years; production account +0.76%, 5 losing years | ⚠️ **WEAK.** Correctly gated: it is not live and needs `/approve`. Recommendation: do **not** approve |
| Intraday / F&O | Not re-tested: the earlier research found no edge after costs for any setup | ⛔ **BLOCKED / experimental.** Shadow mode only |

## What this means for you
1. **The dip-buy is the real edge.** It survives every check: out-of-sample, survivorship, cost stress, and 12 of 14 years beating the average stock. In a realistic account, expect about 70% winners, and a drawdown of about 7% of capital (at 1% risk per tip) in its worst stretch so far. Tips are rare: about 100 a year across the market, and fewer that you will actually see.
2. **Positional is real but slow and streaky.** It wins less than half the time, with large winners. In a 4-slot account: a losing streak of 10 and a 12% drawdown. You need patience for it.
3. **AI picks are a small edge before costs and close to zero after costs**, compared with simply holding stocks. They are capped at 3% of capital at risk. Treat them as the lowest-priority tips. **Owner decision:** you can set `ai_picks: false` in settings.yaml. I did not switch it off myself, because that changes your live tips. (Turning it off would only reduce risk; the mission requires your approval for changes to live recommendations.)
4. **Past results are not a promise.** See KNOWN_LIMITATIONS.md #10–#15.

## Known gaps in this validation
- Ties in the production account are broken alphabetically, not by the live rank.
- Delisted corporate-action adjustment is heuristic.
- The AI is not survivorship-tested.
- Costs are an estimate. Real slippage on small-cap gap days can be larger: see the 0.60% stress column.
- Both the dip-buy and the AI show about 0.0% for 2026 in the by-year excess table. Only a few weeks of 2026 trades have closed, so that figure is not meaningful.
