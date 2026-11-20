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

## NSE terms of use (found 2026-11-03 - correcting D4/D10)
- **D70.** NSE's website Terms of Use prohibit "systematic or automated data collection ... including scraping, data
  mining, data extraction and data harvesting" on the website (nseindia.com terms of use). D4 wrongly treated the
  archive files as freely automatable; that was not checked properly at the start. Actions taken: large
  historical back-fills from NSE (participant OI, F&O) stopped; NO new NSE website/API collectors are built (FII/DII
  cash API, shareholding, announcements, insider trades were found reachable but are not used). The owner decides
  how to continue (see the conversation of 2026-11-03): licensed data via a broker API (Kite Connect, Rs 500/month),
  NSE's paid data products, or accept the terms risk for low-volume personal downloads.

## S12 meta-system (written 2026-11-03 BEFORE computing it)
- **D71.** "Best of all" = an ENSEMBLE, not a single pick: each January choose the 3 variants with the highest
  Sharpe of excess-over-liquid-fund monthly returns over the previous 36 months (>= 30 trades), each from a
  DIFFERENT family, and give each one third of the capital for that year. Evaluated from the saved monthly-return
  matrix of the combined search (validation/search_R_combined.csv.gz) against NIFTYBEES per year, with the same gate
  (counts as one more search procedure). Simplification: per-strategy returns are taken as if run on full capital
  (fixed DP charges on smaller positions are under-counted, which flatters the ensemble slightly).
- **D72. S12 result (2026-11-03):** the 3-family ensemble, honest walk-forward 2016-2025: 7.75%/yr, worst fall -8.4%,
  beat NIFTYBEES in 1/10 years, t -1.47 -> gate FAILED. But compared procedure-to-procedure on the same walk-forward
  years it beats the single-pick procedure that currently feeds aggressive mode (6.49%/yr, worst fall -22.1%).
  Decision: aggressive mode will move to the ensemble (today: ma_cross S385 + volume_surge S444 + nr7 S489, one third
  of the risk budget each) once the live multi-strategy plumbing is built and tested (next ROADMAP step).

## Running without Claude (2026-11-03, the owner's Claude plan ends)
- **D73.** All daily jobs run on GitHub Actions (free for public repositories): hourly scan, evening trades,
  research (pre-registered ideas only; no NEW ideas without Claude), weekly self-check with monthly searches, and an
  hourly Telegram bot poll. Data is kept between runs in the Actions cache; the committed universe list lets a fresh
  runner start with recent data only. The repository is PUBLIC, so personal files (your trades, forwarded tips,
  daily reports) are kept out of git: they live in the cache and are backed up as 90-day private run artifacts.
  NSE data use stays at option B (small daily downloads) until the owner decides otherwise (D70).
- **D74. Self-improvement without Claude (2026-11-03):** an idea factory (swing/idea_factory.py) writes 2 new dated
  ideas from a fixed menu of sensible single changes whenever fewer than 3 are queued; the evening research run tests
  one per weekday with the normal promotion rules. Telegram now reports every job (hourly pulse or actions, evening
  trades + report file + any system problems, research result, weekly self-check), at the owner's request.
- **D75. Pattern library + compounding search (2026-11-03):** 27 well-known patterns/indicators (swing/patterns.py)
  join the families; the idea factory queues ~900 candidates (every family with the current exits, every rule change,
  and family x rule combinations), tested 2 per weekday evening and up to 8 on Saturdays. Anti-fluke rule: an idea
  must beat the current strategy by at least 0.25 x sqrt(ln N) CAGR points (N = ideas tested so far) and, after 50
  ideas, in at least 60% of walk-forward years, with a worst fall no more than 2 points deeper.
- **D76. Company of the day (2026-11-03):** all ~2,391 NSE EQ companies; ~120 statements refreshed per night
  (Yahoo, free), scored 0-100 (quality 25, growth 20, financial health 20, cash flow 15, valuation 10, Piotroski 10;
  -8 per red flag). Pick (changed 2026-11-03 at the owner's request): simply the best score, no trading-volume or price limits;
  red flags are shown as red flags (and cost points); not shown in the last 60 days. Thin trading is marked on the card. Research pick, not a tip; every pick is logged (journal/company_picks.csv) to measure it.
- **D77. Data sources for company analysis:** Yahoo statements, with gaps filled from Yahoo's company-summary
  figures and re-fetched within days when its profile service failed. Bloomberg/Refinitiv/Capitaline are paid
  (thousands of dollars a year); Screener, Moneycontrol, Tickertape and NSE/BSE websites forbid automated copying in
  their terms, so they are not scraped. A licensed source can be added later if the owner decides to pay for one.

## Owner's pattern library (2026-11-04)
- **D78.** library/market_pattern_library (52 chart, 69 candlestick, 176 indicators) is the source of truth, loaded by
  swing/catalog.py. TA-Lib (installed) provides the canonical candle and indicator functions; chart patterns use a
  swing-pivot engine with right-side confirmation (no back-dating). library/IMPLEMENTATION_AUDIT.md lists every item's
  status: candles 44 implemented as entries + 19 bearish detector-only; chart 22 implemented, 15 bearish
  (not applicable to a long-only system), 15 planned (harmonic/Elliott/Wyckoff phases need more pivot geometry);
  indicators 164 implemented, 4 blocked by data (tick/intraday), 8 planned. All new entry rules joined the idea
  factory queue (~108 entry ideas + ~1,800 combinations); nothing is used for tips unless it passes the tests.

## D79 (2026-11-03) Pattern library v2 (791 records) replaces v1
- The owner's v2 library is a superset of v1 (every v1 id kept), adding market-structure/liquidity events (85) and
  quant research features (104). Loaded as five catalogues keyed by type; 1,212 aliases resolved; 0 validation problems.
- Built now (rule version cat-v2): 30 non-TA-Lib bullish candle rules (adaptive body/ATR thresholds), 24 more chart
  detectors (Darvas, VCP, flat base, NR4/NR7, turtle soup, 3-bar play, gap-and-go, symmetrical triangle, ...),
  21 market-structure events (BOS, CHoCH, MSS, liquidity sweeps, FVG, order block, displacement, weekly/monthly
  open reclaim, SAR/chandelier flips, ...), 110 more indicators and 53 quant features. Every new family/indicator has
  a test that its value on a past day does not change when later data is added (no look-ahead).
- Four v2 names that are the same rule as another detector are merged (not counted as separate tests).
- Audit: 492 built (incl. 20 detector-only), 97 bearish/not applicable (long-only), 62 need data we do not have
  (options IV history, order book, tick, volume profile, futures basis), 120 still to build (mostly harmonic/Elliott/
  Wyckoff phases and intraday-session events). Idea queue grows to 182 entry ideas + 3,094 combinations.
- A detector is not an edge: nothing reaches the tips unless it beats the live rule in the walk-forward test.

## D80 (2026-11-03) GitHub runs everything; Claude's scheduled sessions switched off
- The first GitHub nightly ran and sent Telegram, but its save step was rejected (pull --rebase with unstaged files),
  so results were not kept. Fix in branch code (no change to main needed): swing/ci_save.py commits the fixed
  non-personal list, rebases with --autostash (this run's results win conflicts), pushes with 5 retries; every
  scheduled script calls it at the end. Tested against a throwaway remote with a concurrent commit.
- Research on GitHub now tests as many queued ideas as fit in 120 minutes (was 2 per day) and keeps 80 ideas
  pre-written for the next run, so self-improvement no longer depends on Claude.
- Claude's hourly/daily improvement sessions are disabled (owner: "no need of Claude"). Code changes to the system
  itself (new detectors) now only happen if the owner opens a new Claude session; idea testing, strategy searches,
  rollback, company of the day and all Telegram messages continue on GitHub for free.

## D81 (2026-11-04) Lifelong data store; personal files out of public reach
- The repository is PUBLIC (Actions logs and artifacts are readable by anyone). Personal files moved to
  data/private/ (only in the private Actions cache), so the old artifact step uploads nothing; on GitHub, scripts
  print only message lengths, never trade/position contents. Backups go to the owner's own Telegram instead
  (weekly: trades + forwarded tips; monthly: the data archive) and are restored by forwarding them to the bot.
- swing/archive.py keeps everything collected, append-only, forever (data/archive in the cache - market data is
  not redistributed in the public repo): daily bars of every stock (so stocks Yahoo later drops stay in the
  backtests = less survivorship bias), hourly bars beyond Yahoo's ~730 days, 5-minute bars beyond Yahoo's ~60 days,
  news beyond the 60-day store, every statement year ever seen (Yahoo shows ~4). The engine, intraday research and
  company analysis read it. Yahoo full re-downloads can no longer shorten a stock's history.
- Walk-forward periods already extend every year and the holdout rotates yearly, so tests use all data to date.

## D82 (2026-11-04) Library v2 completed (cat-v3): nothing left unbuilt
- 603 items implemented, 28 detector-only, 98 bearish (not applicable to a long-only system), 0 not built.
- New: ATR-zigzag swing engine (confirmed swings only) with 10 harmonic patterns, three drives, 6 Elliott
  structures, 3 pitchforks, diamond, megaphone, Fibonacci cluster/time zone; Wyckoff phases (accumulation, SOS,
  LPS, backup to edge, secondary test, creek), weekly pipe/horn bottoms, point & figure and renko breakouts,
  exhaustion gap/climax, Gann square-of-nine, IPO base; 16 more market-structure entries; remaining indicators.
- 34 items are 'implemented_collecting_data': intraday market-profile rules (need ~250 days of stored 5-minute
  bars - they join the idea tests by themselves when reached) and option IV rank/skew/term structure (IV is now
  computed from the F&O file each evening). 28 items are 'ready_waiting_for_feed': tick/order-book/auction
  metrics in swing/feeds.py start working the day such files are placed in data/feeds/ (e.g. via Kite Connect).
- Breadth (A/D, McClellan, TRIN, high-low index), futures basis/OI/max pain/PCR and execution estimates are now
  computed from data already collected.
- Idea factory: 239 entry ideas + 4,063 combinations. Every no-look-ahead test passes (349 tests).

## D83 (2026-11-04) Reliable start times: free external timer
- GitHub's own scheduler dropped most runs. The owner set up cron-job.org (free) to start the workflow
  (task "bot" = always-on run, swing/daemon.py) daily at 09:50, 14:50, 19:50 and 00:50 IST using a fine-grained
  GitHub token limited to Actions on this one repository (held only by cron-job.org, never in the repo or chats).
  Each run lasts ~5h15m; a start that arrives while one is running waits and continues after it, so scans,
  evening trades, research and the weekly check run on time. GitHub's own schedule stays as a backup.
- If the token expires, runs stop: the owner renews it (same steps) before the expiry date.

## D84 (2026-11-05) Nothing may stop silently: self-restarting runs, retried and logged messages
Problem found: on 4 Nov the always-on run did the evening job, but no run started after 10:30 am on 5 Nov (GitHub
dropped its schedule and no cron-job.org start arrived after the test), and Telegram send results were never
written to the log, so a missing message (company of the day) could not be traced.
- Each GitHub run now starts the next one when it ends (scripts/keep_alive.py, uses only the run's own
  short-lived GITHUB_TOKEN; needs `actions: write` in the workflow). It skips if another run is already waiting and
  pauses itself after 4 restarts in an hour (crash-loop guard, Telegram warning). cron-job.org stays as a backup.
  Free: public repositories have unlimited standard GitHub Actions minutes. Switch off with `keep_alive: false`.
- Telegram: up to 4 tries with backoff, rate-limit aware, splits on line breaks with balanced HTML tags, falls back
  to plain text if formatting is rejected, and logs "Telegram <name> sent/FAILED" (length only - public log).
- Company of the day is its own job (daemon "company", after the trades message, or by 19:30 even if the evening
  job failed), retried up to 3 times if Telegram does not take it; a retry re-sends the same pick. Picks without a
  live price are skipped.
- Evening message gets a "System: n of 6 market scans ran today" line, so any gap is visible the same day.
- In aggressive mode the no-tips headline names the real blocker (was "strategy not validated").
- 5-minute store: the intraday list is rebuilt from the liquidity history when its file is missing (was failing on GitHub).
- Removed the public artifact upload step (backups go to the owner's Telegram, D81).
- (5 Nov evening) Found: the nightly self-tests always failed on GitHub because the test run inherited the job's
  own setting (SWING_CLAIMED=nightly), which changes one daemon test - so the evening blocked all tips. Fixed: tests
  run in a clean environment (conftest + run_tests strips SWING_/TELEGRAM_/GH_ variables) and a failure now names
  the failing test in the log.

## D85 (2026-11-06) Forwarded index / forex / gold / crypto views and setups are understood and tracked
Owner forwarded a Nifty view ("trend continuation on 60 min, weakness only below 24290") and got "could not find an
NSE stock". Now (swing/market_views.py):
- Understands indices (Nifty, Bank Nifty, Fin Nifty, Midcap, Sensex), forex pairs (any of EUR GBP USD JPY AUD NZD
  CAD CHF INR), gold, silver, crude, Bitcoin, Ethereum; SETUPS (entry/SL/TP) and VIEWS with a "wrong if" level.
- A view with no target is tested as a 1:1 move (as far the other way as the "wrong if" level) - the fairest yes/no
  test; time allowed follows the chart timeframe (60 min -> ~3 days, daily -> 2 weeks, ...).
- Reply: live price, distance to the level, hourly/daily trend, base rate from ~2 years of hourly bars (same-bar tie
  = loss), break-even rate, the channel's track record so far.
- Tracking every 30 minutes by the always-on run on hourly bars; the owner gets a Telegram message when a call is
  right, wrong, expired, or (setups) reaches its entry. Stock tips now also get a "right/wrong" message.
- Messages the old checker could not read in the last 7 days are re-read once, judged at the price of the hour
  they were forwarded.
- Forex replies carry the legal note: in India only rupee pairs on NSE/BSE are legal for residents (RBI alert list).
- Pictures are not read (no free OCR on GitHub); the caption text is used.

## D86 (2026-11-06) The bot reads forwarded chart pictures (free)
- Free OCR (rapidocr-onnxruntime, runs on GitHub's computer, no key, no cost) reads the words on the picture:
  title/symbol, timeframe, written levels, entry/SL/TP boxes and pattern names (head and shoulders, double
  bottom, flag, wedge, triangle, cup and handle, order block, FVG, BOS/CHoCH, support/resistance ...).
- The price scale on the right is fitted (robust line through the axis numbers, misreads dropped), so long
  horizontal lines drawn on the chart are converted to prices. Tested on the owner's (blurry, re-screenshotted)
  Dark Horse chart: lines read at 23,961 / 24,313 / 24,458 vs labels 23,947 / 24,296 / 24,442 (within ~0.07%).
- No name readable: the instrument is guessed from the price scale only if exactly one index/commodity/crypto/major
  pair trades inside it (said in the reply). No stop written: the nearest drawn line on the other side of the
  price is used as the "wrong if" level (said in the reply).
- Every tip/view reply (picture or text) also carries the system's OWN pattern check on real daily prices: which of
  the library's chart-pattern / market-structure entries fired in the last 3 days, and TA-Lib candles on the last
  bar - labelled as clues, not tested edges.
- The picture is held only in a temporary file and deleted at once (can be personal); only the words read are kept
  in the private journal.
- Optional paid upgrade NOT enabled (needs the owner's approval): an AI vision model could describe the drawing
  itself (trendlines, zones, arrows) at roughly Rs 1-3 per picture. Free OCR + real-price detectors cover the
  useful part; revisit only if many forwarded charts carry no readable text.

## D87 (2026-11-06) New program code reaches the running system within ~10 minutes
A forwarded chart picture was answered by the old code because the always-on run had started before the update
(runs keep the code they started with, up to ~5 hours). Now every 10 minutes the run compares the program files
(swing/, scripts/, requirements, strategies, settings) on the branch with the ones it started with; if they changed
it ends cleanly and keep_alive starts a fresh run with the new code (data-only commits do not trigger this). The
crash-loop guard only counts runs that ended within 8 minutes. At start each run self-checks the picture reader and
warns the owner on Telegram (once a day) if it cannot start.

## D88 (2026-11-06) One clear reply card for everything forwarded to the bot
Owner: replies must be structured, answer WHY, and be quick to understand. Every reply (stock tip, option tip,
index/forex/gold/crypto view or setup, chart picture) now uses swing/reply_card.py:
answer first in plain words (WORTH CONSIDERING / COIN FLIP / RISKY / SKIP IT / CAN'T JUDGE YET) -> what I read on
the picture -> what the tip says -> where the price is now -> why it could work -> why it could fail (deal-breakers
first) -> the odds as a bar ("48 out of 100, need 50") -> good to know -> the plan (hidden when the answer is skip)
-> bottom line (what to do and why; skipping costs nothing) -> the channel's scoreboard -> tracking note.
Hype words ("sure shot", "jackpot", "100%", "guaranteed" ...) are flagged with why they matter. Right/wrong alerts
say what they said, what happened (with time) and what it means. Fixed: option odds used per-share charges when
the lot size was unknown (showed "need 229%"); now an Rs 5 lakh lot is assumed.

## D89 (2026-11-06) Wrong-instrument bug fixed; picture title, timeframe and position tool are read
Owner forwarded a 15-minute XAU/USD chart with a long position tool; the bot analysed the NSE stock DOLLAR
(Rs 265) because the title "Gold Spot / U.S. Dollar" contains that word and stock symbols were tried first.
- An index/forex/gold/crypto name now beats a stock symbol that is only an ordinary word in the text (a stock still
  wins when clearly named: #SYMBOL or right after BUY/SELL).
- SAFETY RULE: if the chart's own price (title line "O.. H.. L.. C..") differs from the data for the chosen
  instrument by more than 3% (markets) / 5% (stocks), the bot answers CAN'T JUDGE YET and asks for the name - it
  never analyses an instrument that does not match the picture. Small gaps (futures vs spot, e.g. GC=F vs XAU/USD
  ~0.3%) are measured and the data is shifted to the chart's price; tracking uses the same shift.
- Title line also gives the timeframe (e.g. "· 15 · OANDA"); 15-minute-or-less charts are judged on real 15-minute
  bars (last 60 days) instead of hourly bars, and the reply names the data used.
- TradingView long/short position tool: the pale green (target) and red (stop) boxes are found (bridging candles
  drawn on top, solid candles ignored) and their edges priced through the axis -> entry, stop, target, side.
Rehearsal on a mock XAU/USD 15-min long chart: read entry 4,046.49 / stop 4,034.93 / target 4,057.44, 0.30% futures
gap adjusted, verdict RISKY (against the 15-min downtrend, stop only 0.3% away, 47 vs 51 needed).

## D90 (2026-11-06) Hourly message = TIPS UPDATE for every tip (Nifty pulse removed)
Owner: every hourly update must show each tip given so far and from now on; no Nifty line. The hourly scan now
sends (swing/tip_status.py): new signals / actions first, the owner's recorded trades, then every tip -
system tips (pending: vs buy zone; open: gain, Rs P&L on the tip quantity, distance to stop and target),
the hourly-scan "BUY ... tomorrow" signals (journal/scan_signals.csv) until the 6:40 pm list confirms or drops them,
and every forwarded tip (stocks and index/forex/gold/crypto calls) grouped by channel, with my verdict at the
time and "if you took it: ..." advice. Each line: icon, plain status (in profit / close to stop / target
reached today ...) and one "what to do". Finished forwarded calls are shown once on the day they finish.
- (6 Nov, after the 2:20 pm update) Owner: only a few tips were shown. The update listed only tips still being
  tracked with entry+stop+target. Now EVERY tip of the last 60 days is listed every hour: system tips (finished ones
  with their result), and every forwarded tip - tracked ones in full, finished ones with right/wrong, option tips /
  "skip" tips / tips without levels with the price change since forwarding, and unreadable messages so nothing
  disappears. The same tip forwarded twice shows once. Tips forwarded since the previous update are marked 🆕.

## D91 Clean-up: fully automated, no Claude, less noise (owner's choices)
- Daily research message: sent only when an idea is ADOPTED (tips change); otherwise counts go to the Saturday summary.
- Evening HTML report file: sent once a week with the Saturday summary instead of every evening.
- "Smart money" lines removed from the evening message (never tested).
- Saturday message is now: channel scorecards (all time) + every tip of the week (closed right/wrong, open in
  profit/loss, waiting, not tracked) + research count + how many hourly updates ran. Technical self-check notes stay
  in the log.
- Removed: windows/ laptop scripts, the paid Claude review option (review.py, claude_review settings, weekly Claude
  proposal step), the Claude-fed dashboard (dashboard_export.py, dashboard_page.html, the stale dashboard page),
  and the 8 switched-off Claude scheduled tasks. Kept: validated-mode fallback (v1) and feed-ready library items.
- cron-job.org: no longer needed (runs restart themselves); the owner deletes the job and its GitHub key.

## D92 (2026-11-11) Owner's "day-trader-skill" request, rebuilt for NSE without Claude
Source: github.com/Jakeschincariol/day-trader-skill (MIT, 11 US day-trading Claude skills). Rebuilt as automatic
GitHub + Telegram parts for NSE; nothing needs a Claude session.
- PAID, APPROVED BY THE OWNER: Kite Connect "Connect" app, Rs 500/month, for live quotes and historical candles
  (market data only). Why: faster, more reliable prices for the 1-minute alerts and intraday scanner than Yahoo.
  If the credit runs out or the owner does not log in, everything falls back to free Yahoo prices.
- NOT BUILT (owner's choice): order placement. SEBI/NSE require API orders to come from a registered static IP since
  April 2026; GitHub runners have changing IPs, and the owner declined the paid static-IP service. Instead every tip
  gets a risk-checked ORDER TICKET the owner places in the Kite app; "✅ I placed it" records the trade.
- Daily login: Zerodha requires a human login each day. 08:45 IST link -> Zerodha -> GitHub Pages kite-login.html ->
  Telegram /start kite_<request_token> -> token exchange with the secret (GitHub Secrets only). The access token is
  stored encrypted (Fernet, key from the API secret) in data/private and expires 06:00 IST.
- Risk check (owner: standard limits): 1% loss per trade, 2% daily loss stop, 3 new trades a day, 25% max order,
  stop required, free cash. On tickets and on /bought (warning).
- Instant alerts every minute 09:15-15:30 (entry / near stop / stop / target / 4% day move), once per event per day.
- Time Machine: 10,000 seeded bootstrap replays from the instrument's own bars, stop-first on ties; on every reply and
  evening tip. A simulation, not a prediction.
- NSE filings: important announcements, results calendar, insider/promoter trades (PIT feed; takeover-disclosure
  fallback), quarterly results summary; 09:00 morning brief and 15-minute filing alerts for followed stocks. Insider
  records are archived daily; "buy after promoter buying" will be tested once enough history exists (the free feed
  has no long history - it cannot be honestly back-tested today).
- Intraday PAPER trading only (owner's choice): ORB / flag / oversold bounce on completed 5-minute bars, sized to lose
  Rs 450 at the stop, closed 15:20, after charges. No tips; it may only tip after passing walk-forward tests and the
  owner's yes. 2-week paper review of tickets + intraday sent automatically.
- Not adapted: US Congress (Pelosi) tracker -> replaced by Indian insider/promoter disclosures; US pattern-day-trader
  rules (not applicable in India).

## D93 (2026-11-11) Pre-GitHub leftovers removed (owner: "your view" for all)
Removed: laptop bot loop (run_bot.py, bot.run_forever, bot.lock), saving the chat id to a local secrets file, the
5 manual fetch scripts and run_validation.py (the evening/Saturday jobs do these), ROADMAP.md (Claude-session plan;
history is in CHANGELOG/DECISIONS), and 4 of the 5 fixed GitHub schedules (the always-on run does every job; one
hourly schedule stays as a safety net). README and ARCHITECTURE rewritten for the GitHub-only setup. Kept:
first-time setup scripts (emergency rebuild), strategies a1/a2 (rollback history). Owner deletes the 2 public
backup artifacts of 3 Nov and the cron-job.org job + its GitHub key.

## D94 (2026-11-11) Live intraday tips (owner's choice), using Kite
Owner: "I want intraday too ... use the most of the new GitHub system". Changed from paper-only to LIVE tips:
- Scanner uses Kite's live 5-minute candles for the ~150 most-traded stocks (Yahoo fallback), every 5 minutes
  09:35-15:25, in a background thread so the bot never waits. Setups unchanged: ORB, bull flag, oversold bounce.
- A fresh trigger becomes a Telegram INTRADAY TIP (09:35-14:30 only, at most 2 a day, settings intraday_tips /
  intraday_max_tips) with Time Machine odds from the stock's last 30 days of 5-minute bars, plus a risk-checked MIS
  ticket (✅ records it, incl. side and product). Alerts follow it every minute; your MIS trades get a 15:10
  "square off now" reminder. Shorts are allowed only as intraday (MIS).
- FIXED RULE, written before any result: weekly (weekday after the close, needs that day's Kite login) the setups
  are tested on ~200 days of Kite 5-minute history for ~100 stocks with the live code, stop-first, 15:20 exit,
  Zerodha charges; a setup keeps sending tips only with >= 40 trades and profit after charges in BOTH halves.
  Until the first test, all three send, labelled "AGGRESSIVE - not yet validated". Paper tracking of all setups
  continues regardless. Earlier free-data search (D5x): intraday lost money after charges - so expect few or no
  setups to pass; the rule decides, not hope.

## D95 (2026-11-11) Live market engine; Telegram carries only tips, exit alerts, Kite login, company of the day
Owner: too many messages; wants F&O + intraday + normal trades found continuously across the whole market on
Kite data, back-tested, risk-evaluated, ranked x/10, in the owner's sample formats; no daily cap; risk by quality.
- Telegram gate (telegram.ALLOWED): trade tip, exit alert, kite login, company of the day. Everything else (hourly
  update, morning brief, filings, weekly summary, research notices, tickets, replies to forwarded tips) is log-only.
  Forwarded tips are still checked and tracked silently. Commands (/status, /kite, /bought ...) still answer.
- swing/live_engine.py runs 09:14-15:31 in a background thread: ~400 most-traded stocks + all F&O underlyings +
  Nifty/Bank Nifty; Kite 5-minute candles in a rotation (~2.5 requests/s), quotes every 30 s; intraday setups
  (ORB, flag, bounce, VWAP reclaim/rejection) on the bar that just closed; swing strategy (a3) on live prices every
  15 minutes; evening confirmed tips in the same format.
- Quality gates before ranking: with the daily trend, trigger-bar volume >= 1.5x, Time Machine target-first >=
  stop-first, setups that failed the Kite-history test need rank 9. RANK 1-10 = 20% back-tested edge, 20% Time
  Machine, 15% daily trend, 15% relative volume, 10% pattern-library confluence, 10% reward:risk, 10% liquidity
  (weights fixed, not fitted). Sent only at rank >= 8 (settings min_rank). Replay of 11 Nov, 60 stocks: 103 setups,
  13 passed the gates.
- Risk by rank: stocks 1% / 1.5% / 2% of capital (rank 6 / 7-8 / 9-10); options 2% / 3% / 5%.
- F&O = option BUYING only (owner): nearest expiry with >= 3 days left, slightly-ITM strike first, live premium,
  OI and spread <= 3% checks, targets = the stock's targets repriced with the option's implied volatility, stop-loss
  on the SPOT on 75-minute candle closes, lot size; skipped if the loss at the stop exceeds the rank's limit or one
  lot costs more than half the capital (so few stock options fit Rs 45,000 - honest consequence of the limits).
- Every tip is stored in journal/live_tips.csv; exit alerts once each: target 1..n, stop-loss, 3:15 pm intraday
  square-off. Option targets are not back-tested (expired contracts have no free history); the stock setup is.

## D96 (2026-11-12) Whole market, more setups, TradingView chart setups
- Universe = every NSE equity (EQ/BE, ~2,600) + F&O underlyings + indices. Live quotes for all every 30 s (full
  quotes incl. volume, 500 per request); 5-minute candles fetched 2-of-3 for the stocks moving NOW (largest % move,
  at the day's high/low, most traded) and 1-of-3 in a rotation through the rest. Hard floor: < Rs 1 crore traded
  today is not tipped (slippage / circuit risk).
- Setup library swing/setups.py (one code for live + weekly Kite-history test): ORB, FLAG, BOUNCE, VWAP, RANGE,
  EMAPB, INSIDE, GAPGO (+ swing a3). Every setup goes through the same gates, rank and weekly test.
- TradingView: no API lets an outside system draw on a user's chart (checked). Built instead: Pine Script indicator
  tradingview/swing_system_setups.pine with the SAME rules and gates (daily trend, 1.5x volume, 09:30-14:30),
  drawing green profit / red loss boxes, entry / SL / T1-T3 lines, EMA 9/21/50 and VWAP-based setups on 5-minute
  charts and the a3 swing setup on daily charts; corner table with the latest setup; alert conditions. The owner adds
  it once; it then works on every NSE chart and updates by itself. Every Telegram tip links straight to the chart.
  Differences are possible where TradingView's and Zerodha's candles differ slightly, and the indicator cannot apply
  the rank (Time Machine / back-test) - the Telegram tip is the ranked one.

## D97 (2026-11-12) Owner: intraday tips hit the stop within minutes - fixes and a learning loop
- BUG (main cause of "instant" SL alerts): exit checks used the stock's WHOLE-DAY high/low, so a dip from before the
  tip counted as a stop-loss hit (and an earlier high as a target hit). Now only candles that began after the tip,
  the live price and the running high/low since the tip count. Same fix for the owner's own trades bought today.
- Noise-proof stops: at least 1 x ATR(14, 5-min) from the entry (widened), at most 3 x (else skipped); targets reset
  to 1R/2R/3R. Same function in the live engine and the weekly Kite-history test.
- Follow-through at send time: price must still hold the trigger and be at most 0.3R past it; the tip uses the live
  price. Market direction: longs only with Nifty at/above its open, shorts only at/below.
- Evidence (replay, 60 days x 80 liquid stocks, free 5-min data): old rules 11,387 trades, avg +0.03R, stop first
  43%; new rules 1,266 trades, avg +0.10R, stop first 40% (before ~0.10R charges). By setup at a 2R target, positive
  in BOTH months: EMA pullback, VWAP, ORB, RANGE -> on; INSIDE, FLAG -> off; GAPGO, BOUNCE too few -> off
  (REPLAY_SEED until the Kite-history test of these rules, which re-runs tonight because the rules version changed).
- Learning loop: every setup that passes the gates (sent or not) is followed to its result (data/engine_shadow.csv);
  per setup the last 40 results blend into the rank's edge (live weight grows to 100% at 40 results) and a setup with
  >= 12 results and a negative average is paused automatically (rank 10 only). It switches back on when it recovers.

## D98 (2026-11-12) Owner: "7-8 of 10 trades must be in profit" - high-probability dip buy becomes the main tip
Searched the documented high-win-rate strategies (Connors RSI-2 and relatives: Double 7s, IBS, cumulative RSI,
3-day pullback - commonly reported at 70-80% winners on US indices). Tested on 13 years of NSE data
(validation/high_prob_research.py: point-in-time top-300 liquidity universe, next-open entries/exits, 0.35% charges
+ slippage per trade; filters chosen on 2013-2023-10, holdout 2023-11..2026-11 only checked). ~21 variants tried.
- Plain versions on NSE stocks: 56-63% winners (lower than the US claims - individual stocks + real charges).
- Chosen (best on the development years, confirmed on the holdout): RSI(2) < 2, stock >= 10% above its 200-day
  average, Nifty above its 200-day average with Nifty RSI(2) < 20; sell at the next open after the first close
  above the 5-day average; safety stop 4 x ATR; 10-day time limit. 1,660 trades: 71.9% winners, +1.74% per trade
  after charges (avg win +3.9%, avg loss -3.9%); holdout 70.1% winners, +2.06%. Worst year 38.5% winners.
- It trades only when the market dips inside an uptrend: 19 such days in 2024, 36 in 2025, 8 in 2026 (Nifty was
  below its 200-day average for 170 of 212 days in 2026 and crossed back above on 12 Nov). It waits rather than
  forcing trades.
- Telegram: evening "Buy tomorrow at open" in the Normal-trade format (RANK 9-10, 2% risk), sell alert when it
  closes above the 5-day average, time-limit alert, safety stop watched live.
- Switched OFF: a3 swing tips (~53% winners; settings normal_a3_tips) and intraday tips until a setup proves >= 65%
  winners over >= 40 live results (settings intraday_mode: auto). Intraday setups keep being followed silently.

## D99 (2026-11-13) Owner: best trades from all - intraday, F&O. Tested; what passed is switched on
- Intraday, high-hit-rate attempt (60 days x 100 liquid stocks, live rules, 1.5 ATR minimum stop, targets 0.4R-1R,
  0.06% charges): win rates 55-66% at small targets but the average after charges is NEGATIVE for every setup in at
  least one half. No intraday tips (intraday_mode auto: only after >= 65% winners over >= 40 live results).
- Index dip-buy (Nifty / Bank Nifty RSI2, 13 years): 60-69% winners but average moves only +0.1-0.4% in ~4 days -
  option buying on that loses to time decay; not used.
- F&O ON: the high-probability dip buy on F&O stocks, as a ~2% in-the-money CALL, monthly expiry >= 15 days away.
  Modelled (validation/high_prob_options_research.py: Black-Scholes on each trade's real stock path, IV = 20-day
  realised vol x 1.15, 1.5% option costs, top-150 stocks): 811 trades, 69.7% in profit, +16.9% of premium on
  average (win +37%, loss -30%); holdout 70.3%, +18.8%. Modelled, not real option history (none exists free for
  expired contracts); live premium, OI and spread are checked when sent; skipped if the loss at the stock's stop is
  above the rank's limit (5% at rank 9-10) or a lot costs > half the capital.
- Market on 13 Nov: Nifty 25,299, above its 200-day average (23,992), 2-day RSI 100 - not a dip day. Tips (stock +
  option) come on the next market dip inside this uptrend.

## D100 (2026-11-13) Forwarded F&O tips: probability out of 10, reasons, take the good ones; notes for other messages
- Bot replies to forwarded messages again (owner's request; settings reply_to_forwarded).
- F&O tips (e.g. "VOLTAS NOV 1120 PE 25-26 / Target-35-42-50-58+ / Stoploss-1150 SPOT (75 Min CB) / Lot 375"):
  parser now reads the premium range right after the strike, a stop-loss on SPOT and the candle basis.
  swing/fno_analyst.py: live spot + option premium/OI/spread (Kite), exact expiry and lot; implied volatility from
  the premium; premium targets/stop -> spot levels (Black-Scholes, some time decay allowed); PROBABILITY of target 1
  before the stop = mean of the Time Machine on the stock's 5-minute bars (to expiry, max 5 days) and the stock's
  daily history; adjusted for daily trend, option price vs real volatility (IV/HV), days to expiry, chasing,
  spread, and the channel's record (30% weight once it has 10+ finished calls). Reply: PROBABILITY x/10, why it can
  work / fail, plan, per-lot gain/loss, a better version (next expiry, fairer stop).
- TAKEN when probability >= 7/10, target 1 pays at least what the stop costs, and the loss per lot fits the limit
  for that quality (5% / 3% of capital): tracked with exit alerts like the system's own F&O tips. Every forwarded
  call is also followed to its result, so each channel's record (and its weight) improves with time.
- Other forwarded messages (views, news, commentary): mood, stocks and levels are read and kept privately with
  that channel (data/private/channel_notes.csv); two-line "noted" reply.

## D101 (2026-11-13) Forwarded watchlists (pictures or text)
3+ NSE stocks named (symbols or company names; OCR for pictures) -> swing/watchlist.py: each stock rated /10 by
the system's own read (trend, 2-day RSI, the D98 dip-buy rule incl. the market filter, pattern library, distance
from the 52-week high, liquidity), best first, one line of reasons each. A dip-buy signal that exists now is sent as
a Normal-trade tip (and F&O when it fits). All stocks stay watched for 45 days (data/private/watchlist.csv) and are
added to the evening dip-buy scan; stocks outside the tested top-300 are labelled as such.

## D102 - 2026-11-13 - Watchlist pictures read line by line, one combined list (free)
Real NDTV Profit / CNBC-TV18 "stocks to watch" pictures broke the plain text match: merged words (HITACHIENERGY,
TDPower), channel short names (Voda Idea, Zee Ent, Godrej Props, NMDC Steel), misspellings (Mannapuram) and false hits
(NDTV, STAR, TAKE, CLEAN, GLOBAL). Now:
- OCR keeps each line's position and the colour of the arrow printed next to it.
- Each line is matched as a name: channel alias list -> symbol -> company name (also shortened, run together, OCR
  l/I mix-up) -> close spelling. Picture words (NDTV, CNBC, RED, Consolidated...) are never stocks.
- Direction: the RED / GREEN heading above the stock in its column, else the green / red arrow. The channel's reason
  is the line under the name.
- Pictures sent together (one Telegram album) give ONE list: bullish then bearish, each stock once (×2 = named in
  2 lists), with my chart score /10. Bullish names are watched 45 days for the tested dip-buy (D98); bearish names
  are not (the system does not short). Long replies are split into several messages (Telegram's 4,096 limit).
Tested on the owner's 5 pictures of 13 Nov 2026: 50 of 50 stocks read with the right direction, no false names.

## D103 - 2026-11-14 - Order flow (Tredye 'Market Pulse' ideas) built from Kite data and tested (free)
Built `swing/orderflow.py`: Kite order-book buy/sell pressure, market mood (advancers/decliners, VIX), sector money
flow, Chaikin money flow, and bullish ORDER BLOCKS (last down candle before a >=1.5 ATR up move that breaks the
10-day high; first return into the zone = the 'call'). 13-year test, top-300, next-open entry, 0.35% costs,
holdout from 2023-11 (`validation/orderflow_research.py`, `orderflow_robust.py`):

| idea | trades | in profit | avg | holdout in profit |
|---|---|---|---|---|
| dip-buy D98 (baseline) | 1,660 | 71.9% | +1.74% | 70.1% |
| **dip-buy at an order block** | **347** | **80.7%** | **+3.03%** | **82.1%** |
| dip-buy NOT at an order block | 1,372 | 70.3% | +1.49% | 67.1% |
| + stock money flow positive | 459 | 69.9% | +1.82% | 68.5% |
| + breadth risk-on | 788 | 72.2% | +1.74% | 70.8% |
| order-block call ALONE, 2R target | 5,081 | 42.6% | +0.15% | 42.2% |
| order-block call ALONE, exit >SMA5 | 5,193 | 49.2% | -0.09% | 48.1% |

All 27 nearby settings (impulse 1-2 ATR, zone life 30-120 days, touch within 1-5 days) give 76-86%; the middle
setting is used, not the best one. Weak years: 2016 60%, 2019 57%, 2026 so far 57% (7 trades).
Decision: a dip-buy signal at an order block is ranked 10/10 and the tip says so; others stay 9/10. Order-block
calls on their own, money flow and breadth are NOT used (no edge). Sector flow could not be tested (sector known
for too few stocks). Live bid/ask pressure has no history: recorded every 30 min for liquid stocks
(`data/orderflow_shadow.csv`, market data only) and judged by `orderflow.evaluate()` before it may ever count.

## D104 - 2026-11-14 - Positional trades: Rolling Candle Profile (Zeiierman) - and AVPT (PhenLabs) rejected (free)
Exact Python port of the owner-supplied Pine source (`swing/rolling_profile.py`, CC BY-NC-SA, attributed; the
paste ended inside the SELL rule, the last step follows the author's description). Tests, next-open entry, 0.35%:
- Daily, 13 years, top-300, exit on its own SELL signal: 9,552 trades, 44% in profit, +4.4% avg (wins +21%, losses
  -9%), ~43 days. Random top-300 stock held as long: +2.7%. Hourly (3 years): ~0 after costs in every variant.
  Exiting at the anchor or fixed ATR targets removes the edge. Hybrid mode is worse than Price mode.
- Positional filter search (`validation/rolling_profile_positional.py`, chosen on development, checked on holdout):
  BUY only when the stock is within 10% of its 52-week high, 5 x ATR safety stop: 6,340 trades, 45% in profit,
  +5.4% avg (development +6.1%, holdout 43% / +3.2% vs random +2.1%).
Decision: new 'Positional trade' tips in the evening (rank 6/10, 1% risk, at most 2 new a day and 4 open, stocks
only), exit alert on the indicator's SELL signal or after 60 trading days; the safety stop is watched live.
Settings: positional_tips, positional_max_new, positional_max_open.

AVPT - Anchored VWAP Pullback & Target Zones (PhenLabs, MPL-2.0): the paste ended inside trade management, so the
pullback / reclaim / target rules were rebuilt from the code shown + the author's page (`validation/avpt_research.py`,
long side, all 6 profiles, 1/3 sold at each target, break-even after TP1, next-open entry, 0.35%):
- Daily: +2.0 to +2.9% a trade over ~37 days, 57% in profit - about the same as holding a random top-300 stock as
  long (+2.3%); holdout +0.4 to +1.3% (random ~+1.8%). Hourly: -0.1 to +0.1% (holdout about -0.2%).
- Its dashboard counts a trade as a win once TP1 is touched, and 'Auto-Optimize' picks the profile with the best
  win rate on the same chart it reports on (in-sample) - both make its on-chart statistics look better than real.
Decision: not used.

## D105 - 2026-11-14 - 20 TradingView indicators tested; 5 become dip-buy confirmations (free)
Rebuilt in `validation/indicator_lab.py` (from each script's published rules and standard defaults): SuperTrend,
UT Bot, Squeeze Momentum, CM Williams Vix Fix, WaveTrend, Trend Magic, MACD (ChrisMoody), LuxAlgo S/R Levels with
Breaks, LuxAlgo Trendlines with Breaks, LuxAlgo SMC (internal/swing BOS & CHoCH, FVG), S/R Channels
(LonesomeTheBlue), swing high/low S/R, ChartPrime high-volume boxes, RedK VA-CCI, EmreKb Market Structure Break &
Order Block, WillyAlgoTrader HTF Sweep + CISD, ICT killzones (adapted to the NSE first hour), BigBeluga trend volume
profile, plus Rolling Candle Profile. Not testable: JMX v3 (protected source, no rules), HTF Trend Frontier
(formulas not published).
1. STAND-ALONE (swing daily 13y top-300, intraday hourly squared off, F&O hourly 2 days both sides; costs 0.35 /
   0.12 / 0.30%): no indicator beats random holding after costs except Rolling Candle Profile on daily (+1.1% edge,
   holdout ~0 with a 30-day cap; positional version D104). Intraday and F&O: every one negative after costs.
2. AS CONFIRMATION of the dip-buy (`validation/indicator_confluence.py`, `hp_tiers.py`):
   fear spike (Vix Fix) + strong zone (order block / WaveTrend oversold / EmreKb MSB order block / swing-low hold):
   454 trades 79% in profit +2.7% (holdout 81%); fear spike alone 811, 72%, +1.9%; zone without spike 49, 74%;
   NO spike and no zone 391, 64%, +0.4%; Squeeze ON 396, 65%, +0.4% (holdout 51%). SuperTrend / BigBeluga
   bullish made dip-buys worse. Positional: no confirmation helped reliably.
Decision: dip-buy tips now need a tier - A (rank 10), B (9), C (8); weak dips (no spike & no zone, or Squeeze ON)
are not sent. Kept trades: 1,040, 76% in profit, +2.5% avg (holdout 75%, +2.8%) vs 72% / +1.7% before.
Intraday stays paused (D97 gate) - none of the 20 indicators gave an intraday edge after costs.

## D106 - 2026-11-14 - Owner's decision: intraday ON now, no count limits
Owner: "Start intraday, no limits like 2 new tips... if there is a good one send it instantly... dip buy is not
always possible, that does not mean no trade."
- intraday_mode: on (the D97/D98 gate - 40 live results with >= 65% winners first - is removed); intraday_tips on;
  intraday_max_tips 0 (no daily cap); positional_max_new / max_open 0 (no cap); risk_limits.max_trades_per_day 0.
- Kept (quality and money safety, not counts): rank >= 8 to send, liquidity (>= Rs 1 cr traded), the breakout must
  still be holding and Nifty must agree, no new intraday tip after 2:30 pm, square-off alert at 3:15 pm, stop-loss
  on every tip, quantity from 1% risk (risk by rank), 25% max per order, 2% daily-loss stop on order tickets.
- The engine keeps learning: every qualified setup is followed (shadow), and a setup whose live results turn
  negative is paused automatically (needs rank 10 until it recovers).
Evidence stated to the owner: in testing (D97, D105) no intraday setup or indicator was profitable after costs;
intraday tips are therefore higher risk than the dip-buy / positional tips.

## D107 - 2026-11-16 - Live engine: F&O list reloads after a late Kite login; funnel counts
The engine loaded the F&O list once at 9:14 while not yet logged in -> 0 F&O underlyings all day. Now it reloads
when Kite connects. Why setups are dropped is counted and logged every 30 minutes (counts only).

## D108 - 2026-11-16 - Unattended for the long run
- A failed GitHub run (package install, the bot itself...) now sends ONE Telegram 'system problem' message per
  6 hours (new allowed label, only for real breakage); the crash-loop warning uses it too (it was muted before).
- requirements.txt: lower bounds = versions proven on GitHub, upper bounds block future MAJOR releases that could
  break the unattended system; yfinance floats inside 1.x because Yahoo changes need its fixes.
- Already in place: hand-over chain (keep_alive) + hourly safety start, self-update on code change, crash-loop guard,
  shadow learning / automatic pausing of losing setups, weekly re-test of the rules on Kite history.
- What stays with the owner: the daily Kite login tap (Zerodha requires a human login every day), renewing the
  Kite Connect subscription, and the GitHub / Telegram accounts.

## D109 - 2026-11-16 - Autopilot: the system grades itself (before Claude is switched off)
`swing/autopilot.py`: every closed tip stores its real result (result_pct, closed_at). Per strategy (dip-buy,
positional, intraday, F&O) over the last 20-30 closed tips: live avg < 0 -> dip-buy only 10/10; positional paused
60 days then retried; intraday paused until the shadow record (all followed setups) is positive. Setups whose
shadow record is clearly good (>= 40 results, >= 60% winners, avg >= +0.15R) may send from rank 7. Evening data /
self-test problems and "logged in but no Kite prices for 30 min" -> one 'system problem' message a day.
Owner's manual: OWNER_GUIDE.md.

## D110 - 2026-11-16 - AI picks: market-wide machine-learning ranker (free; scikit-learn)
`validation/ml_ranker_research.py`: ~35 features per stock-day (momentum 1d-1y, mean reversion, trend, volatility,
volume, 52-week position, strength vs market, Vix Fix, WaveTrend, squeeze, market regime), cross-sectional ranks,
gradient boosting, target = next-10-day return rank. STRICT walk-forward 2016-2026 (each year trained only on data
ending 15 days before it). Net of 0.35%: top-5 +0.82% / 10 days vs +0.34% average stock; better in 8 of 11 years
(2021-2023 slightly worse); last 3 years +0.94% vs +0.30%; IC 0.053; ~52% of picks in profit.
As a filter on the dip-buy / positional it did NOT help (`ml_combo.py`) - so it is a separate tip type:
'AI pick' every evening (top 5, max 10 open, rank 6/10, 1% risk, wide 4 ATR safety stop, sell after 10 trading
days), retrained weekly on the runner; autopilot pauses it 60 days if its live record turns negative.

## D111 - 2026-11-16 - Late Kite login handled
Before the owner logs in, open tips' stops/targets are watched with Yahoo prices (every 2 min); a third login
reminder at 11:00; on a login after 9:25 a 'Kite connected at HH:MM - live scanning started, N open tips watched'
message. Scanning, the F&O list (D107) and all tip types start the moment the login arrives.

## D112 - 2026-11-16 - Strategy discovery engine: the system invents new strategies itself
`swing/discovery.py`. Weekly: ~400 NEW combinations (first run 1,500) of 2-3 of ~50 building blocks (cross-sectional
extremes of momentum, RSI, distance from averages, 52-week position, volume surge, volatility, Vix Fix, WaveTrend,
closing strength, gap, strength vs market; squeeze; market trend / dip / breadth) x hold 5 / 10 / 20 days, never
retesting a combination. Gates (fresh signals, 0.35% costs, point-in-time top-300): EVERY one of 2013-2019,
2020-2022 and the last 3 years: enough trades, >= 53% in profit, avg >= +1.0 / +0.8 / +0.5%, beating the average
stock on the same days by >= 0.7%; positive in >= 70% of years. Survivors (max 5) are followed silently live;
>= 20 live results with >= 55% in profit and positive avg -> promoted (max 3, rank 7, 1% risk, 4 ATR safety stop,
exit after the hold); a promoted strategy whose live avg turns negative over 20 tips is retired. Owner told on
promotion / retirement ('autopilot' Telegram label; autopilot messages moved to it too).
First sweep (local, 1,500 combinations): 1 survivor - S1 "far above its 200-day average + strong 14-day RSI +
closed near the day's low, hold 20 days": 2013-19 55% / +1.85% (excess +0.95), 2020-22 53% / +2.05% (+1.03),
last 3 years 55% / +2.13% (+1.18), 12 of 14 years positive. (The live system runs its own first sweep.)

## D113 - 2026-11-17 - BUG: the live tip store was not kept between runs (fixed)
journal/live_tips.csv was neither in the Actions cache (only data/ is carried over) nor committed (personal), so
every run started with an empty store: multi-day tips (positional, dip-buy, AI, F&O) lost their exit alerts after
the run that sent them ended, /tips was empty and the autopilot had no live record. Moved to
data/private/live_tips.csv (carried over, never committed); smart_money.csv too. The owner's lost 16 Nov positional
tips are recomputed from the 16 Nov price bars, re-sent as cards and put back into tracking (one-off).

## D114 - 2026-11-17 - Audit fixes (evening run)
- Evening jobs were nested: a crash in the dip-buy step skipped positional, AI picks, discovery and the autopilot.
  Now each is independent and logs its own failure.
- New evening tips are sent only on FRESH prices (exits always run); stale data -> no new tips + one alert.
- Freshness was judged against the last NSE bhavcopy file, which may be unreachable from GitHub -> stale prices
  looked fresh. Now also: did Nifty actually trade today (5-minute bars dated today)?
- The process clock is now Indian time (GitHub runs on UTC: 0:00-5:30 am IST 'today' was yesterday).
- Long jobs (nightly, research ~1 h) blocked the bot: no replies, exit alerts or updates while they ran. They now
  run in a background thread (one at a time); a code update waits for a running job to finish.
- A brief Telegram outage (502) no longer sends the owner a warning - only a problem lasting 30+ minutes.
- Tip wording 'tomorrow' -> 'the next market open' (Friday evening tips said 'tomorrow').
- A stock is never tipped again (same type) while its earlier tip is still open; intraday tips left open by an
  engine stop are closed at that day's close in the evening run.
- Verified on real data: the whole evening run (exits, dip-buy, positional, AI picks, discovery, autopilot) and
  /tips work end to end; the lost 16 Nov positional tips were rebuilt, re-sent and are tracked again.

## D115 - 2026-11-17 - Full audit: safety core, independent re-validation, claim corrections
Evidence and details: FINAL_AUDIT_REPORT.md, SAFETY_AND_SECURITY_REPORT.md, FAILURE_TEST_REPORT.md,
BACKTEST_VALIDATION.md, KNOWN_LIMITATIONS.md.

**Safety**
- Every new tip passes `safety.check_new_entry` (kill switch, latched safety stop, explicit capital, tip validation, portfolio and per-strategy risk caps, losing-streak cooldown).
- 1% risk per tip for all strategies, options included (option tips had risked up to 5%). Orders ≤ 25% of capital.
- Learning can only tighten. Discovered strategies need `/approve`. Strategy switches are proposals (`allow_auto_promotion: false`). AI retraining is validation-gated with rollback.

**Claims corrected** (independent re-test: next-open entry, gap-adjusted stops, 228 delisted stocks rebuilt from NSE files, ETFs excluded, 0.35% costs)
- Dip-buy: reproduced. 76.5% in profit, +2.39% per trade; out-of-sample 75.3%, +2.79%.
- Positional: the win rate is reproduced (45.3%). The average is **+3.8%, not +5.4%** (wins +19%, losses −9%). `positional.STATS` updated.
- AI picks: "better than the average stock in 8 of 11 years" is **not** reproduced after costs: it is 6 of 11, and the after-cost margin is about +0.1% per 10 days. `ml_ranker.STATS` and the tip wording are updated ("SMALL edge, lowest-priority tip"). It stays on, capped at 3% of capital at risk. Switching it off is the owner's decision (`ai_picks: false`).
- Discovered S1: weak in a realistic 2-slot account (+0.76% per trade, 5 losing years). Not approved; recommend not approving.
- Intraday / F&O: no edge after costs. Shadow mode, EXPERIMENTAL.

## D116 - 2026-11-17 - Owner: AI picks OFF; instant exit alerts
- `ai_picks: false` (owner: "don't want AI picks"). No new AI picks and no weekly retraining; any open AI pick still gets its exit alert and its 10-day exit.
- **Fast exit watch** (`Engine.watch_exits`): its own thread checks the open tips' stocks every ~5 seconds with one small Kite request, independent of the slow whole-market scan.
  - Before, open tips were checked every ~30 seconds, once the full refresh had finished.
  - Without a Kite login it uses Yahoo every 60 seconds (was 120).
  - For a tip from before today, today's high and low also count, so a touch between two checks is never missed.
- Exit messages say which tip it is (positional / dip-buy / ...), the stop or target, the price now, the entry, and the result in % and ₹ for the tip's quantity.
  - A gap or fast fall through the stop is reported at the realistic price (today's open or the price now), not the stop.
  - The record uses that price too.

## D117 - 2026-11-17 - Owner: no limit on positional tips; limits count only trades the owner takes
Owner: "Now on there will be no limits on this... give tips, if I will buy I will tell."
- The positional per-strategy cap (4% at risk = 4 open tips) is removed.
- The portfolio limits (total money at risk, open count, per-strategy caps for experimental types, losing-streak cooldown) now count **only tips the owner confirmed with `/bought SYMBOL`**. Unconfirmed or skipped tips never block new ones.
- `/skip SYMBOL`: the tip is still tracked (the live record stays honest) but sends no exit alerts.
- Every tip ends with "Bought it? Reply /bought X · Not taking it? /skip X".
- Unchanged: per-tip checks (1% risk, order ≤ 25% of capital, valid numbers), the kill switch, the safety stop, and never the same stock twice while its tip is open.

## D118 - 2026-11-17 - New trade finder: BREAKOUT tips (52-week-high + tight-range breakouts)
Owner: "Find other smarter and best ways of finding trades, and do tests."
`validation/new_strategies_research.py` tested 6 published swing methods with textbook settings. The setup:
- No tuning on our data.
- The same independent simulator as BACKTEST_VALIDATION.md: delisted stocks included, entry at the next open, gap-adjusted stops, 0.35% costs.
- A pass bar committed **before** the first run: CI above 0, out-of-sample positive, beats the average stock in ≥ 60% of years, profit factor ≥ 1.3, positive at 0.60% costs.

| Method | Trades | Win% | Avg/trade | Out-of-sample | Years beating avg stock | Verdict |
|---|---|---|---|---|---|---|
| 52-week-high breakout on volume (BRK52) | 4,799 | 39.0 | +2.94% | +2.09% | 79% | **PASS** |
| Minervini trend template + breakout | 5,261 | 33.3 | +2.24% | +0.70% | 79% | PASS (not used: weak recently, overlaps) |
| Tight-range (VCP) breakout | 3,207 | 37.9 | +2.56% | +1.76% | 64% | **PASS** |
| Leader pullback to 20-day EMA | 10,127 | 34.8 | +0.51% | +0.31% | 50% | fail |
| Gap-and-go | 321 | 48.0 | +0.85% | +1.17% | 43% | fail (CI includes 0) |
| Turtle 55-day breakout | 8,535 | 29.3 | +2.38% | +0.94% | 36% | fail (not better than holding stocks) |

**Decision:** new "Breakout trade" evening tips, `swing/breakout.py` (BRK52 or VCP).
- **Exit:** first close below the 50-day average, a 3 ATR safety stop watched live, or 60 days at most.
- **Sizing:** rank 6/10, 1% risk.
- **Combined result** (one trade per stock at a time): 5,434 trades, 38% in profit, average win +19.5%, average loss −7.5%, +2.85% per trade; last 3 years +2.03%. About 390 a year (1–2 per trading day), with 14–17% overlap with positional.
- **Autopilot:** pauses it for 60 days if its live record turns negative over 30+ tips. Setting: `breakout_tips`.

`tests/test_breakout.py` proves the live rule equals the tested rule day by day, with no look-ahead.

## D119 - 2026-11-17 - VANTAGE INDICATOR scanner: every NSE company -> Telegram
Owner: "such companies are found and sent to me on telegram ... #VANTAGE INDICATOR #Company code. Instantly. All the companies. No need of claude."

`swing/vantage.py` runs the **exact** VANTAGE AI logic (`vantage-ai/validation/replica.py`, the Pine core tested on 13 years of NSE data) on **every NSE equity**: 2,599 companies from NSE's own list, ETFs excluded.
- **When:**
  - 3:40 pm on trading days, using today's candle from Kite (minutes after the close).
  - Without a Kite login, at 6:50 pm with Yahoo's candle.
  - Holidays are skipped. Stale price history means the stock is skipped, never guessed.
- **Message:**
  - BUY: `#VANTAGE INDICATOR` / `#SYMBOL`, then the signal type, likely win %, entry and stop. Thinly traded stocks (under ₹1 crore a day) are flagged.
  - SELL: sent later only for BUYs that were sent, with the reason and result. If the exit day could not be scanned, the SELL is still sent on the next scan.
- **Safety:**
  - Each signal is recorded (`data/private/vantage_signals.csv`) before it is sent, and is never sent twice.
  - Delivery is retried if Telegram is down.
  - The kill switch and safety stop block new BUYs.
  - Switch: `vantage_scanner`.
- **Coverage:** a stock needs about 2 years of daily history (520 bars). Newer listings are scanned once they have it.
- **Validation:** the 13-year test covered the top 300; smaller companies are scanned with the same rules but were not part of that test.
- **Evidence:** `tests/test_vantage_scanner.py` shows the scan's "today" signal equals the backtest's signal for that day. A dry run on 1,192 stocks took 86 s.

## D120 - 2026-11-17 - VANTAGE INDICATOR live during market hours
Owner: "Market is going on ... if any stock among all NSE stocks gets a signal, I get an instant message."
- **Live scan:** `scripts/run_vantage_live.py` is started by the daemon at 9:20 and runs to 3:30 as its own process.
  - Every ~3 minutes it runs the same VANTAGE logic on every NSE stock using **today's candle so far**: open, high, low, last price and volume from the live engine's 30-second Kite quotes, saved to `data/live_quotes.json` (no extra Kite requests).
  - A fast check first skips stocks that cannot meet any BUY's necessary condition. A test proves it never drops a real signal. A cycle takes ~40 s for all stocks.
- **⚡ LIVE BUY alert:** sent once per stock per day.
  - It is a forming signal and can disappear before the close.
  - At the close scan (3:40 pm) each live alert gets ✅ CONFIRMED (with the normal BUY message, now tracked) or ❌ CANCELLED.
  - **The tested results apply to confirmed signals only.** Acting on a live alert before the close is untested.
- **🔴 Stop-loss:** for BUYs already sent, alerted instantly when the day's low touches the stop.
- **Safety:**
  - Snapshots older than 3 minutes are never used.
  - Stale histories are skipped.
  - The kill switch and safety stop block live BUYs.
  - Everything is recorded before it is sent.
  - Switch: `vantage_live`.
- **Needs** the day's Kite login. Without it there are no live alerts, and the evening scan still runs.

## D121 - 2026-11-17 - Improvement research results; liquidity floor for VANTAGE signals (owner-approved)
The pre-registered tests (`vantage-ai/validation/IMPROVE_PREREGISTRATION.md`, results in `IMPROVE_RESULTS.md`) were all judged on the Nov 2023+ holdout.
- **Failed (not adopted):**
  - market-breadth filter, leader (RS) filter, sector filter, delivery-% filter
  - meta-labeling (personal likely %)
  - break-even and time-stop exits
  - wider dip-buy rules

  They helped in older data but not in the recent three years, or they cut profits.
- **Passed:** scanning all NSE stocks that trade **≥ ₹2 crore a day**. That's about 25 signals a week in the holdout at the same quality (+2.9% per trade, PF 1.48). Stocks under ₹2 cr/day were weaker (PF 1.20).
- **Applied (owner approved):** VANTAGE BUY signals, live and end-of-day, only for stocks with a 20-day average traded value ≥ ₹2 cr. Setting: `vantage_min_turnover_cr`. SELLs and stop alerts for BUYs already sent are unaffected.

## D122 - 2026-11-17 - Round 2 decisions
- **Limit entry (R2), a near miss in the test:** the owner chose a forward test. Every VANTAGE BUY now records `limit_test` = signal close − 0.25 ATR in `data/private/vantage_signals.csv`. After a few weeks, the live record shows whether a limit order would have filled and helped. Nothing changes in the messages.
- **Results-day guard (R4) passed,** but the owner does not want BUYs blocked ("results can also give better ones").
  - Data: signals with results due within 5 trading days still earn money, but about half (+1.7% vs +3.5% per trade in the last 3 years).
  - Proposed (awaiting approval): keep the signal, show the results date, and halve the quantity.
- **D123 (owner approved):** VANTAGE BUYs with company results due within 5 trading days are still sent. The message shows "📅 Results on <date> (in N trading days) - half quantity", and the quantity uses half the risk (0.5%). Results dates come from `data/events/earnings` (506 companies; no change for others).
- **D124:** the approved results rule (D123) is extended to every stock tip (dip-buy, positional, breakout, others) in `live_engine.issue_tip`: results within 5 trading days means the date is shown and the quantity is halved. Option and intraday tips are unchanged.

## D125 - 2026-11-18 - 24-hour push: buy before the close (round 3 passed, applied)
The owner shortened the research push to 24 hours: "do whatever it needs and make the most best for me".
- **Test:** `vantage-ai/validation/IMPROVE3_PREREGISTRATION.md` and `IMPROVE3_RESULTS.md`. Buying VANTAGE signals at the signal day's close beat the next-morning open in both periods.
  - Holdout: +3.24% vs +2.91% per trade, 44.2% vs 42.5% won.
  - Development: +4.31% vs +4.08%.
- **Applied:** every ~3 minutes between 3:15 and 3:29 pm, each stock with a VANTAGE BUY on today's nearly finished candle gets one "🔔 BUY NOW - before the 3:30 pm close" alert. It carries the price, stop, quantity and results note, and goes only to stocks of ₹2 cr/day or more.
- **At 3:40 pm:**
  - If the signal held: "✅ CONFIRMED - if you bought before the close, you are in. Missed it? Buy at the next open".
  - If it did not hold: "❌ ... sell at the next market open".
- **Records:** `data/private/vantage_closecall.csv` is written before sending.
- **Switch:** `vantage_close_call`.
- **Limits:** no change to risk limits or sizing. The kill switch and safety stop block these alerts.
- Needs the day's Kite login, like the other live alerts.

## D126 - 2026-11-18 - Monthly basket of the 20 strongest stocks (round 4 passed, applied)
- **Test:** M3 = the NSE-momentum-index-style ranking of the point-in-time top-300, 20 stocks with equal money, monthly, cash when NIFTY is below its 200-day average. It passed every pre-registered condition.
  - Holdout: 19.5% a year vs NIFTY 7.4%, worst fall 8.9% vs 14.8%.
  - Development: 24.6% vs 12.0%, worst fall 34.2% vs 29.3%.
  - It beat NIFTY in 71% of calendar years.
  - M1 and M2 (without the cash rule) failed on the worst-fall condition.
- **Applied:** `swing/basket.py`, daemon job `basket` on weekday evenings at 7:05 pm or later. It sends once a month, after the last weekday of the month; if that day is a holiday, it sends on the next trading day. The first basket goes out at the first run.
  - The message lists SELL, BUY and KEEP for the next open.
  - The ETF/fund exclusion matches the test.
- **Quantities:** only when the owner sets the money with `/basket 20000` in Telegram, or `basket_capital` in settings.yaml. Otherwise there are no quantities. Capital is never guessed.
- **Kill switch:** sells only.
- **No stop-loss** (as tested). The message says plainly that it can fall 10–30% in bad years.
- **Switch:** `monthly_basket`.

## D127 - 2026-11-18 - Round 5: new short-term setups failed (not adopted)
Pocket pivot, NR7 breakout and the 3-day pullback in leaders give 20–40 trades a week but earn about zero after costs (holdout −0.12%, −0.23% and +0.18% per trade). See `IMPROVE5_RESULTS.md`. Not adopted.

## D128 - 2026-11-18 - Practice mode
`SWING_DRY_RUN=1` writes every Telegram message to `data/private/dry_run_messages.txt` instead of sending it. `scripts/dry_run_all.py` runs every daily job on a copy of the system in that mode, for end-to-end checks without touching the owner's chat or data.

## D129 - 2026-11-18 - Fixes found by the practice run
- **Yahoo can publish the day's prices hours late.** The 6:50 pm backup scan used to count as done even when only a few stocks had the day's candle. It now scans only when at least 60% of normal stocks have it. Otherwise it retries every 20 minutes, up to 12 times (`daemon.retry_later`).
- **A broken scan is never reported as "0 signals".** If more than 20% of stocks fail inside the VANTAGE logic, the scan stops and a "system problem" message is sent.
- **The practice run** (`scripts/dry_run_all.py`) now copies the repository layout, including `vantage-ai/`.

## D130 - 2026-11-18 - "Almost every tip shows 46%": explained and made clear
- **Owner's observation:** almost all VANTAGE tips showed 46%. The cause: the likely-win % is the 13-year record of the signal TYPE, and the trend-follow type (Rolling Candle Profile) makes up ~75% of signals.
- **Pre-registered test** (`vantage-ai/validation/CALIB_PREREGISTRATION.md` / `CALIB_RESULTS.md`): a per-signal % from 10 facts known on the signal day, including the company's own past record. It **failed** on the 2023-26 holdout.
  - It was no more accurate than the type table.
  - There was no steady pattern within the trend-follow type.
  - A company's own past record did not predict its next signal.
- **Applied:** every VANTAGE BUY message (end of day, live, buy-before-close) now carries two lines.
  - "📊 Past record of this signal type: 46% won (43% in the last 3 years), average +4.0% per trade - fewer than half win, but winners are bigger than losers"
  - "🏢 SYMBOL: x of y past VANTAGE signals won"
- **Daily ranked list:** it shows the type next to each VANTAGE tip, plus a one-line note on what the % means.
- No change to which tips are sent.

## D131 - 2026-11-18 - VANTAGE message layout set by the owner
- **Owner's exact layout:**
  - The header line keeps "· likely win N%". For live alerts it reads "... if it holds to the close".
  - "Price now ₹X (HH:MM) · " sits on its own line, then "🛑 Stop-loss ₹Y".
  - "📦 Qty: N shares ≈ ₹Z · " is followed on the next line by "🛘 max loss ≈ ₹W (1% of ₹45,000)".
  - The ⏳ line comes next.
  - Last line: "Note : X of Y past Vantage signals won."
- The "📊 Past record of this signal type" line (D130) is removed.
- The same layout applies to the 3:20 pm buy-now and 3:40 pm BUY messages.
- **The company record** (`vantage-ai/validation/company_record.json`, built by `company_record.py`) covers 2,351 NSE companies with at least 2 years of prices. It counts each company's VANTAGE signals over its whole history in the 13-year test, using the same logic, costs and data handling as round 1's all-stock run. Companies listed less than 2 years ago show "No past Vantage signals for this company yet."

## D132 - 2026-11-18 - Silent forward record: promoter buying (owner: "Yes")
- **The idea:** round 9's near miss (#4). Buy the morning after a promoter market purchase of ≥ ₹10 lakh is disclosed, sell 5 trading days later. In the test it made +0.8% per trade in both periods, against a bar of +1.0%.
- **The record:** `swing/shadow.py`, run in the evening job after the price update. It records every new disclosure in `data/private/shadow_promoter.csv`, one per stock per day, and fills in the would-be trade once prices exist. It applies the same costs and the same ₹2 cr/day filter as the test.
- **Effect on the owner:** no messages, no change to tips.
- **Decision point:** after a few months of live events, the record shows whether the idea reaches the bar.

## D133 - 2026-11-18 - Add to winning trend trades (round 13, owner: "Yes, do it")
- **Rule:** an open VANTAGE trend (Rolling Candle Profile) signal that is up ≥ 8% at the close of its 15th trading day after entry gets one "📈 ADD MORE" message.
  - The second lot is bought at the next open and exits together with the first lot.
  - The check runs once only, on exactly that day, as tested. It is recorded in `vantage_signals.csv` (`added`) before sending.
- **Safety change from the tested version:**
  - The test sized the second lot from its own price, so a stop-out could lose ~3–4% of capital on it. That is above the owner's 1% per-trade limit.
  - The live version sizes it to the REAL stop-loss (the first lot's), so the loss stays ≤ 1%.
  - Re-tested (`improve13_riskcapped.py`): +1.0, +1.0, +0.9 and +0.4 points of yearly growth in the four cells (top-300 and all stocks × development and holdout), with the worst fall at most 1.5 points deeper. That is smaller than the +1–2 points of the tested version, but within the risk rules.
- **No message** under the kill switch or safety stop, when capital is not set, or when one share does not fit.
- **Results rule:** results within 5 days → half quantity (D123/D124).
- **Switch:** `vantage_add_to_winners`.

## D134 - 2026-11-18 - Capital set to ₹51,000 (owner: "from tomorrow I will start final trading... total money 51,000")
- `settings.yaml` capital: 45,000 → 51,000.
- **Effect:** every quantity line now uses ₹51,000. Risk per trade is 1% = ₹510 at the stop-loss, and the maximum in one stock is 25% = ₹12,750.
- The ADD MORE second lot is also capped at 1%.
- The risk limits themselves are unchanged.

## D135 - 2026-11-18 - VANTAGE live scorecard (owner: "track the tips you have been giving")
- **What it does:** `swing/scorecard.py` runs in the evening job.
  - Every VANTAGE BUY ever sent (`vantage_signals.csv`) is scored from its "buy ≈" price to its exit, or to today's close if still open.
  - Each tip records: days held, whether the stop was touched, whether it got an ADD MORE, and whether the limit-entry test (D122) would have filled.
  - Results are set against the 13-year test per signal type, together with the promoter shadow record (D132).
- **Saved to GitHub:** `journal/vantage_scorecard.csv` and `.md`, so the research can read the live record.
- **Contents:** market signals only. Nothing about the owner's trades, money or holdings.
- **Seed:** the 17–18 Nov tips were replayed from official prices (`vantage-ai/validation/live_replay_17_18nov.csv`).
  - 17 Nov: 9 trend tips.
  - 18 Nov: 7 trend tips and 1 breakout.
  - After one day, 3 of 9 were up, average +0.4%, and no stop was hit.

## D136 - 2026-11-18 - Every tip, tracked (owner: "this mistake should not happen again at all")
- **What was wrong:** the strategy tips (journal/tips.csv since 2 Nov), hourly-scan ideas, company picks, VANTAGE tips, live-engine tips, buy-now alerts and the monthly basket were stored, but never followed and analysed together. Several strategy tips showed "open" with no buy price.
- **The fix:** `swing/tracker.py` runs every evening.
  - It follows every idea from every source with one rule set:
    - **Zone tips:** bought at the next open only inside the zone; then the stop-loss or target 1, whichever comes first.
    - **VANTAGE:** from the "buy ≈" price.
    - **Live engine:** from its entry.
    - **Company and basket picks:** price change only.
  - Closed trades pay 0.35% costs.
  - It writes `journal/all_tips.csv` (one row per idea) and `journal/all_tips.md` (by source and type, with the test next to it), both saved to GitHub. The research check-in reads them first.
  - No owner data is written (quantity, /bought, money).
- **First run (18 Nov):**
  - Strategy tips (a3): 16 bought, open average −1.75%.
  - Hourly scan: 18 bought, −1.07%.
  - The a1 tips from 2–3 Nov: ICICIBANK reached target 1 (+13.1%); FEDERALBNK is +6.9%.
  - Shadow a3 (not sent): +7.2%.
  - VANTAGE (17–18 Nov): 16 trend tips, open average +0.2%.
- **Rule from now on:** any new tip type must be added to the tracker in the same change that starts sending it.

## D137 - 2026-11-18 - The Learner: the second engine (owner: "two things simultaneously... built entire system for this")
- **What it does:** `swing/learning.py` runs every evening after the tracker (D136). It adds each idea's situation (known that day) and journey, judges live results against the 13-year profile per type (`tested_profile.json`), shows results by situation, and turns big gaps into research items (`journal/learning_queue.csv`), never into tip changes.
- **What it saves to GitHub:** `journal/learning.md`, `learning_queue.csv` and the enriched `all_tips.csv`.
- **Messages:** a "weekly learning" message every Saturday (a new allowed label), and an instant "Learning check" only when a type is clearly below its tested range.
- **Docs:** `swing-system/LEARNER.md`.

## D138 - 2026-11-18 - The Learner learns from mistakes (owner: "how we learn from our mistakes is more important")
- **Diagnosis:** every losing idea gets a plain diagnosis (never worked / gave back a profit / fast stop / gap through the stop / market fell / results shock / slow drift).
- **Also reported:** repeat stocks across channels, a review of skipped ideas, and research items when one cause explains 40%+ of a source's losses.
- **Shown in:** `journal/learning.md` (sections 4–6), the weekly message, and `all_tips.csv` (`mistake` column).
- **First findings (18 Nov):**
  - 9 losing or weak ideas, mostly from the older "a3" strategy and the hourly scan.
  - AVALON gave back a +6% profit and is now −12.4%.
  - CYIENT was sent 6 times (hourly scan and strategy tips repeat the same stocks), CHENNPETRO, EMIL and WELCORP 4 times each.
  - The one skipped idea that fell, RAIN (−14.5%), was a loss avoided.

## D139 - 2026-11-18 - No repeat tips, a sharper Learner, and a 13-year mistake census (owner: "Yes smartly"; "bare minimum, we can't wait till 40%")
- **No repeat tips:** `swing/registry.py` keeps one list of open tips across the channels that send (VANTAGE and the live engine).
  - A stock with an open tip is not sent again by another channel, or by a later live or 3:20 pm alert.
  - The blocked repeat goes to `data/private/suppressed_repeats.csv`, and the Learner follows it ("blocked repeat") to learn whether blocking was right.
  - ADD MORE is not a repeat.
  - Switch: `no_repeat_tips`.
- **Correction:** evening strategy tips and hourly-scan ideas have been log-only since 11 Nov (D95). The tracker now marks every idea "sent" or "recorded only". The earlier "CYIENT sent 6 times" was internal re-picking; it never reached the owner.
- **Learner lessons from the first sign:**
  - a situation gap of ≥ 2 points with ≥ 3 ideas a side;
  - any mistake cause seen twice;
  - each labelled weak / medium / strong evidence (2–4 / 5–9 / 10+).
- **"Gave back a profit"** now starts at +3%.
- **VANTAGE tips record the next morning's open,** to compare buying at 3:20 pm with buying the next morning.
- **Mistake census** (`vantage-ai/validation/mistake_census.py` / `.json`): the diagnosis applied to all losing VANTAGE trades of 13 years.
  - The biggest fixable cause is "gave back a profit" (all stocks: 37–38% of money lost).
  - Then market falls (21–26%) and results during the trade (top-300: 26–31%).
  - The Learner compares the live mistake mix with this normal mix and flags gaps of 15+ points.
  - Round 20 (protecting profits) was started from it.

## D140 - 2026-11-18 - Micro-inspection fix: splits and bonuses while a tip is open
- **What was wrong:** after a split or bonus (82 NSE stocks in the last 12 months), the live price falls by the ratio while the stored buy price, stop-loss and targets stay in old rupees. That produced:
  - false "stop-loss hit, exit now" alerts (VANTAGE live stop check and live-engine exits);
  - fake losses in the tracker and Learner.

  Signals were not affected, because Yahoo back-adjusts history for splits and the replica uses that history.
- **The fix:** `swing/corp_actions.py`.
  - **Evening re-scale:** open VANTAGE signals and open live-engine NORMAL tips are re-stated by Yahoo's split ratio, once per split (`split_done`).
  - **Same-day guard:** a price below 75% of yesterday's close sends no stop alert until the evening re-scale. NSE price bands make that almost impossible without a corporate action, and a real 20% fall still triggers the stop.
  - **Tracker:** zone tips recorded before a split are compared in today's rupees.
- **Tests:** `tests/test_corp_actions.py`.

## D141 - 2026-11-18 - Project ALPHA input applied (owner forwarded an architecture: "do work on that if it helps us")
- **Built:**
  - Truth Engine luck checks: the edge is stock choice, not timing.
  - Experience memory (`experiments.json`, 75 experiments).
  - Strategy register with lifecycle and live results.
  - Market memory (12 day types × 13 years; panic days were best in both periods).
  - Counterfactuals for rejected VANTAGE signals.
  - All documented in `LEARNER.md`.
- **Not built** (no value for us now): a multi-strategy capital allocator, because VANTAGE is the only proven strategy and correlation weighting needs several. Also a dashboard.
- **No live tip changed.**

## D142 - 2026-11-18 - ATLAS input applied (owner forwarded a second architecture)
- **Beliefs register** (`vantage-ai/validation/beliefs.json`): 11 beliefs, each with an evidence level, its evidence, "wrong if…" and a live check. The Learner reports the status of each (holding / at risk / broken / waiting) and asks ATLAS's daily question: "What do we believe that might be wrong, and what would prove it?" The question appears in `learning.md` and the weekly message.
- **Unknowns list:** 6 assumptions shared by every strategy (daily price/volume only; buy-only; fills assumed at open/close; results dates only for 506 companies; the holdout was a strong rally; which part of the stock choice carries the edge).
- **"Is the system getting smarter?" scorecard:**
  - discovery productivity (75 tested / 8 passed)
  - calibration
  - execution gap (the next open vs the 3:20 pm price)
  - opportunity capture (rejected and blocked ideas)
  - edge-decay flags
- **Market memory by type:** each day type now also shows how each tip type did on such days.
- **Prosecutor test of the live liquidity floor:** round 23, running.
- **Not built:** a genetic strategy search ("alpha genome"), because the risk of overfitting is high with 75 tests already on one holdout. Also a multi-strategy capital brain, because VANTAGE is the only proven strategy.

## D143 - 2026-11-19 - ATLAS build completed (owner: "Work on this. And don't ask me.")
- **Immutable idea history** (`swing/ledger.py`, `journal/ledger.jsonl`): append-only and hash-chained. Each line holds one idea's state change. The Learner checks the chain every evening and warns if it was edited. Market fields only.
- **Opportunities never detected** (Learner section): the top 20 risers of the last 20 days, compared with what was sent. On the first run 18 of 20 were never detected. They started far from their highs (median −17%), so they are a different kind of opportunity than VANTAGE's picks.
- **Research budget manager + meta-intelligence** (`swing/research_queue.py`, `journal/research_queue.md`): one ranked list of what to test next. It draws on beliefs at risk, Learner lessons, missed movers and blind spots. Each idea is weighted by how often ideas of the same kind passed in experiments.json. Repeats of failed tests are pushed down, with the test named. Budget: at most 2 pre-registered tests a week.
- **Multi-stage promotion** (`strategies/registry.json` "stages"): 7 stages, each with a fixed "to pass" bar. A strategy moves one stage only when the bar is met and the owner says yes. The Learner shows each strategy's stage and its readiness, for example "0/100 closed".
- **Portfolio risk** (weekly Telegram only, never in git): if every open tip from the channels that send now was bought as advised, it shows the money needed, the loss if all hit their stops, and the loss if the market opens 10% lower. It needs the capital to be set and never guesses it. First reading: 17 positions need 89% of ₹51,000. All stops together ≈ 15%.
- **Crash scenario** (round 24, `vantage-ai/validation/IMPROVE24_*`): survives. A 10% market gap on the worst day costs about 15% in one morning (stops cannot help a gap), and growth stays positive (recent years 18.8% → 14.5%). Found: the "worst fall" in all rounds is measured when trades close, so the real daily fall is deeper. Added to the blind spots.
- Nothing changes a live tip, the 1% risk limit or any order behaviour. Map of all parts: `ATLAS.md`.

## D144 - 2026-11-19 - APPROVED by the owner (19 Nov: "yes"): VANTAGE scans only the top-300 stocks
- Round 26: in the recent years, top-300 gave 14.8% a year with a worst fall of -20.6%. All stocks >= ₹2 cr/day, which the live system scans now, gave 7.2% and -27.5%. Top-300 also had the higher growth in 6 of 9 years since 2018, with the biggest gaps in the bad years (2018, 2022, 2025).
- Caveat: the older years favour all stocks, but they are inflated by missing delisted small caps, and the recent years had been seen before. The live record checks the decision: signals outside the top 300 are still followed silently.
- Built and tested: setting `vantage_universe: top300` (default `all`, no change until yes). If the list file is unreadable, nothing is blocked.
- Also (round 25): updating the capital setting once a month adds about 1-1.5 points a year for top-300 stocks. This is advice, not a rule.
- **Owner's yes on 19 Nov:** `vantage_universe: top300` is live from the next scan. Open tips are unchanged.

## D145 - 2026-11-19 - Research runs by itself every week (owner: "nobody will run the tests" must not happen)
- `vantage-ai/validation/autoresearch.py` runs every Friday night inside the research job on GitHub (setting `auto_research: true`). One run on 4 cores takes about 8 minutes. Each run:
  - rebuilds all VANTAGE trades from the newest prices, for the top-300 and all stocks (36,413 today);
  - rebuilds the market-type calendar and the ~40 facts per trade;
  - tests all 230+ possibilities with the AUTO_LAB_PROTOCOL bar (older years, luck worlds, recent years, year by year, random-skip placebo).
- **New step 5:** the trades signalled from 20 Nov 2026 onward have never been seen by anyone. Once there are 150 of them in the top-300, a rule must not be worse on them, and approved rules are re-checked on them every week.
- **A full pass that the live system can apply** (skip or half quantity) sends one "🔬 Research result" Telegram message. `/approve LAB-x` or `/decline LAB-x`; `/research` shows the state. Nothing acts without the owner's yes.
- **Live use:** `swing/lab_rules.py` computes the same facts with the same code. Checked on 25 real trades: all 22 facts identical. If anything fails, no rule acts.
- First run (19 Nov): 230 tested, 3 passed the older years, luck worlds 0/0/1, none passed every step. Nearest: "take the strongest 6-month risers first when money is short". It was better for top-300 (18.6% vs 16.2% a year, 11 of 14 years) but not for all stocks, and is re-checked weekly on fresh trades.

## D146 - 2026-11-19 - The why-engine (owner: "ask 'why' for everything - dig deep - test - again")
- `swing/why_engine.py` runs every evening after the Learner. Each finished tip (sent VANTAGE and live-engine tips, plus silently rejected signals) goes through five steps:
  1. **Expected:** what 13 years of similar trades said (same setup, strength, distance from the high, market trend).
  2. **Actual:** what happened.
  3. **Surprise:** as expected / won differently / won much bigger / won against the odds / lost with a known cause / lost with an unknown cause.
  4. **Why:** the main driver (market, results, gap, the stock itself, drift).
  5. **Unusual facts:** for every surprise, the entry facts where this tip sat in the top or bottom 10% are checked on history at once.
- A pattern confirmed in both periods, in the direction that explains the result, becomes a **lead** (`strategies/why_leads.json`). The research list shows it, and the weekly automatic research tests it on the account as an exact skip / half rule, with the full bar.
- Outputs: `journal/why_log.md/.csv`. The weekly message lists the latest surprises.
- **Proof run** (`scripts/why_proof.py`): 113 real test trades from June-October 2026, judged blind. Result: 60 lost with a known cause, 21 lost with an unknown cause, 23 as expected, 5 won much bigger, 4 won against the odds. 6 leads were confirmed on history, for example "the ~30 most-traded stocks" (RCP recent +0.5% vs +4.5% a trade) and "calm market" (worse). The weekly research tested all 6 as 12 account rules: none passed the older years in both trade sets. Patterns that are visible trade by trade did not add money at the account level.

## D147 - 2026-11-19 - ATLAS Context Engine: which rule works on which kind of stock (owner's conditional-edge idea)
- The system is named **ATLAS**; **VANTAGE** is its indicator.
- `vantage-ai/validation/context_engine.py` (protocol `CONTEXT_PROTOCOL.md`, committed before the run):
  - every trade gets its stock's behaviour from the 250 days before the signal: swing, beta and correlation to NIFTY, up-weeks, weekly trend persistence, gap frequency, worst fall, distance from the high, 6-month return, size;
  - ATLAS **discovers its own groups** (k-means fitted on development only), then measures walk-forward, every year from 2016, which groupings predict the next year.
- **Result:**
  - **Behaviour groups matter in both stock lists** (top vs bottom third 1.7-2.4 points a trade); behaviour x setup and behaviour x market also matter.
  - **Sector does not**, and neither does market type alone. Stocks that trade alike matter more than stocks in the same industry.
- **Rules (walk-forward, re-learned every year):**
  - "When money is short, take the best-behaving groups first": all stocks holdout 16.5% vs 8.2% a year, development +2 points in both sets. But top-300 (what is traded) holdout is only +0.8, and one luck world reached 17.5%. **Not passed.**
  - "Skip bad groups" almost never acts.
- **Runs every week inside the automatic research.** The first time a context rule passes every step, it is proposed to the owner (`/approve CTX-xxxx`). If approved, every VANTAGE tip then shows its behaviour group and rank (`strategies/context_model.json`, checked on SBIN, BAJFINANCE, MARICO). Risk is unchanged.

## D148 - 2026-11-19 - Real costs and tax in every test; every way of understanding stocks compared
- **Real costs + tax** (`vantage-ai/validation/costs_real.py`; now inside `auto_lab.sim`, so the weekly research uses them too):
  - Zerodha delivery charges, ₹15.93 DP fee per sale, 0.1% slippage each side, and 20% short-term tax on each year's net profit.
  - The live setup (VANTAGE + dip-buy, top-300) makes **15.1% a year in the older years and 12.0% in the recent years** (17.4% / 14.7% with monthly capital). The earlier 18-23% figures used a flat 0.35% cost and no tax.
  - Worst fall -21% to -28%.
  - The DP fee alone is about ₹3,700 a year on ₹51,000.
- **Context engine run 2:** company, company x setup, sector x setup, sector x behaviour, market x setup, size x sector, and a discovered decision tree were added beside behaviour groups.
  - The company's own past record does not predict.
  - Sector alone does not, but sector x setup and size x sector do.
  - No rule beats luck on the top-300.
- **Group facts** (top-300): about 5 behaviour groups hold almost all the trades, with 92-1,668 trades per group in development and 39-769 in the holdout. A stock stays in the same group for 64% of its trades less than 4 months apart, but only 39% year to year. The groups describe a stock's current state, not a fixed identity.

## D149 - 2026-11-19 - Owner's three investigations (findings recorded; NO live change; waiting for approval)
- Full evidence: `vantage-ai/validation/INVESTIGATION_19NOV.md`.
- **Company record line:** kept in every tip, now labelled "information only, not a signal". It is used nowhere else: not in the likely-win figure, ranking, rules or approvals.
- **Charges:**
  - Checked against zerodha.com/charges. Two corrections: NSE transaction 0.00307% (was 0.00297%), and DP ₹15.34 once per stock per sale day (was ₹15.93 per lot).
  - Tax is now 20% + 4% cess per financial year (April-March), with losses carried forward.
  - Applied in `auto_lab.sim` (weekly research) and `costs_real.py`.
- **NIFTY on identical terms** (same ₹51,000, same first-buy and last-sale dates, total return with a dividend assumption of 1.1-1.5%, fund fee, long-term tax at the sale):
  - 2013 - Feb 2024: system (VANTAGE + dip-buy) 15.1% a year after costs and tax vs NIFTY fund 13.5%.
  - Nov 2023 - Oct 2026: 11.5% vs 7.8%.
  - Earlier NIFTY figures were price-only, with different end dates.
- **Strict behaviour groups** (re-fitted every year on the past only):
  - The predictive value survives (top-300 1.42 points a trade, 9 of 11 years).
  - Current-behaviour membership beats sticky membership.
  - On the account it fails the bar on top-300 development (+0.2 points). The top-300 holdout gains +3.4 points and beats luck.
  - Research lead only.

## D150 - 2026-11-19 - ATLAS mission locked (MISSION.md) and the daily ATLAS brief
- `MISSION.md`: the owner's permanent mission and its principle. "Profit is the objective, capital protection is the constraint, evidence is the authority, continuous improvement is the engine." It maps each part of the mission to where it lives.
- **The daily brief** (`swing/brief.py`, setting `atlas_brief: true`): one message at 3:22 pm inside the buy window. It contains:
  - today's VANTAGE buy-now calls and live-engine tips;
  - for each, entry, stop, exit plan, quantity, money, max loss and the type's 13-year evidence;
  - ranking by evidence per ₹1 risked. It says honestly that no order passed the tests, so take all if money allows;
  - total money and total max loss;
  - the avoid list (signals the rules rejected today);
  - **"No trade today"** when nothing qualified or the safety stop is on.
- The brief only reports what the tested rules already decided: no new trading rule. Message format only.
- Also fixed: a test had written three fake signals into the local `data/private/vantage_rejected.csv`. They were removed, and every test now writes those records into a temporary folder (`tests/conftest.py`). The GitHub record was never affected.

## D151 - 2026-11-19 - ATLAS Strategy Foundry: ATLAS designs new strategies itself (owner: "do this at full capacity")
- `vantage-ai/validation/foundry.py` (protocol `FOUNDRY_PROTOCOL.md` + 2 addenda, each committed before its run) builds complete strategies (entry x filter x exit) from building blocks:
  - 16 entry families, 4 filters, 10 exits;
  - gap-adjusted stops, targets, trailing and time exits;
  - top-300 point-in-time universe with delisted stocks;
  - next-open entries;
  - verified costs + 20.8% tax on the ₹51,000 account, judged alone AND next to the live system.
- **Run 1** (336 strategies, short exits): 0 passed. Short trades cannot beat the costs and tax of a ₹51,000 account.
- **Run 2** (640): 1 passed development and the fair stock-choice luck test (20/20), then failed the holdout (4.5% alone vs NIFTY fund 7.8%).
- Lesson: at this account size the long exit (4 ATR stop, 5R target, 120 days) matters more than the entry.
- **Runs by itself every Friday** inside the automatic research. A full pass leads to two separate yeses:
  1. "🧪 ATLAS designed a NEW strategy" (`/approve FND-xxxx`): ATLAS follows it silently on live prices (`swing/foundry_shadow.py`, `journal/foundry_shadow.md`).
  2. After 100+ fresh trades still passing: "ready for real tips" (`/approve FTP-xxxx`). Then evening tips (buy at the next open) come with stop, target, quantity at 1% risk and exit alerts.
- Tips are tracked ("ATLAS strategy" in the tracker, the why-engine and money-at-risk). They follow the no-repeat rule, the kill switch / safety stop, and are never sent when one share would break the 1% limit.
- Tested end to end on real data (two signals of 18 Nov found, correct message).

## D152 - 2026-11-19 - Evening review at about 4:00 pm (owner: "I want this to be around 4")
- New daemon job `review` (`scripts/run_review.py`). It runs on weekdays from 4:00 pm, right after the 3:40 pm VANTAGE scan, at the latest by 4:20 pm.
  - It first gives every tracked stock today's bar: Yahoo, else Kite quotes, else Yahoo's 5-minute data.
  - Then it runs the scorecard, tip tracker, Learner and why-engine, and saves them to GitHub.
- It sends no tips and changes no rules. The 6:40 pm nightly job still runs the same steps again with the official day prices (final numbers), because Yahoo's daily bar replaces the early one.

## D153 - 2026-11-19 - Kite Connect used to the full (owner: "are we using it at maximum utilisation?")
- **Audit:**
  - Used: live quotes (scans, VANTAGE live and 3:20 / 3:40 pm, 4 pm review), order-book pressure, instrument list, and a little 5-minute history.
  - Unused: years of intraday history.
  - The 5-minute archive came from Yahoo, for only 150 stocks.
- **New `swing/kite_history.py`** (research job, every evening on GitHub, read-only market data, about 2,000 requests a night at Kite's 3-a-second limit):
  - backfills 15-minute candles of the top-300 + NIFTY from 2019, and 5-minute candles of the last 2 years for 9:15-9:45 and 15:00-15:30;
  - stores daily summaries (open, 3:15 pm price, close, VWAP, first-30-minute and last-hour moves, close vs VWAP) and those window bars in `data/kite_hist` (GitHub's private cache).
- Kite data is never committed to the public repository. Only the research results are (`journal/kite_research.md`).
- At 80% coverage (about 4 evenings) it runs automatically:
  - **the 3:20 pm reality check** (the 3:15 pm price vs the close on every VANTAGE signal day, which the tests assumed equal);
  - whether intraday facts on the signal day predict VANTAGE results.
- **Safety fix:** a Kite "403" for a data permission no longer deletes the day's login. Only an expired-login answer does.
- **Not used, on purpose:** the owner's account (holdings, positions, funds), under the privacy rule. Orders: never.

## D154 - 2026-11-19 - Were the tests on Kite data? No - they are now re-run on Kite exchange prices
- **Audit:** every 13-year test (VANTAGE trades, rounds 1-29, auto-lab, context engine, Foundry, cost and NIFTY checks) used Yahoo daily prices. Delisted stocks used NSE bhavcopy rebuilds. Kite was used only for live prices and a little recent 5-minute history.
- **New `swing/kite_daily.py`:** Kite daily candles for every NSE stock since 2011. It runs in the research job on GitHub, about 4,000 requests a night until complete (about 2 nights), then tops up the last 10 days nightly, into the private cache.
  - Splits/bonuses: Yahoo's split factors are applied only if the data shows Kite is unadjusted.
  - Dividends: the same total-return adjustment as before.
  - `SWING_PRICE_SOURCE=kite` makes every price read use Kite first.
- **Once 90% complete, all automatic:**
  - `journal/kite_data_audit.md` (Kite vs Yahoo, close by close);
  - `journal/kite_recheck.md` (top-300 next-open, top-300 3:20 pm buy and all-stocks trade sets rebuilt on Kite prices, side by side with Yahoo, after costs and tax);
  - a Telegram note to the owner;
  - from then on, the weekly automatic research (lab, context engine, Foundry) runs on Kite prices.
- **Live tips** stay on the current price feed until the audit is read. Live quotes during the day are already Kite.
- **The owner's account value:** the owner said yes to reading it for sizing. Adding code that reads the broker account (funds/holdings) was blocked by this session's safety controls, so it was not built. `/capital` monthly remains the way.

## D155 - 2026-11-19 - KITE FIRST everywhere, and every report says which data it used (owner: "Kite Connect is what we are paying - use it")
- `data_prices.load()` now reads **Kite exchange prices first** for every stock, live and in tests. Yahoo is used only for days or stocks Kite has not given yet: before the nightly Kite download completes, and for stocks not on Kite. `SWING_PRICE_SOURCE=yahoo` forces the old source, for comparisons only.
- **Today's bar for every NSE stock** comes from Kite quotes at the 4 pm review and before the 6:40 pm nightly job (`kite_daily.todays_bars_from_quotes`, about 6 requests for all stocks).
- **History:** Kite daily since 2011 (about 2 nights to complete), 15-minute since 2019, and 5-minute around the open and 3:20 pm (D153/D154). Delisted stocks: NSE official bhavcopies. Kite does not list them.
- **Provenance in every report:** `data_prices.provenance_line()` adds "Data used: daily prices of N stocks - Kite only / Kite + Yahoo / Yahoo only" to the Learner, why-log, weekly automatic research, Foundry record and Kite re-check. Claude's answers to the owner state the data source every time.

## D156 - 2026-11-19 - Everything re-run on Kite data (owner: "do all work again ... with Kite Connect data")
- `vantage-ai/validation/kite_rerun_all.py` (daemon job `kite_rerun`, after the research job, once Kite daily history is 90% complete):
  - rebuilds every price-based input from Kite exchange candles: VANTAGE top-300 next-open, 3:20 pm buy, all stocks, live dip-buy trades, market-mood calendar, ADD MORE paths, the 40 facts per trade;
  - re-runs 19 steps: luck checks, fingerprint, rounds 21 / 24-29, real costs + tax, NIFTY on identical terms, auto-lab steps 1-2, context engine, strict groups, Strategy Foundry;
  - writes results to a separate folder, so Yahoo vs Kite sit side by side in `journal/kite_rerun.md` (results only, no prices), and tells the owner on Telegram.
- **Tonight the Kite daily download has no nightly limit** (until complete, about 3 requests a second). Every test script is now portable (no machine-specific paths) and can run in the re-run folder (`ATLAS_RUN_DIR`). A Kite re-run never replaces the live behaviour-group model.
- Kite does not list delisted stocks; those stay on NSE official bhavcopies, and the report counts them.

## D157 - 2026-11-19 - Tonight's re-run switched to STRICT KITE mode (owner's yes and 7 rules)
- `SWING_PRICE_SOURCE=kite_strict` (`data_prices.load` + `kite_daily.frame_strict`):
  - listed stocks come from Kite historical candles only. A stock or day Kite does not have is never filled from Yahoo; it is recorded as missing.
  - Delisted stocks come from NSE official bhavcopies, labelled 'nse'.
  - Splits/bonuses: none if the data shows Kite is already adjusted; otherwise detected from Kite's own prices (clear ratios only; the audit flags anything missed).
  - Price-only (no dividends), NIFTY too, so NIFTY comparisons are like-for-like.
- **Step 0 of the re-run verifies coverage first** (`journal/kite_coverage.md`): every NSE stock and every past top-300 member, on Kite or not, date range, missing stock-days, and whether 13 years are really there.
  - The Kite-vs-Yahoo audit (`journal/kite_data_audit.md`) is the only place Yahoo is used: verification.
  - With no Kite history, the run stops and claims nothing (rehearsed).
- **Every experiment records its data** (`ATLAS_PROVENANCE_FILE`): Kite stocks, stocks not on Kite, Yahoo stocks (must be 0), date range and corporate-action method, shown per step in `journal/kite_rerun.md`.
- The Kite re-check and the weekly automatic research also use strict mode once Kite history is complete.
- **Yahoo-based results preserved** unchanged in `vantage-ai/validation/yahoo_baseline/` (18 result files) for the side-by-side comparison.
- **Not changed (needs the owner's approval):** live tips still read prices Kite-first with Yahoo filling gaps (D155); live trading rules; strategies.

## D158 - 2026-11-20 - Live tips and alerts are KITE ONLY (owner: "no live tip can silently use Yahoo")
- **Price history** for every live strategy (VANTAGE, live engine, Foundry, basket, the forwarded-tip checker): `data_prices.load` is strict Kite by default. No Kite candles means nothing; Yahoo only with an explicit `SWING_PRICE_SOURCE=yahoo` comparison run (`yahoo_allowed()`).
- **Live prices:** `kite.live_prices` has no Yahoo fallback. The live engine's "not logged in, use Yahoo for open tips' stops" path was removed.
- **Blocked Yahoo downloads:** intraday scanner (5-minute), hourly scan snapshot, F&O 5-minute fallback, the forwarded-tip checker's live price, and alerts on Indian index tickers.
- **No Kite means no tip, and the owner is told:** `kite.report_unavailable()` sends one Telegram note a day per job, and work resumes by itself once Kite data is back. It covers:
  - the VANTAGE 3:40 pm scan, VANTAGE live alerts and the evening VANTAGE scan;
  - the evening tips;
  - the live engine;
  - the 3:22 pm plan, which says "No trade today - Kite price data is not complete" instead of the risk sentence.
- VANTAGE and the evening tips wait until Kite history covers 90% of stocks.
- **Proof** (`tests/test_no_yahoo_in_live.py`, 23 checks):
  - static: every Yahoo call in 20 live modules must sit behind the `yahoo_allowed()` guard; 4 such calls found and guarded, and a deliberately unguarded call is caught;
  - dynamic: with Yahoo made to fail and no Kite data, history, live prices, the hourly snapshot and the tip checker return nothing, and VANTAGE sends no tip and reports.
- **Kite downloads** got their own job (`kite_download`, weekdays from 6:55 pm, right after the nightly job), because on 19 Nov the research job found no valid login at 8:17 pm and later hit its time limit.
- **Research** runs nothing price-based until Kite history is complete. The weekly research run of 19 Nov 8:39 pm used mixed Kite+Yahoo data; it is marked INVALID in `journal/auto_research.md` and `lab_rules.json`, kept for the record. It made no proposals.
- **Unchanged:** every entry, exit, ranking, confidence and risk rule.
- **Still on Yahoo, not tips or prices for tips:** company fundamentals and results dates (Kite has none), global markets (non-Indian), the Yahoo comparison copies, and `kite_is_adjusted()`, which uses Yahoo split dates only to verify whether Kite's candles are already split-adjusted (the prices stay Kite).

## D159 - 2026-11-20 - Everything Kite has: the full candle library; delisted stocks out of research (owner 20 Nov)
- **Delisted stocks are left out of all research** (owner: "remove delisted and suspended stocks' history"). `independent_validation._delisted()` returns nothing unless `ATLAS_INCLUDE_DELISTED=1` (kept only for a one-off comparison). Reports now say "delisted stocks left out". Honest effect: stocks that later failed are missing, so backtest results can look a little better than reality (survivorship). The old NSE bhavcopy files stay on disk unused (nothing deleted).
- **Expired F&O contract history: not collected** (Kite does not keep it and the owner does not want it).
- **Daily candles (`kite_daily`)**: every NSE stock + NIFTY 50 + NIFTY BANK + INDIA VIX, from 2000-01-01, or as far back as Kite has. Stocks first downloaded from 2011 are read further back (`backfill`) until Kite returns nothing.
- **Intraday candles (`kite_candles`, new)**: current top-300 + NIFTY 50 + NIFTY BANK:
  - 60-, 15- and 5-minute: all Kite has (read backwards from today until two empty chunks);
  - 1-minute: the last 2 years, then kept going forward;
  - 3-, 10- and 30-minute are built exactly from the 1-, 5- and 15-minute files (no extra requests);
  - parquet files in the private GitHub cache (`data/kite_candles/`), never in git; `journal/kite_candles.md` reports progress, the earliest day per interval, stocks not on Kite, and size.
- **When**: the `kite_download` job now runs in ~10-minute chunks whenever the day's Kite login is valid, any day, but **never 8:45 am - 3:50 pm on weekdays**. Jobs run one at a time, so live scans, the buy window and VANTAGE always come first. Daily history first, then intraday. It repeats every minute until complete, then tops up once a day.
- **Safety**: read-only Kite historical API only (no order endpoints); about 3 requests a second; downloads pause if the data folder passes 4 GB (GitHub keeps 10 GB of cache in all). Estimated ~37,000 requests (~3.5 hours) and ~1.4 GB in total.
- **New package**: `pyarrow` (free, open source) for parquet files.
- **Unchanged**: every live entry, exit, ranking, confidence and risk rule. The full re-run of all backtests on Kite starts only when daily history is complete (coverage report first, then results vs the Yahoo baseline); any live change waits for the owner's yes.

## D160 - 2026-11-20 - Company financials come from NSE filings, not Yahoo (owner 20 Nov)
- **New `swing/nse_financials.py`** reads each company's own annual results from NSE (free, public, read-only):
  - the annual-results list (2019-2024 XBRL files) and, from 2025, NSE's "integrated filings" (the year-end quarter's file holds the full year and the balance sheet);
  - from each official XBRL file: sales, profit (owners' share), profit before tax, finance costs, operating cash flow, capital spending, EPS, total assets, current assets and liabilities, equity, borrowings, and share count;
  - promoter holding from the latest shareholding-pattern filing;
  - industry and name from NSE's Nifty-500 list.
- **Point-in-time is now exact**: a year counts only from its REAL filing date, not "period end + 60 days".
- **Consolidated** figures when filed, else standalone (marked on each year). Parsed files are cached by NSE's filing number, so each is read once.
- **P/E, P/B and market value** come from the latest **Kite** close × the filed share count. If Kite has no price, they stay empty (strict Kite).
- **Never mixed**:
  - NSE failing keeps the last NSE copy, never a Yahoo one;
  - old Yahoo snapshots are ignored and refetched;
  - the lifelong store keeps Yahoo years apart (`_other_source`), and company research only joins years of the same source;
  - the old Yahoo reader stays as `fetch_fundamentals_yahoo` for comparison only; nothing live calls it.
- **Checked** on TCS, Reliance, HDFC Bank, Dixon and IRFC against the published results (e.g. TCS FY24 sales ₹2,40,893 crore, Dixon FY25 ₹38,860 crore).
- **Honest limits**:
  - about 7 years per company (NSE has no XBRL before ~2019);
  - banks' older files use another layout, so fewer years and no equity figure;
  - NSE filings have no "gross profit" or business description, so those stay empty, and the Piotroski "gross margin" test counts as not passed.
- **Same rules**: the quality screen's thresholds are unchanged (loss-making, debt/equity > 2, negative equity or cash flow, P/E > 120). Only the data source changed, which can change which tips the screen removes.
- **Still Yahoo, not financial statements**: results DATES and the EPS-surprise history. Moving them to NSE's board-meeting calendar is the next step.

## D161 - 2026-11-20 - The full re-run waits for ALL Kite daily history (owner: "once we get all ... then start backtests")
- `kite_daily.history_complete()`: every stock is up to date AND read back as far as Kite goes.
- The full re-run of every past backtest (`kite_rerun`, all 19 steps, strict Kite, delisted left out, compared with the preserved Yahoo baseline), the weekly research and the Kite re-check start only when it is true. Weekends are allowed for the re-run.
- The download job is now the lowest-priority daemon job: every other job (re-run, research, nightly, basket, weekly) goes first.
- The re-run report shows the data coverage first, then the results. Nothing live changes without the owner's yes.

## D162 - 2026-11-20 - ATLAS rebuilt from zero (owner: "remove all other things... we will rewrite everything from start")
- **Removed** (git history keeps the code):
  - VANTAGE (indicator, Pine files, every scan and alert), RCP, dip-buy, breakout, pullback;
  - the live engine, evening tips, intraday paper trading, F&O tips, basket, company of the day;
  - the forwarded-tip checker, chart reader, morning brief and filings alerts;
  - the Foundry, the lab and auto-research, the old Learner and why-engine, scorecards;
  - every old research script and result, all old documents (~600 files);
  - Yahoo from the code and requirements.
- **Old data on GitHub's cache** is deleted once by `swing/reset.py`: Yahoo prices, NSE bhavcopy rebuilds, delisted stocks, old research data, quote-built daily files.
  - Kept: Kite candles already downloaded, the Kite login pass, the Telegram message position, NSE filings.
  - Old personal records (old tips, VANTAGE signals, trades) are moved to `data/private/old_system`, not deleted, until the owner says so.
- **Kept**: Kite login and read-only data access, Telegram, the always-on runner and keep-alive, the kill switch, Zerodha costs, NSE company financials (D160, not used by anything yet).
- **New**:
  - candle library for EVERY NSE stock at 1 day, 60, 15, 5 and 1 minute, all Kite has (3/10/30-minute derived);
  - the live streaming feed of every stock with live candles at every interval;
  - the strategy framework with the owner's default 1% stop-loss;
  - the tester (Kite only);
  - the Learner (where, how and why each strategy works or fails; suggestions only);
  - live tips with exit alerts for approved strategies only;
  - bot commands /test /learn /approve /unapprove /stop /resume.
- **Sizing unchanged**: at most 1% of capital lost at the stop and at most 25% of capital in one position. With a 1% stop the 25% cap decides (₹12,750 of ₹51,000, max loss ≈ ₹128 before costs).
- **Storage limit**: the free GitHub cache holds 10 GB per repository. Downloads pause at 4 GB and the owner is shown "storage limit reached". All NSE stocks at 1-minute for every year Kite has will very likely not fit; where to keep more is the owner's decision (anything paid needs his approval).
- **Live feed**: Kite WebSocket, read-only. Quote mode, IST receive time for the minute; the evening download replaces today's live candles with Kite's official ones. A new GitHub run during the day refills missed minutes from Kite's own 1-minute candles.
- **Not yet proven on GitHub**: the live feed and the full-market download have only been tested with simulated Kite data here (the Kite keys exist only on GitHub). The first market day is the real check; /status and the 3:45 pm message show it.

## D163 - 2026-11-20 - Old records deleted; Company of the Quarter; GitHub storage used fully
- **Deleted on GitHub** (one-time `reset.py`, version 3; the owner: "delete my personal records and NSE company financials"):
  - the old personal records (old tips, VANTAGE signals, trades, forwarded tips);
  - the old company-financials store;
  - everything else of the old system.
  - Kept: Kite candles and the Kite login.
- **Company of the Quarter** (owner: "company of the day, but one company once a quarter"):
  - one pick per calendar quarter, at 6:30 pm on the first weekday of Jan/Apr/Jul/Oct (the first as soon as 80% of companies have been read);
  - scored 0-100 from each company's own NSE annual filings (quality, growth, financial health, cash, valuation from the Kite price, health checks);
  - red flags remove a company; no repeat within 4 quarters; picks recorded in `results/company_picks.csv`.
  - The NSE filings reader stays only for this pick (`company_filings.py`); nothing else uses company data.
- **GitHub storage**:
  - every run used to save a full new copy of the data (each copy counts toward GitHub's 10 GB). Now each run deletes the older copies after saving its own (`scripts/clean_caches.py`);
  - GitHub's computer also deletes ~25 GB of unused preinstalled tools first, so there is disk room;
  - limit raised from 4 to 8.5 GB of data.
- **Measured**: 1-minute candles take ~1.3-1.6 MB per stock per year, so every NSE stock at 1-minute for every year Kite has is ~25-35 GB, which no free GitHub storage holds. Day, 60, 15 and 5-minute for all stocks (~6-8 GB) should fit. The download order (day → 60 → 15 → 5 → 1 minute) means nothing is lost while the owner chooses where 1-minute history lives.
- **Correction (same day)**: GitHub runs the workflow file of the `main` branch, so the two new workflow steps would never have run. Both moved into code that does run from this branch:
  - `keep_alive.py` deletes every older saved copy except the newest, before this run saves its own;
  - the daemon frees ~25 GB of unused tools at the start of each run.
  - The workflow file on this branch is again identical to `main`.
  - A manual "Run workflow" must use the task `bot`; the old default `nightly` script no longer exists.

## D164 - 2026-11-20 - Kite history kept for our use until the subscription ends; 1-minute history skipped for now
- **Owner's decision** after the data-policy check: download everything decided, keep it in GitHub's private storage for our own research and tests, and delete it when the Kite subscription ends (Kite terms clause 9(b)). Never published.
- **Known risk, accepted by the owner**: Kite terms clause 4(b) says no databases or permanent copies "unless expressly permitted by Zerodha". Written permission from kiteconnect@zerodha.com would remove that risk.
- **1-minute history is not downloaded** for now (owner: test on everything else first; add 1-minute only if tests show it helps). History downloads: day, 60, 15 and 5-minute for every NSE stock.
  - The live feed still builds 1-minute candles during the day: they are needed for exit alerts and live 3/5/10-minute candles.
  - Strategies on 1- or 3-minute candles cannot be tested until 1-minute history is added.

## D165 - 2026-11-20 - Practice trader: ₹50,800 of pretend money, Kite prices, goal ₹10,000+ a day (owner's experiment)
- **Owner**: "you decide, earn ₹10,000 a day, losses are okay - it is an experiment". The owner is told this is ~20% a day and cannot be promised.
- **No real order is ever placed.** Kite terms 2(e) say no fully automated trades, and SEBI's retail-algo rules need a registered algo and a fixed IP. The owner places trades himself, from the instant Telegram messages.
- **Rules (my choice, `swing/autotrader.py`)**:
  - NIFTY weekly options (at-the-money):
    - entry: a 5-minute close beyond the 9:15-9:30 range, with the 20-candle trend and the day's open;
    - stop -30% of the premium, target +60%, stop to the entry at +30%;
    - at most 2 trades a day, about ₹3,000 at risk each.
  - Intraday stocks (the day's 100 most-traded):
    - entry: a range breakout with 1.5x volume, on the VWAP side;
    - stop 1%, target 2%;
    - at most 3 trades a day and 2 at a time, about ₹1,500 at risk each.
  - Day limits: stop new trades at +₹10,000 net or -₹7,500; everything sold by 3:15 pm.
- **Real charges** (Zerodha options and intraday) plus slippage; MIS margin 20%; options need the full premium.
- **Replay**: once, on the last 5 market days (Kite 1-minute candles of NIFTY, every NSE stock and the options used), with 5 dashboards on Telegram one by one plus a summary.
  - Limit: Kite has no expired option contracts, so on those days the next listed expiry is used (said on the dashboard).
- **Live** from the next market day, on the streaming feed:
  - every entry and exit goes instantly to Telegram;
  - the dashboard picture (Zerodha's 'Closed positions' layout) after 3:30 pm.
- **Not tested on long history yet**: the stock rule can be, once the 5-minute library is complete. The option rule cannot (Kite has no expired option candles), so only the replay and live results judge it.

## D166 - 2026-11-20 - NSE holidays (owner: "Tuesday 24 Nov 2026 is a holiday, so the weekly expiry is on Monday")
- `swing/market_days.py` reads NSE's official trading-holiday list (confirmed: 24 Nov 2026, Prakash Gurpurb Sri Guru Nanak Dev), with a built-in copy of the 2026 holidays if NSE cannot be reached.
- On a holiday: no Kite login message, no live feed or practice trading, and history downloads may run all day.
- The weekly expiry moving to Monday needs no code: option contracts and their expiry dates come from Kite's own NFO list. On expiry day after 1:30 pm the trader uses the next weekly expiry.

## D167 - 2026-11-20 - Weekend long test; 15-minute and 1-hour candles built from 5-minute
- History downloads are now day + 5-minute only. 15-, 30- and 60-minute candles are built exactly from Kite's 5-minute candles (aligned to 9:15). Same data, ~9 hours less downloading, less storage.
- **Long test** (`swing/longtest.py`), runs by itself once 5-minute history is complete, outside market hours.
  - **Stocks**: the live opening-range rule on every day of Kite 5-minute history, with the same top-100 universe, limits, sizing, charges and slippage. 72 settings tried:
    - volume 1.5/2x;
    - last entry 11:30/13:00;
    - long+short or long only;
    - stop 0.75/1/1.5%;
    - target 1.5/2/3%.
  - **NIFTY options** as an ESTIMATE on NIFTY's 5-minute candles (premium 0.35% of NIFTY, delta 0.5, no time decay). Kite has no candles of expired options. 18 settings.
  - **Fair check**: settings are chosen on the years before 2024, and 2024 onwards is shown separately; a setting is used only if it also wins there.
  - The fast exit maths equals the step-by-step rules on 300 random cases (test).
- **Weekends/holidays**: one Kite login message a day at 9 am while history is incomplete (downloads need the day's login).

## D168 - 2026-11-20 - Extra factors tested, winners switched on by the system (owner: "you have freedom; make the most profit; goal ₹10,000 a day")
- **Long test factors**, each tried INSIDE the signal (it waits for the first breakout that passes them), alone and in 13 combinations, on the live stock setting with all 9 stop/target pairs:
  - beyond yesterday's high/low (support/resistance);
  - NIFTY moving the same way;
  - stronger than NIFTY today;
  - India VIX below 20;
  - no resistance (yesterday's high/low) within 1%.
- **NIFTY options**: beyond yesterday's high/low, VIX below 20, and both, on all 18 settings (estimate).
- **Switching on**: a setting replaces the live one ONLY if it wins both before 2024 (where it was chosen) and in 2024 onwards, with a recent worst fall at most 1.5x deeper. Winners are written to `data/practice_params.json`, and the live practice trader uses them from the next start. The Telegram summary says what changed.
- **₹10,000 a day**: the report shows how many times today's risk per trade would be needed to average ₹10,000, against what ₹50,800 allows (~1.6x stocks, ~4.8x options), with losses growing by the same factor. Raising the risk is NOT switched on by itself; it is shown for the owner.

## D169 - 2026-11-20 - Every interval downloaded from Kite as it is (owner: "download 5, 15, 30, 1 hour and 1 day separately")
- Replaces the D167 shortcut. Download order: day (done), 5-minute (the tests need it), then 60, 30 and 15-minute. All are Kite's own candles; only 3- and 10-minute would be built.
- Storage: all of these together are estimated at ~9-10 GB against the 8.5 GB limit. If the limit is reached, the last one (15-minute) pauses and the owner is told.
- Weekend/holiday Kite login message moved from 9 am to 6 am (owner: "don't want to waste 3 hours" - a login lasts until 6 am the next day).
- /proof (owner 20 Nov: "what's the proof you traded honestly?"): every practice trade (replay or live) as a CSV with exact entry/exit times, buy/sell prices and reason, so each can be checked on Kite's own 1-minute chart.
- Intraday stock margin in the practice account: 25% (4x) instead of 20% (5x) - owner noticed a ₹1.5 lakh trade on ₹50,800; Zerodha gives up to 5x only on the most liquid stocks, so the cautious figure is used (practice trader and long test).

## D170 - 2026-11-21 - Kite's margin calculator allowed (owner, in writing: "Yes, allow Kite's margin calculator (/margins/orders)")
- `kite.order_margin()` / `kite.mis_ratio()`: Kite's margin CALCULATOR, the only Kite address besides market data and the daily login. It computes the margin for a hypothetical order and places nothing.
- The practice trader uses Zerodha's own intraday margin per stock, once a day per stock. If Kite cannot say, the cautious 25% is used. Each entry message shows the margin used.
- The safety tests allow ONLY this exact address. Every order, GTT, holdings, positions and funds address stays blocked, and a new test checks this.
