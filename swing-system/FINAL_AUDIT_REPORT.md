# Final audit report (16–17 Nov 2026)

**Scope:** every module in `swing/`, the GitHub workflow, data and cache handling, the Kite and Telegram integrations, every live strategy and its backtest.

**Method:** 7 passes.
1. Map the system (`SYSTEM_ARCHITECTURE.md`).
2. Audit the code, data and backtests.
3. Failure-injection tests (`FAILURE_TEST_REPORT.md`).
4. Repair.
5. Regression and independent re-validation (`BACKTEST_VALIDATION.md`).
6. A second audit of my own changes.
7. Documentation.

**Severity:**
- **CRITICAL**: could send a dangerously wrong tip or lose records.
- **HIGH**: a safety control that did not work.
- **MEDIUM**: wrong or missing information.
- **LOW**: cosmetic or robustness.

## Findings and fixes
| # | Severity | Finding | Fix | Evidence |
|---|---|---|---|---|
| 1 | CRITICAL | The live tip store (`journal/live_tips.csv`) was **not carried between GitHub runs**. Every ~5 h hand-over lost all open tips: no exit alerts, an empty `/tips`, the autopilot blind. | Moved to `data/private/` (cached); the 16 Nov tips were rebuilt and re-sent | D113; live log "One-off rebuild: 4 positional tip(s)" |
| 2 | CRITICAL | Position size: intraday orders could use **up to 100% of capital**; the dip-buy used 2% risk; option tips up to **5%** | One sizing function (`safety.size`): 1% risk, order ≤ 25% of capital; option loss ≤ 1% | `test_invalid_tip_numbers_are_refused`, `test_option_tip_risk_is_held_to_the_owners_per_trade_limit` |
| 3 | HIGH | The **kill switch did not stop** the dip-buy, positional, AI, discovered or live-engine tips | Central gate `safety.check_new_entry` in `issue_tip`, the single path for every tip | `test_kill_switch_blocks_new_tips_but_not_exits` |
| 4 | HIGH | **No validation of tip numbers.** NaN, a stop on the wrong side or quantity 0 could be sent | `safety.validate`: 8 checks; refusals logged to `skipped_signals.csv` | 8 parametrised tests |
| 5 | HIGH | **No portfolio limits.** Unlimited open tips and total risk | Max 15 open, ≤ 10% total at risk, per-strategy caps, 8-loss cooldown | `test_portfolio_open_risk_and_position_limits`, `test_lower_ranked_...`, `test_losing_streak_cooldown` |
| 6 | HIGH | **Telegram bot token in committed reports** (3 Nov) — the repo is public | Redaction on every log line and report; reports not committed. **The owner must rotate the token** | `test_redact_removes_tokens`, `test_logger_scrubs_before_writing` |
| 7 | HIGH | The tip store could be **corrupted** by two writers or a crash mid-write | fcntl lock, atomic replace, last-good backup restored and a safety stop latched | `test_two_processes_...`, `test_crash_before_rename_...`, `test_corrupted_store_...` |
| 8 | HIGH | **Send-then-record**: a crash after sending lost the record. A restart could re-send the same tip | Record first (with a signal id), then send; dedupe on the id; retrying outbox | `test_tip_is_recorded_before_it_is_sent`, `test_same_signal_twice_is_sent_once` |
| 9 | HIGH | **Learning could loosen risk on its own.** The autopilot widened to rank 7, the weekly loop switched live strategies, discovered strategies went live by themselves | The autopilot only tightens; switches are proposals; `/approve` is required; AI retrain validation gate with rollback versions | `test_autopilot`, `test_discovery`, `test_ml_ranker` |
| 10 | HIGH | **Stale prices looked fresh** (the freshness check used an NSE file GitHub often cannot reach), so evening tips could be made on yesterday's data | A second check that Nifty traded today; no new tips on stale data | `test_stale_prices_detected`, `test_holiday_is_not_treated_as_stale` |
| 11 | HIGH | **Kite quotes were sent faster than the documented 1 request/s**; one 429 wiped the whole price refresh | Pacing ≥ 1.05 s, each batch isolated and retried, prices validated | `test_kite_down_rate_limited_or_expired_never_crashes`, `test_empty_or_partial_quote_...` |
| 12 | HIGH | The Kite client could in principle call any endpoint | Allowlist: `/quote`, `/instruments` only; order code banned by test | `test_kite_client_is_read_only`, `test_no_order_placing_code_anywhere` |
| 13 | MEDIUM | **Weekly backups were silently muted** (their Telegram label was not on the allowed list) | Label allowed; delivery failure announced; daily local backups with tested restore | `test_local_backup_skips_damaged_files_and_restores` |
| 14 | MEDIUM | Evening jobs nested: one crash skipped all later strategies | Independent jobs; status file | D114 |
| 15 | MEDIUM | Runner clock on UTC: from 0:00 to 5:30 IST "today" was yesterday | Process TZ = Asia/Kolkata | D114 |
| 16 | MEDIUM | Long jobs blocked the bot (no exit alerts during a ~1 h research run) | Background job thread | `test_daemon_jobs` |
| 17 | MEDIUM | **Silent failures.** No notice when the system was down, and no reason given for "no tips" | Heartbeat with recovery notice, daily status with the reason, weekly health | `test_monitor` (4) |
| 18 | MEDIUM | The same stock could be tipped again while its tip was still open; stale intraday tips stayed open | `already()` blocks; evening expiry | `test_live_engine` |
| 19 | MEDIUM | Intraday was switched on with **no proven edge** | Shadow mode (`intraday_mode: auto`); EXPERIMENTAL label | KNOWN_LIMITATIONS #12 |
| 20 | MEDIUM | Survivorship: 359 delisted/renamed stocks of the historical top-500 had no prices (28% of the 2013 top-300) | Rebuilt from NSE daily files; results with and without them | BACKTEST_VALIDATION.md |
| 21 | LOW | "Tomorrow" in Friday tips | "the next market open" | `test_high_prob` |
| 22 | LOW | Brief Telegram outages alarmed the owner | Alert only after 30 min | `test_bot_tips` |
| 23 | LOW | Broken price rows (duplicates, NaN, high < low) reached strategies | `data_prices.sanitize` | `test_price_loader_cleans_...` |
| 24 | MEDIUM | Tip messages quoted research figures that do not reproduce (positional +5.4%, AI "8 of 11 years") | Messages now quote the independent re-test | BACKTEST_VALIDATION.md |

## Checked and found correct
- **No look-ahead** in any live strategy. Truncation tests (`test_no_lookahead_strategies.py`) cut the history at many dates and show that the signals for past days never change.
- **Point-in-time universe:** each month uses only data before that month.
- **No order placement code** anywhere. Dependencies: `pip-audit`, no known vulnerabilities.

## Accepted (not fixed in code)
- Some modules still default to ₹45,000 when computing a size. This is harmless: the safety gate reads `settings.yaml` itself and refuses every tip if capital is not set there (`test_missing_capital_blocks_tips`).

## Backtest validation (summary; details in BACKTEST_VALIDATION.md)
| Strategy | Claim | Independent result (after costs, survivorship-corrected) | Verdict |
|---|---|---|---|
| Dip-buy | 76%, +2.5% | 76.5%, +2.39%; out-of-sample 75.3%, +2.79%; beats the average stock in 12 of 14 years | ✅ reproduced |
| Positional | 45%, +5.4% | 45.3%, **+3.76%**; out-of-sample 42.9%, +3.12% | ⚠️ average overstated → corrected |
| AI picks | beats the average stock in 8 of 11 years | 6 of 11 after costs; margin about +0.1% per 10 days | ❌ overstated → corrected, labelled small edge |
| Discovered S1 | (candidate) | 52%, +1.41%; realistic account +0.76%, 5 losing years | ⚠️ weak, needs approval: do not approve |
| Intraday / F&O | — | no edge after costs in the research | ⛔ experimental, shadow only |

The validator itself had 3 defects found during this audit, all fixed before the final run:
- a regime-mask type error
- a price-weighted "average stock" benchmark
- an unrealistic every-signal drawdown

Delisted-stock prices needed corporate-action repair: NSE's old files left splits and bonuses unadjusted.

## Production checklist
| Item | Status |
|---|---|
| Read-only with respect to Kite; no order code | ✅ READY |
| Every new tip passes the safety gate (kill switch, safety stop, validation, portfolio limits) | ✅ READY |
| Risk per tip ≤ 1% of stated capital, order ≤ 25% | ✅ READY |
| Tip records survive restarts, are locked, atomic and backed up | ✅ READY |
| No silent failures (heartbeat, daily status, failed-run alerts) | ✅ READY |
| Backups delivered and restorable | ✅ READY |
| Learning cannot raise risk or go live without approval | ✅ READY |
| Full test suite passes in a clean clone | ✅ READY (501 passed, 17 Nov) |
| **Telegram bot token rotated** | ⛔ **BLOCKED: owner action** (runbook) |
| **Intraday / F&O tips** | ⛔ **BLOCKED** (experimental, shadow mode until their live record passes; labelled) |
| Continuous 24/7 monitoring | ⚠️ LIMITED: GitHub Actions is not a continuous server (1–3 min gaps at hand-overs); keep stop orders at the broker |
| Special sessions (Muhurat, shortened days) | ⚠️ UNTESTED live; protected only by the stale-data rule |
| Partial-candle handling in the live engine | ⚠️ No dedicated test |
| Data-cache loss | ⚠️ Recoverable only from the weekly Telegram backup: keep those files |
