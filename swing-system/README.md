# Personal NSE Swing-Trading Research System

> **Research, not advice.** No system can guarantee profit. You decide and place every order yourself.

Every weekday evening this system downloads free market data, checks it, and writes a report
(`reports/latest.html`) with either a ranked list of swing-trade ideas with full plans, or
**"No tips today"** and the reason. It only gives tips if its strategy has passed a strict honesty test
(the "validation gate"). It never connects to your broker.

## Your 3 steps

**Step 1 - Install Python (once, 5 minutes)**
1. Open https://www.python.org/downloads/ and click the yellow **Download Python 3.12** (or newer) button.
2. Open the downloaded file. **Tick the box "Add python.exe to PATH"** at the bottom of the first screen.
3. Click **Install Now**, wait, then click **Close**.

**Step 2 - Get this folder and run setup (once, 1-3 hours, mostly waiting)**
1. Download the file **swing-system.zip** that Claude sent you in the chat. Right-click it -> **Extract All...**
   -> choose e.g. `C:\swing` -> **Extract**. Open the `swing-system` folder inside it.
2. Open the `windows` folder and **double-click `SETUP.bat`**. If Windows says "Windows protected your PC",
   click **More info -> Run anyway**.
3. Leave the black window open until it says **DONE**. Your first report opens in your browser. From now on
   it runs by itself every weekday at 6:30 pm (and catches up if your PC was off), and a self-check runs on
   Saturdays.

**Step 3 (optional) - Get the report on your phone via Telegram**
Already done for you: your bot token is saved in `my_secrets.yaml` (private, never uploaded). Just open your bot
**@Vsjshsjsbaksnsjsh_bot** in Telegram and send it any message (e.g. "hi"). Reports then also arrive in Telegram.

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
