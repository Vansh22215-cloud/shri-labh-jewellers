# DECISIONS.md - every default chosen, and why

Written 2026-11-02 **before** the first backtest was run. Nothing here was changed after seeing results
unless an entry says so explicitly (with date and reason).

## Where it runs
- **D1.** The system is built in this folder and runs on your Windows PC (Python + Windows Task Scheduler).
  The first build, data download, backtest and report were produced in Claude's cloud workspace; your PC
  re-downloads the same free data during setup (nothing paid, no logins).
- **D2.** No broker connection at all. The system never sees your Zerodha credentials and cannot place orders.

## Data sources (all free; terms checked 2026-11-02)
- **D3. Prices: Yahoo Finance via `yfinance`.** Free for personal use. One batched download per night, cached
  locally, so each price is fetched once. Split/bonus-adjusted O/H/L/C; we also apply the dividend factor
  (Adj Close / Close) so returns include dividends.
- **D4. Official cross-check: NSE bhavcopy files** from `nsearchives.nseindia.com` (public static downloads).
  Fetched one file at a time with pauses and cached forever. Used to (a) build the point-in-time universe,
  (b) verify Yahoo prices. A stock whose Yahoo price disagrees with NSE's official close by >2% on >10% of
  checked days, or by >1% in the last 3 checks, or with an unexplained one-day jump of >45% / <-45%, is
  **quarantined** (excluded), not "fixed".
- **D5. Screener.in is NOT used.** Its terms allow only "personal, non-commercial transitory viewing" and
  forbid copying. NSE's JSON API (corporate actions, pledge data) blocks automated access, so it is not used.
- **D6. Fundamentals: Yahoo (annual statements, ~4-5 years) via `yfinance`.** Point-in-time rule: an annual
  number is "known" only 60 days after the period end (SEBI LODR deadline for annual results). This history
  is restated, not as-first-published, and too short for a 10-year test, so **fundamentals are a live safety
  screen only** (can remove a tip, never add one) and are not part of the validated strategy.
- **D7. Promoter pledge:** no free source we may automate. The report says so and tells you to check it on
  Zerodha (Kite shows shareholding) before buying. Promoter holding is approximated by Yahoo's insider %.
- **D8. Results dates:** Yahoo earnings calendar (past + next). In the backtest the actual historical dates
  are used, which is mildly optimistic (in real life dates are announced only days ahead).
- **D9. Liquid fund for idle cash:** Nippon India Liquid Fund - Direct - Growth NAV from mfapi.in (AMFI data).
- **D10. Bulk/block deals:** NSE's daily public CSVs, kept as a local history for context in stock notes.

## Universe
- **D11.** Monthly, point-in-time: top 500 NSE EQ-series stocks by **median daily traded value over the previous
  ~4 months**, using only data before that month. Excluded: traded on <80% of sampled days, first seen <365
  days earlier (new listings), median price < Rs 50, BE/BZ (surveillance) series, and < 250 days of price
  history. Because the list includes stocks later delisted, survivorship bias is reduced - but Yahoo has no
  prices for delisted/renamed stocks, so they drop out of the test. The validation report quantifies this.
- **D12.** Sector strength uses the current Nifty 500 industry labels (small look-ahead; stocks without a
  label get a neutral sector score).

## Strategy v1 (fixed from standard textbook values, not tuned)
- **D13. Market filter:** new trades only when Nifty 50 > its 200-day average AND >= 40% of the universe is
  above its 50-day average.
- **D14. Stock must be:** above a rising 200-day average and its 50-day average above the 200-day; not more
  than 25% above its 50-day average; in the top 30% by 6-month relative strength vs Nifty (skipping the last
  5 days).
- **D15. Entry timing (either):** *Breakout* = close at a new 50-day closing high, volume > 1.5x its 50-day
  average, close in the upper half of the day's range. *Pullback* = low touched within 3% of the 20-day EMA in
  the last 5 days, then a close above the EMA and above the previous day's high.
- **D16. Score (0-100) to rank candidates:** 35% 6-month RS, 20% 3-month RS, 15% sector RS, 20% trend quality
  (consistency above 50-day avg + low volatility), 10% liquidity.
- **D17. Valuation sanity** (live screen only): removes a tip if P/E > 120, loss-making, negative equity,
  negative operating cash flow, or debt/equity > 2.
- **D18. Trade plan:** buy at next open. Do NOT buy if the open is above signal close + 0.5 x ATR(14) or at/below
  the stop. Stop = signal close - 2 x ATR(14). Target 1 = entry + 1.5R (sell half, move stop to entry).
  Target 2 = entry + 3R. Time exit after 25 trading days.
- **D19. Risk engine:** 1% of capital risked per trade (Rs 450 on Rs 45,000); max 25% of capital per position;
  max 4 open positions; if equity falls 10% below its peak, no new trades for 20 trading days; weak-market filter
  (D13).
- **D20. Results-date rule:** v1 FLAGS results due within 5 trading days in the risks list but does not exclude
  them. Whether excluding them helps is tested as proposal P1 (IMPROVEMENTS.md), registered before testing.

## Backtest realism
- **D21. Costs:** Zerodha delivery charges from zerodha.com/charges (checked 2026-11-02): brokerage 0, STT 0.1%
  buy and sell, NSE transaction 0.00307%, SEBI Rs 10/crore, GST 18% on (brokerage+transaction+SEBI), stamp duty
  0.015% on buys, DP Rs 15.34 per scrip per sell day (each partial exit pays it again).
- **D22. Slippage:** 0.15% per side (conservative for top-500 stocks with orders < Rs 15k).
- **D23. Fills:** next-day open entries; if a day opens below the stop we exit at that open (gap-through-stop);
  if stop and target are both within one day's range we assume the stop hit first.
- **D24. Tax** (short-term capital gains) is not modelled; it would reduce both strategy and benchmark gains
  (more for the strategy, which realises gains more often).

## Validation gate (fixed before testing; never loosened)
- **D25.** Walk-forward periods: calendar years 2013 ... 2024 plus Jan-Apr 2025, each starting fresh with
  Rs 45,000. Holdout: 2025-05-01 to latest data - never used to choose anything.
- **D26.** Benchmarks: NIFTYBEES buy-and-hold (after buy costs); same daily exposure in NIFTYBEES with idle cash
  in the liquid fund; liquid fund alone. The strategy's own idle cash also earns the liquid-fund return.
- **D27. Pass requires ALL:** beats NIFTYBEES in >= 60% of walk-forward periods (+2 percentage points per extra
  variant ever tried, max 80%); holdout beats NIFTYBEES and the liquid fund; max drawdown <= 20% (walk-forward)
  and <= 15% (holdout); >= 100 walk-forward trades; t-stat of monthly excess return vs NIFTYBEES >=
  max(1.0, sqrt(2 ln N)), N = variants tried.
- **D28.** Every distinct parameter set ever backtested is recorded in `validation/variants_tried.json`; the
  count raises the bar (D27).
- **D29. Holdout rotation:** when the holdout exceeds 30 months, its start moves forward 12 months (older part
  joins the walk-forward). Because every proposal sees a holdout pass/fail, promotions are limited to one per week
  and all are logged.

## Operations
- **D30.** Paper mode by default for 8 weeks from 2026-11-02. Tips are journaled and tracked automatically with
  the exact backtest rules; the report compares paper results with the backtest.
- **D31.** When tips are blocked (gate failed, weak market, kill switch...), the would-be picks are still tracked
  silently as "shadow" entries so the system keeps measuring itself. They are never shown as tips.
- **D32.** Nightly job: weekdays 6:30 pm, Windows Task Scheduler with "run as soon as possible after a missed
  start" (catch-up if the PC was off). Weekly improvement: Saturdays 10:00 am.
- **D33.** Claude review (`claude -p`) is OFF by default: it needs Claude Code installed and signed in, and uses
  your Pro plan quota. When on: max 6 stocks/night, stops for the night at the first usage-limit error. It can
  only comment; verdicts are logged so the weekly job can test whether it ever helped.
- **D34.** Auto-rollback: after >= 20 closed paper trades of the live version, if average R is negative and more
  than 2 standard errors below the backtest's, or paper drawdown exceeds 15%, roll back to the previous version
  (or pause tips if there is none).
- **D35.** Kill switch and all user settings live in `settings.yaml` (editable in Notepad). An unreadable
  settings file forces the kill switch ON.
- **D36. Paid services:** none used. None proposed at this stage.

## Strategy SEARCH (added 2026-11-02, written BEFORE the search was run)
You asked the system not to be limited to one strategy. So it now searches a large space instead of
testing a single idea.
- **D37. Search space:** 10 strategy families (see `swing/families.py`: trend pullback/breakout, Donchian
  breakout 20/55, 52-week high, mean reversion RSI(2), momentum leaders, volatility squeeze, moving-average
  cross, volume surge, NR7, low-volatility momentum) x stop-loss (1.5/2/3 ATR) x exit style (targets 1.5R/3R,
  wide targets 2R/4R, chandelier trailing stop 3 ATR; mean reversion: exit on bounce above 5-day average) x
  maximum hold (10/25/50 days; mean reversion 5/10) x market filter on/off. ~550 variants. Every variant is
  recorded in `validation/variants_tried.json`.
- **D38. The danger:** among hundreds of variants some will look excellent by pure luck. Picking the best
  backtest and calling it "validated" would be self-deception. So the raw best variant is reported only as
  "cherry-picked, not evidence".
- **D39. Honest selection (walk-forward search):** at the start of each year from 2016, the system picks the
  variant with the highest Sharpe ratio (monthly returns) over the PREVIOUS 36 months, among variants with
  >= 30 trades in that window. That pick is then traded for the year. Only these out-of-sample years count.
  The gate (D27) is applied to this chain; "variants tried" for the haircut = number of *search procedures*
  tried (`validation/search_procedures.json`), because selection happens inside the walk-forward. The raw
  variant count is still reported, and a second, informational check asks whether the cherry-picked best
  variant survives a haircut for ALL raw variants (t >= sqrt(2 ln N_raw)).
- **D40. Holdout:** the variant chosen with the 36 months before the holdout start is run once, fresh, on the
  holdout. Must beat NIFTYBEES and the liquid fund, with drawdown <= 15%.
- **D41. Simplification (stated):** in the chain, each year's return comes from that variant's continuous
  backtest (positions carried in from the previous year), not a fresh restart.
- **D42. If the search ever passes:** the variant selected on the latest 36 months becomes the next live
  version (vN). The weekly job re-runs the search when the last one is > 30 days old.

## Short-term and intraday trading (added 2026-11-03 at your request, written BEFORE these searches)
You asked for short trades (hours to 2-3 days, exit at target) and allowed the rules to change.
- **D43. Short-term daily search** (`search.short_space`): holds of 2/3/5 days, stops 1/1.5/2 ATR, quick
  targets 1R/2R, 1.5R/3R or a 2-ATR trailing stop, and a second sizing option of **2% risk per trade with up
  to 6 open trades** (rule change from D19). 10 patterns incl. 4 new short-term ones (inside-day breakout,
  gap-and-go, strong close, 3-day pullback). 1,080 variants. Same walk-forward selection and gate as D39-D40.
- **D44. Intraday data:** Yahoo hourly bars (free, ~730 days; we keep older bars cached so history grows).
  Top 150 liquid stocks of the current universe (small survivorship bias over 3 years).
- **D45. Intraday rules:** see `swing/intraday.py` docstring - entry at the next bar open after a closed
  signal bar, stop-first when ambiguous, square-off at the 15:15 bar open, 1% risk, max 50% of capital per
  trade, NO leverage (MIS leverage magnifies losses; capital protection first), max 1-2 trades/day.
- **D46. Intraday costs:** Zerodha MIS charges (zerodha.com/charges) + slippage **0.05% per side** (typical
  bid-ask spread of top-150 NSE stocks is 0.02-0.05%). Because this is an estimate, a strategy must ALSO stay
  above the liquid fund with **double slippage (0.10%)** to pass.
- **D47. Intraday walk-forward:** calendar quarters; each quarter's strategy is picked by best Sharpe over the
  previous 6 months (>= 30 trades). Holdout: 2026-07-01 onward, never used for choices. Benchmarks: NIFTYBEES
  and the liquid fund (idle intraday capital earns nothing in the backtest).
- **D48. Kite Connect:** not used. It is paid (about Rs 500/month) and the free data is enough for this
  research; orders are placed by you. Revisit only if a strategy passes and needs minute-level data to confirm.
  Never share API keys in chat.

## Telegram tip checker (added 2026-11-03 at your request)
- **D49.** Forward any tip to your bot; it parses stock / entry / stop / targets / intraday-or-swing, checks the
  live price, and judges the tip by the stock's OWN last 5 years: how often the target distance was reached
  before the stop distance within the holding window (1 day intraday, 2 BTST, 10 swing, 40 positional;
  stop-first if both on one day), versus the win rate needed to break even after Zerodha charges + slippage.
- **D50. Verdicts:** AVOID if the odds are > 5 points below break-even, the stock is illiquid (< Rs 5 crore a
  day - classic pump-and-dump), in a surveillance series, the entry is > 10% from today's price, or the tip has
  already failed. RISKY if any caution flag (no stop-loss, odds within 5 points of break-even, tight/wide stop,
  below 200-day average, weak market, results within 7 days, price already ran > 1.5%). Otherwise GOOD.
  These base rates are unconditional (they ignore the tip-giver's chart reasoning), so they are a reality check,
  not a prediction.
- **D51. Learning:** every checked tip is stored with its source (channel/person) and its real outcome is
  tracked; the report shows hit rates per source and per verdict. After 30 resolved tips the weekly job checks
  that GOOD tips beat AVOID tips and flags the checker for review if not. Only the owner's chat is answered.

## Aggressive mode (added 2026-11-03 - the owner's explicit choice)
You said you want daily tips even if somewhat risky, and do not want the index fund. It is your money, so:
- **D52.** `tips_mode: aggressive` in settings.yaml. When no strategy passes the gate, the system still gives
  tips from the walk-forward search's CURRENT pick (chosen by the fixed rule: best Sharpe over the last 36
  months), clearly labelled **NOT validated**. Today that is a1 = 20/50-day moving-average crossover above the
  200-day average, stop 3 ATR, targets 2R/4R, max 25 days, no market filter.
- **D53. Expectations (backtest, after costs, idle cash in a liquid fund):** 2013-Apr 2025 about 9% a year,
  worst fall about 10%, ~516 trades, ~50% winners; untouched holdout May 2025-Nov 2026 +5.5% (NIFTYBEES -1%).
  It earned LESS than NIFTYBEES over the full period. These are estimates, not promises.
- **D54. Risk 1% per trade, not 2%.** Tested both (2 more variants counted): 2% risk earned LESS (8.4% vs
  9.0% a year, 2013-Apr 2025) with a much worse fall (-26% vs -10%). More risk did not mean more money.
- **D55. Brakes:** max 4 positions, max 25% of capital each, a 4-week pause after a 10% fall, and a HARD STOP
  when aggressive tips have lost 20% of capital in total (only you can restart it). Kill switch still works.
  Mode set to live (paper_weeks 0) at your request; every tip and its outcome is still journaled. The weekly
  job moves aggressive mode to the new search pick each month (a2, a3, ...), logged in CHANGELOG.md.
- **D56.** Idle cash: the backtest assumes money not in a trade sits in a liquid fund (LIQUIDBEES or a liquid
  mutual fund - this is cash parking, not index investing). If it sits idle in the trading account instead,
  expect about 4-5% a year less.

## Hourly scan and risk score (added 2026-11-03 at your request)
- **D57. Risk score 1-10** (`swing/risk_score.py`): +3 if the strategy is not validated (+1 if it is),
  +0-3 volatility (daily range), +0-2 liquidity, +1 not in a long-term uptrend, +1 weak market, +2 results within
  7 days, +1 stretched > 15% above the 50-day average. A checklist, not a probability.
- **D58. Hourly scan** 10:20-15:20 IST on weekdays (the scheduler's minimum is hourly; every 10 minutes is not
  possible and would use up the Claude plan). Live 5-minute data for the top ~500 company shares (ETFs/funds
  excluded) feeds the SAME strategy code on a provisional "today so far" bar. Signals are provisional until the
  close; the 6:40 pm run confirms them and the plan is to buy at the next open inside the buy zone (as tested).
  Your trades are checked live for stop/target hits.
- **D59. Kite Connect: declined.** Paid, needs a daily login with your Zerodha password (which this system must
  never hold), and free 5-minute data is enough for hourly scans.

## Continuous research (added 2026-11-03 at your request)
- **D60. Daily research session** (weekdays 20:17 IST): tests ONE pre-registered idea from IMPROVEMENTS.md
  against the strategy currently giving tips. Aggressive line (aN): promote only if it beats the base in most
  walk-forward years, has a higher walk-forward CAGR, and its worst fall is not more than 2 points worse.
  Validated line (vN): must also pass the full gate. The holdout is never used to decide. Every idea counts as a
  tried variant. New ideas must be written into IMPROVEMENTS.md (with reason and date) BEFORE they are tested.
- **D61. Market dynamics:** each backtest trade is tagged with the market regime on its signal day (Nifty trend,
  VIX mood, breadth). Reports show today's regime and how the strategy did historically in similar markets.
  Samples per regime are small (30-300 trades), so this is context, not a trading rule; any rule derived from
  these tables would be "data already seen" and must be pre-registered and tested like any other idea.
- **D62. Bug fixed 2026-11-03:** ETFs/funds (e.g. LIQUIDBEES) were inside the backtest stock universe; one Yahoo
  glitch in a liquid ETF produced an -84R trade. 35 ETFs/funds are now excluded; all validations and searches
  were re-run.

## Deep upgrade session (added 2026-11-03 at your request)
- **D63.** Every 2 days (21:47 IST) a deep session works through ROADMAP.md: builds one new capability (data,
  strategy family, risk, ensemble, honest walk-forward machine learning, live-learning), with unit tests, then
  validates it with the same rules (pre-registered proposal or search space, walk-forward, untouched holdout,
  costs, variant count). Anything that does not help is kept as code but not used. Results go to CHANGELOG.md,
  ROADMAP.md and Telegram. Scheduled sessions use the owner's Claude plan; when its limit is reached a session
  may be skipped until the limit resets.

## Mission and Kite Connect (2026-11-03)
- **D64. Mission (owner):** give the best trades one can find every day, combining the best-known methods
  (Minervini, O'Neil, Weinstein, Darvas, academic momentum, earnings drift, Connors, sector rotation, quality),
  each tested on NSE data, and a meta-system that picks the currently strongest ones using only past data.
  "Best" always means "best by honest out-of-sample evidence", never "guaranteed".
- **D65. Kite Connect (Rs 500/month, owner's decision to buy):** useful for minute-level history and reliable live
  quotes. Cost note: Rs 6,000/year is ~13% of the Rs 45,000 capital and more than the strategy's expected yearly
  profit, so it must earn its cost through better research. Security: API key/secret stored only in
  my_secrets.yaml (never on GitHub); the daily access token is obtained by the owner logging in on Kite's own page;
  the system never asks for the Zerodha password/TOTP and NEVER calls any order API. Access tokens expire daily.

## Selection-rule fix (written 2026-11-03 BEFORE running the combined search)
- **D66. Flaw found:** walk-forward selection used the Sharpe ratio of equity that INCLUDES liquid-fund interest on
  idle cash, which rewards strategies that barely trade (smooth cash-like curves; e.g. the library pick PEAD made
  < 1 trade a month and its trades lost slightly in the holdout). New procedure "wf-search-combined-v1": pool ALL
  swing + library variants (684) and pick each year the variant with the highest Sharpe of monthly returns IN
  EXCESS OF THE LIQUID FUND over the previous 36 months (>= 30 trades). Everything else as D39-D40. This counts
  as one more search procedure (stricter gate). If its gate fails, aggressive mode follows this procedure's
  current pick anyway (owner's choice, D52), because it measures what the TRADES add over parking cash.
- **D67. Abnormal-market detector & daily loss limit (2026-11-03):** no new trades after a day when India VIX jumps
  > 20% or is above 28, when Nifty moves more than 2.5%, or when realised losses on tracked tips reach 2% of
  capital that day. Thresholds are standard risk-desk defaults, not tuned.
- **D68. Smart money (2026-11-03, owner's request):** evening message lists bulk/block deals where a fund or well-known
  investor was a NET buyer of >= Rs 5 crore in a liquid top-500 stock that is in an uptrend (HFT/prop/broker names
  excluded). Free deal history starts now, so it is labelled an untested idea; every flagged deal is logged in
  journal/smart_money.csv and will be tested as a strategy once ~6 months of deals exist.
- **D69. Learning from the owner's tip channels:** the forwarded-tip journal scores every channel; once a channel
  has >= 30 resolved calls with a target-hit rate clearly above what its stops imply (break-even after costs) its
  checked calls can be added to the daily list (to be built when the data exists).
