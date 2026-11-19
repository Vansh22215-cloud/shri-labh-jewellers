# ATLAS - owner's guide, running without Claude (updated 19 Nov 2026)

Everything runs by itself on GitHub (free) and talks to you on Telegram. You place every order yourself.
The system only READS prices from Kite: it can never buy, sell or touch your money.

## Your day
| Time | What you do |
|---|---|
| **8:45 am** | Tap the 🔑 Kite login link on Telegram, log in, tap Start (Zerodha needs a human login daily). Missed it? send `/kite` |
| 9:15 am - 3:15 pm | Nothing. "⚡ LIVE BUY … if it holds to the close" = early warning only, **don't buy**. 🛑 stop-loss alert on a stock you hold = **sell** |
| **3:22 pm** | **🧭 ATLAS plan**: all of today's opportunities ranked, money needed, what to avoid - or "No trade today" |
| **3:15 - 3:29 pm** | **The "buy now" (3:20 pm) VANTAGE message = buy.** Exact quantity shown. Then set a GTT stop-loss in Kite at the 🛑 price. Send `/bought SYMBOL` |
| **About 4:00 pm** | **Evening review**: every tip tracked, the Learner and the why-engine update (journal/all_tips.md, learning.md, why_log.md). Final numbers again at 6:40 pm with the official prices |
| After 3:40 pm | 🔴 SELL message on a stock you hold = sell at the **next morning's open** |

## Messages
| Message | What to do |
|---|---|
| **VANTAGE BUY (3:20 pm)** | Buy the quantity shown (max loss ≈ 1% of your money). Only top-300 stocks (D144) |
| **➕ ADD MORE** | Buy the extra quantity shown (winner up 8%+, still within 1% risk) |
| **🛑 Stop-loss / 🔴 SELL / exit alerts** | Do what it says, the same day or the next open as written |
| Live-engine dip-buy / F&O tip | Follow the entry, stop-loss and exit shown |
| **Company of the day** | Reading only - not a buy tip (never tested as a trade) |
| **📒 Weekly learning (Saturday)** | Read: results, main mistake, money at risk. Nothing to do |
| **⚠️ System problem** | Usually fixes itself. Every day for a week -> see "When to get help" |

## Money rules
- Never buy more than the quantity shown. Never move a stop-loss lower.
- Money used up (about 15 trades on ₹51,000)? Skip new tips - don't sell good trades to make room (tested: it loses).
- Expect to lose more than half the trades; winners are about twice the size of losers. 6-8 losses in a row happen.
- **Once a month send `/capital 60000`** (your account value that day). New tips are sized on it. Big changes ask
  for `sure`. `/capital` alone shows the current figure.

## Bot commands
`/tips` open tips · `/bought SYMBOL` · `/sold SYMBOL PRICE` · `/trades` · `/capital` · `/research` · `/health` · `/kite`

## What runs by itself every day (no Claude needed)
- **Finder:** VANTAGE live scan, 3:20 pm buy call, 3:40 pm close scan, ADD MORE, live-engine tips.
- **Learner (6:40 pm):** every tip tracked to the end (`journal/all_tips.md`), each loss explained, patterns found,
  live results compared with the 13-year test, missed big risers, money-at-risk, an un-editable history
  (`journal/ledger.jsonl`), the ranked research list (`journal/research_queue.md`).
- **Self-checks:** a broken scan, stale prices, live results below the tested range or a tampered history
  -> one "system problem" message. The top-300 list rebuilds itself every night.
- Nothing changes your tips by itself: every change needs a passed test **and** your yes.

## Research keeps running by itself (every Friday night)
- GitHub rebuilds all 13 years of VANTAGE trades from the newest prices, describes every trade by ~40 facts and tests
  every possible rule (230+) with the same strict 4 steps used all along, plus the new trades since 20 Nov 2026 that
  nobody has ever looked at.
- Only a rule that passes everything sends you a **🔬 Research result** message with the numbers.
  Reply `/approve LAB-xxxx` to use it, or `/decline LAB-xxxx` to drop it. Nothing changes without your yes.
- Rules can only skip a tip or halve its quantity - never more risk. An approved rule that stops working on the
  new trades is reported to you; `/decline` switches it off.
- `/research` shows the last run. Full report: `journal/auto_research.md`.
- **Every finished tip is asked 'why'** (`journal/why_log.md`): what history expected, what happened, the surprise, the
  main reason, and whether its unusual facts mattered in 13 years. Real patterns go into the weekly research.

## Which rule works on which kind of stock (weekly)
- ATLAS groups stocks by how they actually trade (not just by sector), checks every week which groups' past predicts
  their future, and tests rules per group. A rule that passes is proposed to you (`/approve CTX-xxxx`).

## New strategies ATLAS designs itself (weekly)
- "🧪 ATLAS designed a NEW strategy" -> `/approve FND-xxxx` starts a SILENT live record (no tips, no money).
- After 100+ live trades it asks again: "ready for real tips" -> `/approve FTP-xxxx` (or `/decline`).
  Its tips come in the evening: buy at the next open, with stop-loss, target, quantity and exit alerts.

## Emergency stop
github.com -> repository -> branch `claude/nse-swing-trading-system-sqncpt` -> `swing-system/settings.yaml` -> pencil ->
change `kill_switch: false` to `kill_switch: true` -> Commit changes. All tips stop. Set back to `false` to resume.

## If nothing arrives for a whole market day
github.com -> repository -> **Actions** -> **swing-system** -> **Run workflow** -> task `bot` -> Run. That restarts the
chain (it also restarts itself every hour). Then send `/health`.

## Keep these alive
- **Kite Connect** subscription (₹500/month, developers.kite.trade). If it lapses, Yahoo prices are used.
- GitHub account, this repository and the branch above - never delete. The Telegram bot - never delete.
- API keys live only in GitHub -> Settings -> Secrets. Never paste them anywhere else. If one leaks: create a new
  key on developers.kite.trade, replace it in GitHub Secrets, delete the old one.

## When to get help (Claude or any developer)
- "System problem" every day for a week, or no messages for 2 market days after the restart above.
- The weekly message says a type is "below expected" for several weeks (the live record disagrees with the test).
- You want a change. Point them to `ATLAS.md` (map), `DECISIONS.md` (every decision) and this guide.

Research, not investment advice. Past results do not guarantee future profits.
