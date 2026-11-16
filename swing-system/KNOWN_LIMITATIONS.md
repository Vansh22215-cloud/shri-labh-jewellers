# Known limitations (read these before trusting any tip)

These are not bugs that can be fixed in code. They are limits of the data, the infrastructure or the method. Each one says what it means for you.

## Infrastructure
1. **GitHub Actions is not a continuous server.**
   - Each run lasts at most ~5¼ hours (GitHub's hard limit is 6 h per job: docs.github.com/en/actions/reference/actions-limits). A new run is then started.
   - At each hand-over the system is **not running for about 1–3 minutes**. If GitHub queues the run, the gap can be longer.
   - A gap of more than 20 minutes is announced ("🔄 System recovered … from X to Y").
   - What it means: an exit alert or intraday move that falls inside a gap can be late or missed. **Always keep your own stop-loss order at the broker**; do not rely on the alert alone.
2. **Data lives in the GitHub Actions cache.**
   - GitHub deletes caches that are not used for 7 days, and caches can be evicted.
   - If the cache is lost, the tip history, trade journal and Kite token are gone.
   - The weekly backup file in Telegram restores them: forward it to the bot.
   - Keep those files in the chat.
3. **GitHub can change its rules.** Free minutes for public repositories, action versions and the Node.js runtime can all change. The monthly check in the runbook covers this.
4. **Code updates reach the running system within about 10 minutes**, not instantly.

## Market data
5. **Kite live coverage is not tick-by-tick.**
   - Kite allows 1 quote request per second (kite.trade/docs/connect/v3/exceptions/), so the live engine gets new prices for each stock every ~30 s.
   - The most active stocks are rescanned every 1–2 minutes, and the whole market every ~20–40 minutes.
   - A move that happens and reverses between two looks is not seen.
6. **Evening strategies use Yahoo daily prices, which arrive late or wrong at times.**
   - When the newest bar does not match the trading day, no new evening tips are sent (stale-data rule).
   - That day is skipped, not guessed.
7. **Kite needs a human login every trading day.**
   - The access token is valid only for that trading day (Zerodha's Kite Connect FAQ).
   - Without the login there are no intraday or F&O tips, and no live Kite prices for exits. Evening tips still work on Yahoo data.
8. **Special sessions** (Muhurat trading, shortened days, unscheduled holidays) are detected only through the stale-data check. Their behaviour has **not been tested on a real special session**.
9. **Partial candles:** the live engine works on intraday bars that are still forming. The logic tolerates this, but no automated test covers it specifically.

## Strategies and backtests
10. **Backtests are not a promise.**
    - Every win rate is measured on 2013–2026 NSE history, with the costs and slippage stated in `BACKTEST_VALIDATION.md`.
    - Market behaviour changes. Live results will differ, and a losing streak of 8–10 tips is normal even for the best strategy here.
11. **Survivorship bias is reduced, not removed.** Delisted stocks were rebuilt from NSE's own daily files, but corporate actions on delisted stocks are adjusted only approximately (from NSE's previous-close field). See `BACKTEST_VALIDATION.md` for the effect.
12. **Intraday and F&O are EXPERIMENTAL.**
    - They have no proven live or backtested edge.
    - They run in shadow mode (`intraday_mode: auto`). They send tips only after their own live record passes the bar, and every such tip is labelled 🧪 EXPERIMENTAL.
13. **Gaps:** a stop-loss is not a guaranteed exit price. A stock that opens far below the stop (results, news, circuit) loses more than the "money at risk" shown on the tip.
14. **Small sample of live tips:** the autopilot judges strategies on their live record. For the first months that record is too small to be meaningful, so it mostly relies on the backtest.
15. **The AI model can stop working.**
    - It is retrained weekly and must pass a validation check, otherwise the old model is kept.
    - A model that passes can still fail in a new market regime. The autopilot pauses it if its live record falls well below its tests.

## Your side
16. **Capital is whatever `settings.yaml` says** (₹45,000). If your real capital changes, change it there. The system never reads your Kite funds or holdings, by design.
17. **The system does not know which tips you actually bought.** Exit alerts are sent for every tip.
18. **The Telegram bot token was exposed in old commits** and must be rotated (PRODUCTION_RUNBOOK). Until you do, anyone who found it could send messages as the bot and read messages you send to the bot (including forwarded tips and backup files). They cannot reach your Kite account; that needs the Kite secret and your login, neither of which was exposed.
