# Round 7 results: how trend-follow (RCP) trades end (18 Nov 2026)
**Rules:** `IMPROVE7_PREREGISTRATION.md`. **Data:** `improve7_results.json`, `improve7_trades_X*.csv`.

## RCP trades, holdout (Nov 2023+)
| ID | Rule | Trades | Won | Profit per trade | Profit per day held | Worst run of losses | Verdict |
|---|---|---|---|---|---|---|---|
| Today | SELL or 60 days | 1,161 | 42.8% | +3.30% | 0.078 | −84 | |
| X1 | no SELL, 60 days | 1,101 | 49.0% | +3.39% | 0.067 | −96 | ❌ |
| **X2** | **SELL kept, 120 days** | **978** | **40.9%** | **+5.19%** | **0.089** | **−61** | ✅ |
| X3 | no SELL, 120 days | 781 | 44.7% | +6.73% | 0.075 | −66 | ❌ less profit per day |
| X4 | SELL only after 20 days | 1,136 | 44.8% | +3.41% | 0.077 | −77 | ❌ |
| X5 | 120 days + trailing stop | 1,153 | 37.6% | +2.24% | 0.053 | −62 | ❌ |

X2 in development: +4.19% → +6.39% per trade, worst run −97 → −79.

## A real ₹45,000 account
Supplementary, not pre-registered. Signals are taken in random order while cash allows; median of 15 runs.

| | Development: yearly / worst fall / new trades a week | Holdout: yearly / worst fall / new trades a week |
|---|---|---|
| Today | 19.0% / −17.1% / 4.2 | 14.7% / −20.1% / 2.7 |
| X2 | 19.3% / −16.4% / 3.3 | **18.8% / −14.6% / 2.0** |

## Other findings from the same research day
- **Money, not signals, is the limit:** about 70% of signals cannot be taken with ₹45,000, because the money is already in open trades.
- **"Take the signals that need the least money first"** beat random picking on the top-300 stocks, but not on all NSE stocks. Rejected.
- **Smaller risk per trade** (0.25–0.75%) means more trades but lower yearly growth. The 1% setting stays.

**Status:** X2 passed. It is reported to the owner and not applied without his yes.
