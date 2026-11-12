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
