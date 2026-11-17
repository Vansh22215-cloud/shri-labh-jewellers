# Improvement research: results (17 Nov 2026)

The rules were fixed beforehand in `IMPROVE_PREREGISTRATION.md`. Data: `improve_results.json`, `improve_trades_*.csv`.

**Baseline (current VANTAGE logic):**
- Development (to Oct 2023): 5,745 trades, 46.7% won, +4.08% per trade.
- **Holdout (Nov 2023 onward): 1,519 trades, 42.5% won, +2.91% per trade, profit factor 1.57.**

| ID | Idea | Development | **Holdout** | Verdict |
|---|---|---|---|---|
| F1 | Market breadth ≥ 50% | +4.08 → **+5.08%**, 46.7 → 49.1% won | +2.91 → +2.88%, 42.5 → 42.3% won | ❌ helped in the past, not in recent years |
| F2 | Leader filter (RS rank ≥ 70) | +4.08 → +4.76% | +2.91 → **+2.50%** | ❌ worse recently |
| F3 | Sector in the top third | +4.08 → +4.44% | +2.91 → +2.46% | ❌ |
| F4 | Delivery % above its own average | win 46.7 → 48.4% | win 42.5 → 44.0%, but +2.91 → +2.56% | ❌ more winners, smaller profits |
| M | Meta-labeling (personal likely %, walk-forward) | +4.03 → +4.01% | +2.91 → +2.60% | ❌ not well calibrated (signals given 50–60% won only 38%); only its top group (> 70%) held up: 71% won, 83 trades |
| E1 | Break-even stop after +1R | +4.08 → +3.46% | +2.91 → +2.50% (drawdown smaller) | ❌ less risk but less profit; cuts winners |
| E2 | Time stop after 20 bars | +4.08 → +3.00% | +2.91 → +2.20% | ❌ |
| D1 | Dip-buy RSI(2) < 5 | added trades: 71% won, +1.47% | added: 62% won, +0.65% | ❌ below the 70% / +1.5% bar |
| D2 | Dip-buy RSI(2) < 10 | added: 70% won, +1.20% | added: 67% won, +0.96% (78 more a year) | ❌ below the bar (positive, but weaker than today's dip-buys) |

**U: more stocks (all stocks with data, no top-300 limit),** by average traded value per day:

| Bucket | Signals a year | Development | **Holdout** | Verdict |
|---|---|---|---|---|
| ≥ ₹50 cr | 345 | 47% won, +3.58% | 42% won, +2.47%, PF 1.45 | ✅ |
| ₹20–50 cr | 192 | 47%, +4.61% | 40%, +2.39%, PF 1.37 | ✅ |
| ₹10–20 cr | 155 | 50%, +7.38% | 37%, +1.30%, PF 1.18 | ❌ (holdout PF below 1.3) |
| ₹5–10 cr | 157 | 49%, +5.76% | 44%, +4.71%, PF 1.82 | ✅ |
| ₹2–5 cr | 188 | 50%, +6.75% | 44%, +8.48%, PF 2.41 | ✅ |
| < ₹2 cr | 303 | 51%, +11.05% | **37%, +1.80%, PF 1.24** | ❌ thin stocks: weak recently |

**Supplementary** (not pre-registered; for the decision on a single simple rule):

| Universe | Signals a week | Holdout | Holdout signals a week |
|---|---|---|---|
| All stocks ≥ ₹2 cr/day together | 20 | 41.0% won, +2.91%, PF 1.48 | **25.5** |
| Stocks < ₹2 cr/day | 6 | 36.5% won, +1.43%, PF 1.20 | — |

**Caveat:** small stocks outside the historical top-300 are included only if they still trade today. Delisted small caps are missing, which flatters the development years for small stocks. The holdout is less affected.

## Conclusions
1. **No quality filter beat the current logic on the most recent three years.** Breadth, leaders, sectors, delivery and meta-labeling all looked good in older data and faded since 2023. Adding them would be curve fitting to the past. **Not adopted.**
2. **Exit tweaks cut drawdowns but also cut profits** (they stop out the big winners VANTAGE depends on). **Not adopted.**
3. **Wider dip-buys add trades that are still profitable** (67% won) but weaker than today's dip-buys. **Below the bar; not adopted.**
4. **More good trades: YES, by scanning all NSE stocks that trade ≥ ₹2 crore a day.**
   - That's about **25 signals a week** in the recent holdout, keeping the same quality (+2.9% per trade).
   - The current all-stock scanner also sends thin stocks (< ₹2 cr/day), which were clearly weaker recently.
   - **Proposed change:** the VANTAGE scanner sends signals only for stocks with ≥ ₹2 crore average daily traded value.
