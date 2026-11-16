# Safety and security report (audit 17 Nov 2026)

Each item lists the evidence: an automated test (name in `tests/`), a code location, or a command and its result. Status is **PASS**, **FIXED** (it was broken and is now fixed) or **OWNER ACTION**.

| # | Certification item | Status | Evidence |
|---|---|---|---|
| 1 | **No automated order execution is possible** | PASS | `test_no_order_placing_code_anywhere` scans every module: no `/orders`, `/gtt`, `place_order`, `modify_order` or `cancel_order`. `test_kite_client_is_read_only`: `kite._get` refuses `/orders`, `/orders/regular`, `/gtt/triggers`, `/user/margins` and `/portfolio/holdings` before any request (`READ_ONLY_PREFIXES = ("/quote", "/instruments")`). The only POST to Kite is the daily login token exchange (`/session/token`). |
| 2 | **No credentials exposed** | **OWNER ACTION** | `git log --all -p` scan: **the Telegram bot token appears in reports/logs committed on 3 Nov 2026** (commits 655dbfa and bf2068e; error text containing the Telegram API URL). It is not in any current file. No Kite key or secret was found anywhere in history. `my_secrets.yaml` is gitignored and was never committed. Fix: every log line and report is now scrubbed (`config.redact`, tests `test_redact_removes_tokens`, `test_logger_scrubs_before_writing`), and reports and logs are not committed. **You must rotate the bot token** (PRODUCTION_RUNBOOK → "Telegram bot token must change"). |
| 3 | **Emergency shutdown works** | FIXED | It did NOT work before (the kill switch only affected old paths). Now every new tip passes `safety.check_new_entry`. `test_kill_switch_blocks_new_tips_but_not_exits` shows no new tip while an open tip still gets its stop-loss alert. ON/OFF is announced (`test_kill_switch_change_is_announced`). |
| 4 | **Critical failures generate notifications** | PASS | Safety stop (`test_emergency_latches_...`), failed run (`test_failure_alert_once_per_6h`), recovery after downtime (`test_recovery_message_after_a_gap`), stale data and Kite no-data (`autopilot.health_alert`, `kite_watch`), failed backup, rejected model. Delivery is retried through the outbox (`test_telegram_down_keeps_tip_and_retries`). |
| 5 | **Invalid market data cannot generate recommendations** | PASS | Stale evening prices mean no new tips (`nightly`: `new_ok`; `test_stale_prices_detected`). Broken bars are removed (`test_price_loader_cleans_...`). Invalid tip numbers are refused (8 cases). Extreme or degenerate data cannot produce a bad stop (`test_strategies_survive_...`). |
| 6 | **Duplicate executions cannot corrupt records** | PASS | File lock + atomic write (`test_two_processes_writing_at_once_lose_nothing`, `test_crash_before_rename_leaves_old_store_intact`). Signal ids stop duplicates (`test_same_signal_twice_is_sent_once`). GitHub `concurrency` runs one workflow at a time. |
| 7 | **Restarts preserve state** | FIXED | The tip store was lost at every run end until 16 Nov (it was in `journal/`, not carried over). It now lives in `data/private/`, which the Actions cache carries over (D113). The rebuild and re-send of the lost 16 Nov tips was verified in the live log ("One-off rebuild: 4 positional tip(s)"). |
| 8 | **Backups can be restored** | FIXED | Weekly Telegram backups were **muted** (label not allowed); now delivered, and a failed delivery is announced. Daily local backups are made only from healthy files and restore was tested (`test_local_backup_skips_damaged_files_and_restores`). Telegram backup restore: forward the file to the bot (`bot._restore_backup`; it merges and never overwrites). |
| 9 | **Learning cannot bypass safety** | FIXED | The autopilot now only tightens (the automatic rank-7 loosening was removed). Discovered strategies need `/approve`. The weekly loop's automatic `live_strategy` / `aggressive_strategy` switches are now proposals only (`allow_auto_promotion: false`). AI retraining is validation-gated with 4 versions kept for rollback. Learning code cannot change `risk_limits`, `kill_switch` or the safety module: no code path writes them. |
| 10 | **Operates without Claude Code** | PASS | Everything runs on GitHub Actions from files in the repo. The full suite passes in a clean clone (498 at the time of the run). Runbook and health check are in the repo. No component calls Claude or any AI service. |
| 11 | **Does not falsely report success** | PASS | The daily status distinguishes market closed / no opportunity / stale data / paused / job failed / evening scan not run (`test_status_explains_why_no_tips`). Telegram "sent" is logged only on HTTP success. Backup failures are reported. |
| 12 | **Limitations disclosed** | PASS | `KNOWN_LIMITATIONS.md`. |

## Security details
- **Secrets:** they live only in GitHub Secrets (4) and reach only the bot step as environment variables. The Kite access token is stored encrypted (Fernet). Logs and reports are scrubbed of anything token-shaped.
- **Repository is public:** personal files (tips, trades, forwarded messages, outbox, skipped signals, backups) are only in `data/private/` and the Actions cache, never in git. The `.gitignore` covers `data/*`, `reports/`, `logs/` and `my_secrets.yaml`.
- **Workflow permissions:** `contents: write` (saves results), `actions: write` (starts the next run). There are no other permissions. The bot only accepts commands from the owner's chat id (`bot.handle`: messages from other chats are ignored).
- **Dependencies:** `pip-audit -r requirements.txt` → "No known vulnerabilities found" (17 Nov 2026). Versions have upper bounds on major releases (`requirements.txt`). Nothing downloads and executes code at run time.
- **Untrusted input:** forwarded pictures are OCR'd in memory or a temp file and deleted. Backup restore accepts only `private/` and `archive/` paths, with no absolute paths or `..`.

## Money-safety rules (enforced in `swing/safety.py`)
- **No assumed capital:** `capital` and `risk_limits.risk_per_trade_pct` must be set explicitly in `settings.yaml`. Otherwise no tip is sent.
- **Per tip:** loss at the stop ≤ 1% of capital (was 2% for the dip-buy, and intraday orders could use up to 100% of capital). Order value ≤ 25% of capital. Stop no more than 50% away. **Option tips:** the modelled loss at the stop ≤ 1% of capital and the premium paid ≤ 25% of capital (found in the second audit pass: option tips used the rank's own risk, up to 5% of capital; test `test_option_tip_risk_is_held_to_the_owners_per_trade_limit`).
- **Portfolio:**
  - at most 15 open tips
  - total money at risk on open tips ≤ 10% of capital
  - per strategy at most: AI picks 3%, positional 4%, discovered 2%, intraday 2%, F&O 3% (the dip-buy keeps the rest)
  - after 8 losing tips in a row, a 3-day cooldown
- **Every alert says:** money at risk in rupees and as a % of the stated capital, a signal id, and that a stop is not a guaranteed price (gap risk). Experimental strategies are labelled.
