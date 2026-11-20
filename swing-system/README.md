# ATLAS - rebuilt 20 Nov 2026

The owner's NSE research and alert system, started again from zero (owner 20 Nov: "we will re-write everything
from start ... I will hold power into this completely"). Runs on GitHub Actions, talks on Telegram, uses Kite
Connect (read-only market data) as its only price source. It never places, changes or cancels an order.

## How it works

| Part | File | What it does |
|---|---|---|
| Candle library | `swing/candles.py` | Downloads every NSE stock + NIFTY 50 / NIFTY BANK / INDIA VIX from Kite: 1 day, 60, 15, 5, 1 minute, everything Kite has; 3/10/30 minutes built from them. Only outside market hours, ~10-minute chunks. |
| Live feed | `swing/live_feed.py` | Kite's streaming feed for every stock, 9:15-3:30: live 1/3/5/10/15/30/60-minute and day candles. |
| Strategies | `swing/strategy.py`, `swing/strategies/` | Each strategy = entry rule (+ optional exit rule). Default stop-loss 1% below entry, targets in multiples of the risk. Written only from the owner's own descriptions. Empty today. |
| Tester | `swing/backtest.py` | Runs a strategy on the Kite library of every stock: 1% stop, target, gaps, 3:20 pm square-off, Zerodha costs + slippage, account simulation. Report starts with the data used. |
| Learner | `swing/learner.py` | Every trade (test and live): did it work, where it works and where it fails (time, weekday, trend, market, VIX, gap, volume, volatility...), why losers lost, ideas to test. Suggests only - never changes anything. |
| Live tips | `swing/tips.py` | Approved strategies on every closed live candle -> BUY tip (entry, stop, target, quantity) -> SELL alert at stop / target / exit rule / 3:20 pm. |
| Runner | `swing/daemon.py` | The always-on GitHub run: login link 8:45 am, live feed, downloads, tests, weekly Learner, nightly private backup. |
| Company of the Quarter | `swing/company_quarter.py` | One company a calendar quarter (research, not a tip), scored from its own NSE filings + Kite price; red flags remove it; no repeats within 4 quarters; next message says how the last pick did. |
| Bot | `swing/bot.py` | /status /kite /capital /stop /resume /tips /strategies /test /learn /approve /unapprove |

## The owner's procedure for every strategy

1. The owner describes the strategy -> it is written in `swing/strategies/<name>.py`.
2. `/test <name>` -> tested on Kite history of every NSE stock -> results + Learner report on Telegram.
3. `/approve <name>` (the owner's decision only) -> it sends live tips.
4. The Learner watches every test and live trade and suggests improvements; each change is tested again and goes
   live only with the owner's yes.

## Data rules

Kite candles only (Yahoo removed). Delisted stocks are not included (Kite lists only today's stocks). Every test
report and message states the data used. Kite candles and personal records stay in GitHub's private cache, never
in this public repository; `results/` holds only results.
