# Owner's guide - running the system without Claude

Everything runs by itself on GitHub (free) and talks to you on Telegram. You place every order yourself;
the system never touches your money or your Zerodha account.

## Your only daily job
- **8:45 am (market days): tap the "🔑 Log in to Kite" link** on Telegram, log in, tap **Start**.
  Zerodha requires a human login every day. Late login = intraday/F&O scanning starts only after you log in.

## What comes on Telegram
| Message | What to do |
|---|---|
| **Intraday trade** (instantly, 9:35 am - 2:30 pm) | Optional. Small quantity, always use the stop-loss, square off by 3:15 pm |
| **F&O trade** (option buying) | Buy the option shown; exit on the alert |
| **Normal trade (dip-buy)** in the evening, rank 8-10/10 | Buy at next morning's open; sell on the exit alert (~4 days) |
| **Positional trade** in the evening, rank 6/10 | Buy at next open; hold until the SELL alert (weeks); expect several small losses before a big win |
| **AI pick** in the evening, rank 6/10 | Buy at next open; sell after 10 trading days (alert). ~half win, but winners beat the market on average |
| **Discovered strategy Sx** in the evening, rank 7/10 | A rule the system invented, tested on 13 years AND proved on live data itself. Buy at next open, sell on the alert |
| **🧪 New strategy promoted / retired** | Information only - the system found (or dropped) a strategy by itself |
| **Exit alert** (✅ ⛔️ ⏰ 🔻 ⌛) | Do what it says |
| **Company of the day** | Read if you like |
| **⚠️ System problem / 🤖 Autopilot** | Usually nothing to do - it explains itself. Repeating every day for a week? see "When to get help" |

Forward any tip, chart picture or watchlist album to the bot - it answers with a score and reasons.

## The autopilot (it watches itself)
- Every closed tip's real result is recorded. If a strategy loses money live over its last 20-30 tips, it is
  throttled (dip-buy: only 10/10), paused for 60 days (positional) or paused until its followed setups turn
  positive (intraday). You get one Telegram message each time, with the numbers.
- Intraday becomes a little less strict (rank 7) for setups whose followed results are clearly good.
- If a GitHub run fails, prices are stale, self-tests fail or Zerodha stops sending prices: one "System problem"
  message (at most once a day / 6 hours). It retries by itself.

## It invents new strategies by itself
Every week it combines market building blocks into hundreds of new rules, keeps only those that won in 3 separate
periods of 13 years, follows them silently on live data, and lets them send tips only after ~20 live trades prove
them. Losing ones are retired automatically.

## Changing settings (no code needed)
On github.com open the repository → branch `claude/nse-swing-trading-system-sqncpt` → `swing-system/settings.yaml`
→ pencil icon → edit → **Commit changes**. The system picks it up within ~10 minutes.
| Setting | Meaning |
|---|---|
| `kill_switch: true` | STOP all tips (emergency) - set back to `false` to resume |
| `capital: 45000` | Your trading capital (quantities are sized from it) |
| `intraday_mode: on` / `off` | Intraday tips on/off |
| `positional_tips: true/false` | Positional tips on/off |
| `ai_picks: true/false`, `ai_top: 5` | AI picks on/off, how many per evening |
| `min_rank: 8` | Lowest rank sent (9 = fewer, stronger tips) |
| `risk_limits` | 1% risk per trade, 25% max per order, 2% daily-loss stop |

## Keep these alive
- **Kite Connect subscription** (Rs 500/month at developers.kite.trade) - if it lapses, Yahoo prices are used and
  you get a "System problem" message.
- **GitHub account + this repository + the branch** - never delete them. **Telegram bot** - don't delete it.
- The API key/secret live only in GitHub → Settings → Secrets. Never paste them anywhere else.

## When to get help (Claude or any developer)
- "System problem" every day for a week, or no messages at all for 2 market days.
- Zerodha / Yahoo / GitHub announce big changes to their services.
- You want new features. Point them to `DECISIONS.md` (every decision and test result) and this guide.

Research, not investment advice. Past test results do not guarantee future profits.
