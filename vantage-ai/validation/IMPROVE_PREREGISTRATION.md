# Improvement research: pre-registration (written 17 Nov 2026, BEFORE any of these tests were run)

**Owner's goal:** better trades (higher quality, less risk), more profit, and a good number of trades every week.

**Base for every test:**
- The current VANTAGE AI logic (`replica.py`, the Pine core) on the point-in-time top-300 NSE stocks, 2013–2026, with delisted stocks rebuilt from NSE files.
- Entry at the next open, gap-adjusted stops, 0.35% costs.
- Baseline trades: `trades_FINAL.csv`.

**Periods:**
- Development: signals before 1 Nov 2023.
- Holdout: signals from 1 Nov 2023. The decision is made on the holdout.

**Honesty note:** an exploratory look (17 Nov) at win rates by market breadth and by relative strength used all years, including the holdout. To avoid choosing thresholds from that look:
- Filter thresholds come from the literature or practice: breadth 50%, RS rating 70, sector top third, delivery above its own average.
- The meta-label model learns only from the past (walk-forward).

## A. Quality filters (applied to the baseline trades; features known at the signal close)
| ID | Filter | Source of the threshold |
|---|---|---|
| F1 | Market breadth ≥ 50% (share of the top-300 above their 200-day average) | StockCharts / common practice: 50% line |
| F2 | Relative-strength rank ≥ 70 (6-month return percentile among the top-300) | IBD-style RS rating 70 |
| F3 | Sector in the top third (sector = mean 6-month return of its stocks; Nifty 500 industry map; stocks without a sector are kept) | Moskowitz & Grinblatt industry momentum |
| F4 | Delivery % above the stock's own 20-day average delivery % (NSE MTO files) | Practitioner heuristic (no published evidence) |

**A filter PASSES only if,** on the holdout, it:
1. raises expectancy, and
2. does not lower the win rate, and
3. keeps ≥ 50% of the trades,

and it also raises expectancy in the development period (same direction).

## M. Meta-labeling (López de Prado): a personal likely-win % per signal
- **Walk-forward:** for each year Y from 2016 to 2026, train on trades whose **exit** is before 1 Jan Y; predict the trades signalled in Y.
- **Model:** fixed before the run: `HistGradientBoostingClassifier(max_iter=200, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=40, random_state=0)`.
- **Label:** trade profitable after costs.
- **Features (at the signal close):** setup, dip tier, score, breadth, RS rank, sector rank, ATR %, distance from the 52-week high, relative volume, RSI(14), 20-day return, NIFTY vs its 200-day average, stop distance %, delivery % and its z-score.
- **Rule:** drop the signals whose predicted probability is below the 30th percentile of that year's training predictions. The threshold comes from training data only.
- **Passes under the same criteria as A.** It is also reported for calibration: predicted vs actual win rate by bucket on the holdout.

## E. Exits (re-run of the replica; Breakout and RCP only; dip-buy exits are already short)
| ID | Rule |
|---|---|
| E1 | Break-even: once the high reaches entry + 1R, the stop moves up to the entry price |
| E2 | Time stop: after 20 bars in the trade, exit at the next open if the close is still below the entry |

**An exit rule PASSES if,** on the holdout:
1. expectancy is not lower than the baseline's, and
2. max drawdown at 1% risk improves, or the profit factor rises.

It must also pass in development.

## U. Bigger universe (more trades)
- **Run:** the same logic on every stock with price data (not only the top-300).
- **Buckets:** each signal is put in a bucket by its 20-day average traded value: ≥ ₹50 cr, 20–50, 10–20, 5–10, 2–5, < 2 cr a day.
- **A bucket is ADDED if,** on the holdout:
  1. expectancy > 0, and
  2. profit factor ≥ 1.3, and
  3. win rate ≥ the baseline's minus 3 points.

  The same must hold in development.

## D. More dip-buys (more trades)
| ID | Change (tiers and the Squeeze block unchanged) |
|---|---|
| D1 | RSI(2) < 5 instead of < 2 |
| D2 | RSI(2) < 10 instead of < 2 |

**A variant PASSES if** the ADDITIONAL trades it creates (not in the baseline) have, on the holdout:
1. a win rate ≥ 70%, and
2. expectancy ≥ +1.5%,

and the same holds in development.

## Decision
- Only passing items are proposed to the owner, with their numbers. Failures are reported too.
- Nothing changes in the live system or the TradingView indicator without the owner's approval.
