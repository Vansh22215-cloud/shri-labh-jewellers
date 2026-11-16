# Daily health check

## Checked automatically (no action unless a message says so)
| Check | Where in code | Message when it fails |
|---|---|---|
| The system is running at all (heartbeat; a gap > 20 min → notice) | `monitor.heartbeat` | 🔄 System recovered … (from–to) |
| A GitHub run step failed | `scripts/keep_alive.py` | ⚠️ System problem: a GitHub run failed at … (≤ 1 per 6 h) |
| Crash loop (runs ending within minutes) | `keep_alive.py` | ⚠️ System check: … restart paused itself |
| Prices fresh for the evening (Nifty bar = trading day) | `nightly.py` + `health.expected_day` | ⚠️ System problem (evening check) + daily status "prices NOT fresh" |
| Self-tests (≈500) pass on the runner each evening | `nightly.run_tests` | System problem (evening check) |
| Kite logged in | daemon | 🔑 at 8:45, ⏰ at 9:30 and 11:00 |
| Kite sending prices while logged in | `autopilot.kite_watch` | ⚠️ logged in but no prices for 30 minutes |
| Tip store readable | `live_engine.load_tips` | 🛑 SAFETY STOP (restored the last good copy) |
| Integrity check before resuming after a stop | `safety.integrity_check` | ✅ Integrity check passed - resumed |
| Telegram delivering (critical messages queued) | `telegram.send_reliable` / `flush_outbox` | Daily status "N messages waiting" |
| Each evening job ran (failures isolated) | `nightly._job` → `evening_status.json` | Daily status "jobs that FAILED" |
| Live record of every strategy vs its tests | `autopilot.throttle` | 🤖 Autopilot: … paused / only 10/10 … |
| AI model still useful after the weekly retrain | `ml_ranker.train` | ⚠️ AI picks: retrained model failed its validation |
| Backups delivered | `archive.send_backups` | ⚠️ Weekly backup could not be delivered |
| Kill switch state | `monitor.kill_switch_watch` | 🛑 KILL SWITCH ON / ✅ OFF |

## The 19:20 daily status: how to read "Why no tips"
- **market closed**: weekend or holiday. Normal.
- **no stock met the tested rules today**: normal. Most days there is no dip-buy.
- **data unavailable (stale prices)**: Yahoo was late. Nothing was sent, which is the safe choice. It retries tomorrow.
- **tips are paused by the safety system**: a safety stop or the kill switch is on (the reason is shown).
- **a strategy job failed** / **the evening scan did not run**: a system problem. It usually recovers. If it repeats for 3 days, see the runbook.

## What YOU check
- **Daily (30 seconds):**
  - The Kite login is done.
  - The daily status arrived at about 19:20. **No daily status means something is wrong.**
- **Weekly:** the Saturday health message and backup file arrived.
- **Before acting on any tip:**
  - The price at the open is close to the tip's entry.
  - The tip is not marked EXPERIMENTAL, unless you accept that risk.
