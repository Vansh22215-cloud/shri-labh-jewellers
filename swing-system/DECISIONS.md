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
