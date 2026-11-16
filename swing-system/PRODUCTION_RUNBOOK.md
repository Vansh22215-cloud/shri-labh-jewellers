# Production runbook

Everything below works from a phone. Nothing needs Claude, a laptop or a command line.

## Normal day (what happens by itself)
| IST | Event | You |
|---|---|---|
| 08:45 | 🔑 Kite login link (reminders 9:30, 11:00) | **Tap it, log in, tap Start.** The only daily duty. |
| 09:14–15:30 | Live engine scans with Kite data; exit alerts for open tips | Act on exit alerts |
| 18:40 | Evening scan: exits first, then new dip-buy / positional / AI / approved-discovered tips (only on fresh prices) | Buy at the next open if you choose |
| 18:46 | Company of the day | — |
| 19:20 | 🩺 **Daily status**: what ran, what was sent, why there were no tips | Glance at it |
| 20:00 | Local backup (14 days kept) | — |
| Sat 10:30 | 📊 Weekly strategy health + weekly backup file | **Keep the backup file in the chat** |

Commands you can send the bot: `/tips` (every open tip) · `/health` (status now) · `/status` (Kite) · `/kite` (login link) · `/approve S1` (allow a proven discovered strategy).

## Emergencies
| Situation | Do this |
|---|---|
| **Stop all new tips now** | github.com → repo → branch `claude/nse-swing-trading-system-sqncpt` → `swing-system/settings.yaml` → ✏️ → set `kill_switch: true` → Commit. Within ~10 min you get "🛑 KILL SWITCH ON". Exit alerts continue. Undo the same way (`false`). |
| 🛑 "SAFETY STOP: new trade tips are paused" | Nothing. It clears itself after its integrity check passes (✅ message). If it stays more than 2 days, read the reason line and see "When to get help". |
| ⚠️ "System problem: a GitHub run failed" | Nothing at first: it restarts itself. If it repeats every day for 3+ days, open GitHub → Actions → the red run → read the failed step (see below). |
| 🔄 "System recovered … was not running from X to Y" | Check `/tips` against your broker positions; exits that fell in the gap may have been missed. |
| No message at all for 2 market days | GitHub → Actions → "swing-system" → **Run workflow** (task `bot`). If it fails, see "When to get help". |
| Kite "Invalid checksum" / login refused | GitHub → Settings → Secrets → re-enter `KITE_API_SECRET` exactly as the Kite developer console shows it. |
| Telegram bot token must change (leak) | Telegram → @BotFather → `/revoke` → pick the bot → copy the NEW token → GitHub → repo → Settings → Secrets and variables → Actions → `TELEGRAM_BOT_TOKEN` → Update. The chat stays the same. |
| Tips lost / store damaged | The system restores its last good copy by itself. If everything is gone (cache lost): forward the latest **weekly backup file** from the chat to the bot; it merges it back. |

## Reading a failed GitHub run
GitHub → Actions → the red run → `run` job → the red step:
- **Install packages**: a dependency could not install. Wait a day; if it persists, a developer must adjust `requirements.txt`.
- **Run bot**: look for `ERROR` lines near the end. Credentials are scrubbed from the log.
- **Save data**: the GitHub cache failed. Data from that run is lost; the next run continues from the previous save.

## Changing settings safely
Edit `swing-system/settings.yaml` on GitHub (any change is applied within ~10 min). Safe to change: `kill_switch`, `capital`, `risk_limits` (`risk_per_trade_pct` max 5, `max_open_positions`, `max_open_risk_pct`, `loss_streak_pause`), `intraday_mode` (`auto`/`on`/`off`), `positional_tips`, `ai_picks`, `ai_top`, `min_rank`. **Do not** delete `capital` or `risk_limits`: without them the system refuses to size any tip (by design).

## Monthly / quarterly maintenance (owner, 10 minutes)
- **Monthly:**
  - Kite Connect subscription still active (developers.kite.trade).
  - Saturday backups are arriving.
  - The weekly health shows no strategy paused for long.
  - GitHub → Actions has no long red streaks.
- **Quarterly:**
  - Forward one backup file to the bot to test that restore works ("Backup restored: N files").
  - Read `KNOWN_LIMITATIONS.md` again.
  - If GitHub shows "Node.js deprecated" warnings becoming errors, a developer must bump the action versions in `.github/workflows/swing.yml` (on **main**).

## When to get help (any Python developer, no Claude needed)
- **Hand over:** `SYSTEM_ARCHITECTURE.md`, `DECISIONS.md`, `FINAL_AUDIT_REPORT.md` and this runbook.
- **Running the tests:** `cd swing-system && pip install -r requirements.txt && python -m pytest -q tests` (≈1 minute, all must pass).
- **Always:** never add order placement. The Kite client refuses it by design (`kite.READ_ONLY_PREFIXES`).
