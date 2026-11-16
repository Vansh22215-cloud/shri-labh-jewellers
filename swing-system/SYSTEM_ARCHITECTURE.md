# System architecture (from the code, audit 17 Nov 2026)

The code is the source of truth. Older documents (ARCHITECTURE.md, README.md) describe earlier stages.

## 1. Where it runs
| Piece | What it really is |
|---|---|
| Computer | GitHub Actions, a free Ubuntu runner for public repositories. **It is not a permanent server.** One run lasts at most 315 minutes (`SWING_DAEMON_MINUTES`; GitHub's hard limit is 6 hours). At the end it starts the next run itself (`scripts/keep_alive.py`), and an hourly cron start is a safety net. Between two runs there is a gap of about 1–3 minutes. |
| Workflow | `.github/workflows/swing.yml` (the copy on **main** is the one GitHub runs). It checks out the branch `claude/nse-swing-trading-system-sqncpt`, installs `requirements.txt`, restores `swing-system/data/` from the Actions cache, runs `scripts/bot_poll.py` → `swing.daemon.run()`, starts the next run, then saves `data/` back to the cache and commits non-personal results (`swing/ci_save.py`). |
| Concurrency | `concurrency: swing-system` means one run at a time and the next one waits. Two runs can never write the same data. |
| Persistent state | **Only `swing-system/data/`** survives between runs, via the Actions cache (~107 MB, one entry per run, newest restored). Personal files live in `data/private/` (never committed). Code and research results live in git. |
| Secrets | GitHub Secrets: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `KITE_API_KEY`, `KITE_API_SECRET`. They are passed as environment variables to the bot step only. The Kite login pass is stored encrypted (Fernet, key derived from the secret) in `data/`. |
| Clock | The process clock is set to Asia/Kolkata in `swing/config.py`, because the runners use UTC. |

## 2. The daemon (one run)
`swing/daemon.py` loops once a minute until about 2 minutes before the run ends:
1. Every 10 minutes it checks whether new code was pushed. If so, it hands over to a fresh run, but only once no job is running.
2. Every 30 minutes it tracks forwarded tips and views.
3. `bot.poll_once()` answers Telegram messages: forwarded tips, pictures, watchlists, `/tips` `/health` `/status` `/kite` `/approve` and others.
4. `minute_tasks()`:
   - **monitor**: heartbeat and recovery notice, kill-switch notice, outbox redelivery, safety-stop integrity check, 7:20 pm daily status, Saturday weekly health, 8 pm local backup
   - Kite login prompt (8:45) and reminders (9:30, 11:00)
   - morning brief and filings
   - **live engine** (09:14–15:30, background thread)
   - intraday paper scanner (only if the engine is off)
   - weekly intraday backtest on Kite history
   - price alerts (muted)
5. Scheduled jobs (`due()`), run **one at a time in a background thread** (`run_job`):
   - hourly `scan` (muted)
   - **`nightly` at 18:40** on weekdays
   - `company` at 18:45
   - `research` at 20:17
   - `weekly` on Saturday 10:17

## 3. Signal journeys
### Evening strategies (`nightly.py`, 18:40)
```
update data (Yahoo daily bars + NSE files) -> freshness check (last Nifty bar vs the NSE trading day; "did Nifty
trade today" from Yahoo 5-min bars) -> if NOT fresh: exits only, no new tips, alert
-> exits:   dip-buy (close > 5-day avg / 10 days), positional (RCP SELL / 60 days), AI (10 days), discovered (hold)
-> new:     high_prob.send_evening (dip-buy D98 + confirmation tiers D105, F&O ITM call version)
            positional.send_evening (Rolling Candle Profile BUY within 10% of the 52-week high)
            ml_ranker.send_evening (AI picks; weekly retrain gated by validation)
            discovery.maybe_search (weekly) + discovery.evening (shadow / approval / tips of approved strategies)
-> autopilot.health_alert + autopilot.throttle -> data/evening_status.json
```
### Intraday / F&O (`live_engine.py`, 09:14–15:30, needs the Kite login)
```
every 30 s: Kite quotes for ~2,600 stocks (6 batches, paced 1/s) -> exits() for every open tip (only prices AFTER
the tip count) -> update_shadows()
continuously: 5-minute candles from Kite, one stock every ~0.4-1 s (2 of 3 slots go to the stocks moving most)
-> intraday_candidates (setups.py: ORB, VWAP, range, EMA pullback ... on the LAST CLOSED bar)
-> gates (Kite-history test, ATR noise, volume, trend) -> rank 1-10 -> record_shadow (every qualified setup)
-> live-proof gate (intraday_mode auto: >= 40 followed results, >= 65% winners, positive average)
-> min rank, liquidity >= Rs 1 cr, breakout still holding, Nifty agrees, before 14:30 -> issue_tip
```
### Every new tip: `live_engine.issue_tip` (the only exit door)
```
safety.check_new_entry: kill switch -> latched safety stop -> capital/risk explicitly configured -> tip numbers
valid -> portfolio limits (open tips, total money at risk, losing-streak cooldown)
-> duplicate check (persistent signal id) -> RECORD in data/private/live_tips.csv (file lock + atomic write +
healthy backup) -> THEN send to Telegram (telegram.send_reliable; failed critical messages go to the outbox and are
retried every minute)
```
Refused signals are written to `data/private/skipped_signals.csv` with the reason.

## 4. External dependencies
| Service | Used for | Failure behaviour |
|---|---|---|
| Kite Connect (paid, read-only) | live quotes, 5-minute and daily history, NFO instruments | Client is hard-limited to `/quote*` and `/instruments*`. 403 drops the token. Batches are paced and retried. Otherwise Yahoo prices are used or the stock is skipped. No Kite means no intraday or F&O scanning. |
| Yahoo Finance (yfinance) | daily history (all evening strategies), fallback prices | Stale data stops new evening tips and alerts the owner. |
| NSE public archive | bhavcopy (universe, freshness), F&O, delivery, filings | Can be unreachable from GitHub. The trading-day check is independent of it. |
| Telegram Bot API | everything the owner sees | Critical messages are queued in the outbox and retried. A read problem lasting 30+ minutes alerts the owner. |
| GitHub Actions + cache | compute and persistence | Crash-loop guard, hourly cron safety start, "System problem" message on a failed step, recovery notice after a gap. |

## 5. Modules (main ones)
- **Live paths:** `safety`, `live_engine`, `high_prob`, `confirmations`, `orderflow` (order blocks), `positional`, `rolling_profile`, `ml_ranker`, `discovery`, `autopilot`, `monitor`, `telegram`, `bot`, `kite`, `data_prices`, `health`, `nightly`, `daemon`, `archive` (backups), `setups` (intraday), `options_check` (Black-Scholes for options).
- **Research and older paths (not sending tips):** `strategy`, `backtest`, `engine`, `search`, `weekly` (now only proposes), `families`, `patterns`, `catalog`, `features`, the `validation/*.py` research scripts.
- **The old "a3" swing strategy** is switched off (`normal_a3_tips: false`). Its walk-forward machinery still runs in research, and its switches now need the owner's approval (`allow_auto_promotion: false`).

## 6. Claims vs implementation
| Claim (older messages / docs) | Reality |
|---|---|
| "Scans the whole market every few seconds" | Quotes for all stocks every ~30 s. 5-minute candles: the most active stocks every 1–2 minutes, the full ~2,600 every ~20–40 minutes. |
| "Runs 24/7" | Chained runs of ≤ 5 h 15 m, with 1–3 minute gaps at hand-overs (one falls inside market hours). |
| "Kill switch stops everything" | **It did not** (only old paths). Fixed on 17 Nov: it now blocks every new tip, while exits keep running. |
| "1% risk per trade" | **The dip-buy used 2%, and intraday orders could use up to 100% of capital.** Fixed on 17 Nov: 1% and at most 25% per order, enforced centrally. |
| "Weekly backups to Telegram" | **They were muted.** Fixed on 17 Nov. Daily local backups were added too. |
| "Tips are tracked to the end" | **The tip store was lost at every restart until 16 Nov.** Fixed (D113). |
| Intraday "on" | Back in shadow (paper) mode until its own live record proves it, per the owner's 17 Nov mission. |
