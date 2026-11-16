# Failure test report (audit 17 Nov 2026)

How to read it:
- **TESTED:** an automated test breaks the thing on purpose. All of them are in `tests/`, run on every change, and passed at the time of writing (full suite: 501 passed in a clean clone, 17 Nov).
- **BY DESIGN:** shown by code inspection, no automated test.
- **NOT TESTABLE HERE:** needs live infrastructure. The reason is stated.

The four questions for each row: does the system **detect** it, stay **safe** (no false or duplicate tip), **recover**, and **tell the owner** when a human is needed?

| # | Failure | Evidence | Detect | Safe | Recover | Tell owner |
|---|---|---|---|---|---|---|
| 1 | Kite API down / network error | TESTED `test_kite_down_rate_limited_or_expired_never_crashes` | yes | yes: no Kite → no intraday/F&O scan; exits use Yahoo | yes, next poll | after 30 min with no prices while logged in (`autopilot.kite_watch`) |
| 2 | Kite 429 rate limit | TESTED (same) + quotes paced to 1/s, batch retried once | yes | yes | yes | logged |
| 3 | Kite token expired / invalid (403) | TESTED: token dropped, `RuntimeError` | yes | yes | at the next daily login | login reminders at 8:45, 9:30, 11:00 |
| 4 | Empty / partial quote response | TESTED `test_empty_or_partial_quote_response_is_ignored` | yes | yes: that stock is skipped, others kept | yes | — |
| 5 | Telegram down (send) | TESTED `test_telegram_down_keeps_tip_and_retries` | yes | the tip is recorded first, then queued | outbox retried every minute | messages arrive when Telegram is back |
| 6 | Telegram down (reading messages) | BY DESIGN `bot._updates_problem` | yes | yes | yes | only if it lasts 30+ min |
| 7 | Stale prices (evening) | TESTED `test_stale_prices_detected`, `test_integrity_check_flags_stale_nifty` | yes | **no new tips**; exits still run | next evening | daily status + "System problem (evening check)" |
| 8 | Weekday market holiday | TESTED `test_holiday_is_not_treated_as_stale` | yes | yes | — | daily status says "market closed" |
| 9 | Missing / unsorted / duplicate bars, zero or NaN prices | TESTED `test_price_loader_cleans_...` | yes (`data_prices.sanitize`) | broken rows never reach a strategy | — | — |
| 10 | Extreme moves, circuits, gaps, zero volume, flat price | TESTED `test_strategies_survive_extreme_and_degenerate_data[4 cases]` | — | no crash, every stop finite and below entry | — | — |
| 11 | Too little history | TESTED `test_insufficient_history_gives_no_signal` | yes | no signal | — | — |
| 12 | Invalid tip numbers (NaN, ∞, ≤0, stop on the wrong side, qty 0, risk above limit, stop > 50% away, target on the wrong side) | TESTED (8 cases) | yes | refused and logged in `skipped_signals.csv` | — | count in the daily status |
| 13 | Same signal twice (restart, double job) | TESTED `test_same_signal_twice_is_sent_once` | yes (signal id) | sent once | — | — |
| 14 | Crash between "record" and "send" | TESTED `test_tip_is_recorded_before_it_is_sent` | — | the record exists, and the message goes via the outbox on the next try | yes | yes |
| 15 | Tip store file corrupted | TESTED `test_corrupted_store_is_restored_and_new_tips_stop` | yes | last good copy restored, **new tips stopped** | after the integrity check passes | 🛑 SAFETY STOP message, then ✅ resumed |
| 16 | Power cut / kill mid-write | TESTED `test_crash_before_rename_leaves_old_store_intact` | — | old file untouched (atomic rename) | yes | — |
| 17 | Two processes writing tips at once (evening job + live engine) | TESTED `test_two_processes_writing_at_once_lose_nothing` (2 × 25 writes, 0 lost) | — | yes (file lock) | — | — |
| 18 | Two workflow runs at once | BY DESIGN `concurrency: swing-system` in the workflow | — | GitHub queues the second run | — | — |
| 19 | GitHub run cancelled / timed out | BY DESIGN: cache save step `if: always()`, keep_alive, hourly cron | yes | state saved at the end of the run | next run (≤ 1 h) | "🔄 System recovered … was not running from … to …" if the gap is > 20 min (TESTED `test_recovery_message_after_a_gap`) |
| 20 | Run crashes repeatedly (bad update, package break) | TESTED `test_failure_alert_once_per_6h` + crash-loop guard | yes | — | hourly cron restart | "⚠️ System problem: a GitHub run failed at: …" |
| 21 | Restart halfway through tracking | BY DESIGN: tips live in `data/private/live_tips.csv` (carried over; D113 fixed the loss); exits use the stored hi/lo since the tip | yes | yes | yes | — |
| 22 | Long job blocking the bot | TESTED `test_jobs_run_in_background_one_at_a_time` | — | the bot keeps answering | — | — |
| 23 | Kill switch | TESTED `test_kill_switch_blocks_new_tips_but_not_exits` | — | **no new tips from any strategy**; exits continue | owner sets it off | "🛑 KILL SWITCH ON" / "✅ OFF" (TESTED `test_kill_switch_change_is_announced`) |
| 24 | Capital / risk not configured | TESTED `test_missing_capital_blocks_tips` | yes | no quantities, no tips | owner fixes settings | safety-stop reason in the daily status |
| 25 | Portfolio overload (too many tips, too much total risk, losing streak) | TESTED `test_portfolio_open_risk_and_position_limits`, `test_losing_streak_cooldown` | yes | refused | after cooldown / closes | count in the daily status |
| 26 | Several failures at once (Telegram down + kill switch + invalid numbers) | TESTED `test_telegram_down_plus_kill_switch_plus_bad_numbers` | yes | nothing recorded or sent, skip logged | — | — |
| 27 | Damaged file at backup time | TESTED `test_local_backup_skips_damaged_files_and_restores` | yes | a damaged file never enters a backup | restore tested | logged |
| 28 | Credential in an error message | TESTED `test_redact_removes_tokens`, `test_logger_scrubs_before_writing` | — | scrubbed before log or report | — | — |
| 29 | Order placement | TESTED `test_no_order_placing_code_anywhere`, `test_kite_client_is_read_only` | — | impossible: no code, and the client refuses those endpoints | — | — |
| 30 | Strategy peeking at the future | TESTED `tests/test_no_lookahead_strategies.py` (4 truncation tests) | — | no difference found | — | — |
| 31 | Retrained AI model worse | BY DESIGN `ml_ranker.train` validation gate (actual run: rank-correlation 0.079 ≥ 0.02 → accepted) | yes | old model kept | next week | "⚠️ AI picks: this week's retrained model failed its validation" |
| 32 | Incomplete (still-forming) candle | BY DESIGN: `setups.py` works on the last **closed** 5-minute bar (`intraday_candidates`). No dedicated test. | — | — | — | — |
| 33 | Special / shortened sessions (Muhurat) | NOT TESTABLE HERE: the engine follows clock times (9:14–15:30). A shortened session is treated as "nothing after the close", and no tips go out after 14:30. | partial | yes (fewer scans) | — | — |
| 34 | Kite WebSocket disconnects | N/A: the system uses REST polling, not WebSocket | — | — | — | — |
| 35 | GitHub cache evicted / lost (all `data/`) | NOT TESTABLE HERE. Mitigation: weekly Telegram backup (forward back to the bot to restore) + `data/universe_history.csv` in git; prices re-download | partial | the empty store means no exit alerts for old tips until restored | manual: forward the backup | the daily status shows "Open tips: 0" |
| 36 | Telegram bot token leaked | FOUND IN HISTORY (3 Nov reports). Scrubbing added; **rotation is the owner's action** | — | — | — | SAFETY_AND_SECURITY_REPORT.md |
