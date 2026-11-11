# Personal NSE Swing-Trading Research System

> **Research, not advice.** No system can guarantee profit. You decide and place every order yourself.

Every weekday evening this system downloads free market data, checks it, and writes a report
(`reports/latest.html`) with either a ranked list of swing-trade ideas with full plans, or
**"No tips today"** and the reason. It only gives tips if its strategy has passed a strict honesty test
(the "validation gate"). It never connects to your broker.

## How it runs (no Claude, no laptop needed)
Everything runs **automatically on GitHub's free computers** (GitHub Actions, file `.github/workflows/swing.yml`):
| When (IST, weekdays) | What you get on Telegram |
|---|---|
| 10:20 - 15:20, hourly | only if something needs action: a new buy signal, or your stop/target was hit |
| 18:40 | tomorrow's trades (stock, buy range, stop, target, quantity) + the full report as a file |
| every hour | answers to tips you forward, and to /bought /sold /trades |
| 20:17 | (silent) tests one pre-registered improvement idea |
| Saturday 10:17 | (silent) weekly self-check; once a month it re-runs all strategy searches |

**One-time setup (2 minutes, on your phone):** GitHub repo -> Settings -> Secrets and variables -> Actions ->
New repository secret: `TELEGRAM_BOT_TOKEN` = your bot token, and `TELEGRAM_CHAT_ID` = your chat id.

**Record your trades** by messaging the bot: `/bought ICICIBANK 5 1425 1340` (symbol, qty, price, stop) and
`/sold ICICIBANK 1500`. These stay private (not in the public repository).

Everything runs on GitHub on its own (each run starts the next); no laptop and no Claude session is needed.

## Check any tip on Telegram
Forward any stock tip (from a channel, group or friend) to your bot **@Vsjshsjsbaksnsjsh_bot**. Within seconds it
answers 🟢 GOOD / 🟡 RISKY / 🔴 AVOID with reasons, using real prices and Zerodha charges. Send /score to see
how forwarded tips actually turned out, and /report for tonight's summary. (The bot runs on your PC, so it answers
while the PC is on; tips sent while it was off are answered when it starts.)

## Everyday use
- Read `reports/latest.html` each evening. In **paper mode** (first 8 weeks) do not use real money - watch how
  the ideas perform.
- When you actually buy something, add one line to `my_trades.csv` (Excel or Notepad):
  `INFY,2026-11-03,1500,7,1430` = symbol, buy date, buy price, quantity, stop. The report then tells you each
  evening whether to hold, move your stop, or exit.
- **Kill switch:** in `settings.yaml` change `kill_switch: false` to `kill_switch: true` to stop all tips.

## Files (for the curious)
`settings.yaml` your settings | `reports/` daily reports | `validation/latest.html` backtest & gate |
`stocks/` running notes per stock | `journal/tips.csv` every tip and its outcome |
`DECISIONS.md` why every default was chosen | `IMPROVEMENTS.md` tested ideas | `CHANGELOG.md` history |
`logs/system.log` errors.

## Status (2026-11-03)
Three honest searches, all with Zerodha charges, all **FAILED** the validation gate:
| Search | Strategies tested | Fair walk-forward result | Newest untouched period |
|---|---|---|---|
| Swing (days-weeks) | 556 | beat NIFTYBEES in 2 of 10 years | +5.4% vs liquid fund +9.8% |
| Short-term (1-5 days) | 1,080 | beat NIFTYBEES in 1 of 10 years | -13.2% |
| Intraday (same day) | 120 | lost Rs 985 on Rs 45,000 | -2.6% |

Short trades fail mainly because of **charges and slippage on every trade**. So the daily report says
**"No tips: strategy not validated. Use the index fund."** All searches re-run monthly by themselves.
Details: `validation/search.html`, `validation/search_short.html`, `validation/search_intraday.html`.
