# How it works (2026-11)

**One always-on GitHub run** (`scripts/bot_poll.py` -> `swing/daemon.py`) loops every minute for ~5 h 15 min:
answers Telegram, runs due jobs, then hands over to the next run (`scripts/keep_alive.py`). Jobs are claimed in
`data/jobs_done.json` so nothing runs twice. New program code on the branch ends the run within ~10 min so the next
one uses it. Data lives in the GitHub Actions cache (`data/`, incl. the lifelong archive); results that are not
personal are committed by `swing/ci_save.py`; personal files are in `data/private/` and backed up to Telegram.

| Part | Module | When |
|---|---|---|
| Kite login, live quotes, history (data only) | `kite.py` (+ `kite-login.html` on GitHub Pages) | 8:45 prompt; used all day |
| Instant alerts | `alerts.py` | every minute 9:15-15:30 |
| Hourly tips update | `live_scan.py`, `tip_status.py` | 10:20-15:20 |
| Evening trades, tickets, Time Machine | `nightly.py`, `risk.py`, `timemachine.py` | 18:40 |
| Company of the day | `company_research.py` | after the evening trades |
| Research (pre-registered ideas, walk-forward + holdout) | `scripts/run_research.py`, `weekly.py`, `validate.py` | 20:17 |
| Filings, results calendar, insider trades, results summary | `nse_filings.py` | 9:00 brief + every 15 min |
| Intraday paper trading | `intraday_paper.py` | every 5 min 9:35-15:25 |
| Forwarded tips / views / pictures | `bot.py`, `tipcheck.py`, `market_views.py`, `chart_reader.py`, `reply_card.py` | any time |
| Weekly summary, backups, self-checks | `run_weekly.py`, `tip_status.weekly_summary`, `archive.py` | Saturday |
| Strategy engine + backtests | `engine.py`, `families.py`, `backtest.py`, `catalog.py` | evening / research |

Rules that never change: no look-ahead, Zerodha charges in every result, variants counted, holdout never used to
choose, orders never placed by the system.
