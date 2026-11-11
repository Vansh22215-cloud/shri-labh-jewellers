# Personal NSE Swing-Trading Research System

> **Research, not advice.** No system can guarantee profit. You decide and place every order yourself.
> The system never places orders: it sends risk-checked order *tickets* that you place in the Kite app.

## How it runs (fully automatic - no laptop, no Claude)
Everything runs on **GitHub's free computers** (`.github/workflows/swing.yml`). One always-on run does every job on
time, picks up new code within ~10 minutes, and starts the next run when it ends (an hourly schedule is only a safety
net). Your Telegram bot is **@Vsjshsjsbaksnsjsh_bot**.

| When (IST) | What you get on Telegram |
|---|---|
| ~8:45 am, market days | 🔑 Kite login link - one tap gives live Zerodha prices until 6 am next day (else Yahoo) |
| 9:00 am | 🌅 morning brief: results due, company filings, insider trades for your stocks (only if any) |
| 9:15 am - 3:30 pm, every minute | 🔔 instant alerts: entry reached, near stop, stop hit, target hit, big moves |
| 10:20 am - 3:20 pm, hourly | ⏱ Tips update: every tip of the last 60 days - profit/loss, distance to stop/target, what to do |
| during the day | 📢 new important filings for stocks you follow |
| 6:40 pm | 📋 tomorrow's trades with Time Machine odds + 🎫 order tickets (✅ I placed it / ⏭ Skip), then 🏢 company of the day |
| 8:17 pm | research (silent unless an upgrade is adopted) |
| Saturday | 🗓 weekly summary: channel scorecards, every tip of the week, intraday paper result, report file |
| any time | replies to any tip, setup or chart picture you forward |

## Bot commands
`/bought SYMBOL QTY PRICE [STOP]` · `/sold SYMBOL [PRICE]` · `/trades` · `/score` · `/status` (Kite + live price
check) · `/report` · forward any tip, view, setup or chart picture (stocks, Nifty/Bank Nifty, forex, gold, crypto).

## One-time setup (done)
GitHub -> Settings -> Secrets and variables -> Actions: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `KITE_API_KEY`,
`KITE_API_SECRET`. Kite Connect app redirect URL:
`https://vansh22215-cloud.github.io/shri-labh-jewellers/kite-login.html`. Keys live only in GitHub Secrets.

## Safety
- Risk limits (settings.yaml `risk_limits`): 1% loss per trade, 2% daily loss stop, 3 new trades a day, 25% max order.
- **Kill switch:** `kill_switch: true` in `settings.yaml` stops all tips.
- Personal files (your trades, forwarded tips, tickets, Kite login pass - encrypted) stay out of this public repository.
- Intraday trading is paper-only; it can only ever send tips after passing walk-forward tests and your yes.

## Files
`settings.yaml` settings | `journal/tips.csv` every tip and its outcome | `strategies/` strategy versions |
`validation/` tests | `DECISIONS.md` why every choice was made | `IMPROVEMENTS.md` tested ideas |
`CHANGELOG.md` history | `ARCHITECTURE.md` how the parts fit together.
