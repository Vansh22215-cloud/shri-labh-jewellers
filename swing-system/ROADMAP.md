# ROADMAP.md - capability plan, COMPRESSED TO ONE MONTH (target: done by 2026-12-03)

Worked through by: hourly improvement sessions (weekdays 16:53-23:53, weekends 08:53-23:53 IST), the daily deep
upgrade (21:47) and the daily research session (20:17). 'Month N' below now means 'Week ~N' of the month.

Goal: a wider, smarter, more robust research and trading-signal system - every upgrade built with tests,
validated honestly (walk-forward, untouched holdout, costs, variant counting) and adopted only if it helps.
Each session: pick the FIRST unchecked item, build it, test it, record the result here and in CHANGELOG.md,
send a Telegram summary. Mark items [x] done or [~] built-but-did-not-help (keep the code, note why).


## MISSION (set by the owner 2026-11-03)
Give the best trades one can find, every day: learn from the best-known traders, funds and research, combine the
best of all of them into OUR own system, keep only what proves itself on data, and run on its own.


## INTELLIGENCE DESK (owner's institutional brief, 2026-11-03) - see ARCHITECTURE.md
- [x] I1. (2026-11-03: built - daily NSE participant OI since 2013, 'Big money' line in every message, nightly update; idea R12 queued) FII/DII/Pro/Client positioning from NSE participant-wise OI (daily history) -> regime feature + report.
- [x] I2. (2026-11-03: built - daily NSE F&O bhavcopy summary from Jul 2024: build-up type, PCR, max pain, call/put OI walls, real expiry dates; shown on trade cards; options checker uses real expiries) F&O end-of-day data (futures + options bhavcopy): OI build-up (long/short build-up, unwinding), PCR,
      max pain, implied volatility per stock -> features + "options view" in each trade card.
- [ ] I3. Global markets overnight (US, Asia, crude, USD/INR, US yields, gold) -> pre-market risk line + feature.
- [ ] I4. News & announcements: headlines (RSS) and NSE/BSE corporate announcements, matched to stocks;
      Claude summarises/flags them in sessions; shown as "news check" on trade cards.
- [ ] I5. Economic/event calendar (RBI, Budget, CPI, Fed, results season) -> abnormal-day flags.
- [ ] T1. Trade card upgrade: T1/T2/T3, calibrated probability of T1-before-stop with sample size, confidence
      score, invalidation conditions, expected holding period from history.
- [ ] T2. Daily loss limit + abnormal-market detector (VIX spike, big gap, data outage) -> no new trades.
- [ ] UI1. DASHBOARD: phone-friendly web dashboard (published Artifact) refreshed after every scan: market
      overview, ranked opportunities, interactive charts, open trades & risk, performance analytics, research log.
- [ ] A1. Performance analytics: per strategy / per regime / per month: win rate, avg R, P&L, drawdown, Sharpe,
      after tax; mistakes review ("why did losers lose").

## Week 1 PRIORITY - Strategy library: the best-known methods, each built and tested on NSE data
Each becomes a family in swing/families.py (with tests), joins the walk-forward search, and is pre-registered.
- [x] (built+tested 2026-11-03, see CHANGELOG) S1. Mark Minervini "Trend Template" + VCP (volatility contraction pattern) breakouts.
- [ ] S2. William O'Neil CANSLIM-style: new highs + earnings growth + relative strength (uses fundamentals).
- [x] (built+tested 2026-11-03, see CHANGELOG) S3. Stan Weinstein Stage Analysis: buy only stage-2 breakouts above the 30-week average.
- [x] (built+tested 2026-11-03, see CHANGELOG) S4. Nicolas Darvas boxes: breakouts from tight boxes near highs with volume.
- [x] (built+tested 2026-11-03, see CHANGELOG) S5. Jegadeesh-Titman / AQR cross-sectional momentum (12-1 month), monthly top-decile rotation.
- [x] (built+tested 2026-11-03, see CHANGELOG) S6. George & Hwang 52-week-high momentum (stocks closest to their 52-week high).
- [x] (built+tested 2026-11-03, see CHANGELOG) S7. Post-Earnings-Announcement Drift (Ball & Brown; widely used by quant funds): buy strong results gaps.
- [x] (built+tested 2026-11-03, see CHANGELOG) S8. Larry Connors short-term mean reversion (RSI(2), %b) in uptrends - already partly done, extend.
- [x] (built+tested 2026-11-03, see CHANGELOG) S9. Antonacci dual momentum / Faber sector rotation using NSE sector indices.
- [ ] S10. Quality + momentum (AQR "quality minus junk" idea) using fundamentals as a filter.
- [ ] S11. Turtle/Donchian trend following with volatility sizing (Richard Dennis) - extend existing.
- [ ] S12. "Best of all" META-SYSTEM: every evening rank each family by its recent walk-forward performance
      (only past data), and give the top trades from the top families, with risk score 1-10. This becomes the
      daily "best trades" list once it beats the single-strategy a1 in walk-forward testing.
- [ ] K1. (If the owner buys Kite Connect) Kite integration: daily login via Telegram, live quotes and minute
      history for intraday research; the code NEVER calls order APIs.

## Month 1 - Better data = better decisions
- [~] D1. (2026-11-03: built - 13 yrs of delivery data, delivery_breakout family, delivery filter; neither beat a1: 4.3-4.6%/yr vs 9.2%) Delivery % from NSE full bhavcopy (DELIV_PER): store history; new factor "high delivery breakout"
      (genuine buying vs speculative intraday volume). Add family + proposal.
- [ ] D2. Sector indices strength (NIFTY IT/BANK/AUTO/...): sector-rotation family (buy leaders of the
      strongest 2-3 sectors).
- [ ] D3. Results-reaction study: post-results drift (stocks gapping up on results with volume tend to keep
      drifting) - new family using historical results dates.
- [ ] D4. Bulk/block deal history as a signal (large investor buying) - collect daily, test after 3 months.
- [ ] D5. Data-quality dashboard in the report (coverage, quarantine, staleness per source).

- [ ] D6. Market-event calendar (Union Budget, RBI policy, election results, index rebalancing, F&O expiry):
      study how our trades behave around these days; pre-register a "skip entries before big events" test.
- [ ] D7. Execution tracker: compare the price you actually bought/sold at with the planned price, to measure
      real slippage and recalibrate the backtest's cost assumptions.
- [ ] D8. Tax & net-profit tracker: short-term capital gains tax (20%) and all charges per closed trade, so the
      report shows what you really keep.

## Month 2 - Smarter portfolio and risk
- [ ] P1. Volatility-scaled sizing (equal risk per trade already; add portfolio "heat" limit: total open risk <= 4%).
- [~] P2. (2026-11-03: built as max_per_industry; 7.0%/yr vs 9.2% - not adopted) Correlation / sector limit: max 2 open trades in the same industry.
- [ ] P3. Monte-Carlo of trade sequences: probability of a 10%/20% drawdown -> shown in reports.
- [ ] P4. Parameter-stability maps: show the strategy still works when each setting is nudged (robustness, not tuning).
- [ ] P6. Edge-decay alarm: rolling 30-trade live result vs backtest; automatic warning/pause when the live edge
      is statistically worse than expected.
- [ ] P7. Idle-cash tracker: remind to park unused cash in a liquid fund/LIQUIDBEES (the backtest assumes it).
- [ ] P5. Liquidity-based slippage model (smaller stocks = more slippage) in the backtest.

## Month 3 - Combine strategies (ensemble)
- [ ] E1. Signal ensemble: a stock gets points from every family that fires; trade only multi-family agreement.
- [ ] E2. Regime-switching selection: choose the family by market regime using walk-forward only (pre-registered).
- [ ] E3. Multi-timeframe confirmation: weekly trend must agree with the daily signal.

## Month 4 - Machine learning, done honestly
- [ ] M1. Feature store (momentum, trend, volatility, delivery, sector, regime, results distance) per stock-day.
- [ ] M2. Walk-forward ranking model (logistic regression, then gradient boosting): trained only on past years,
      predicts "target before stop"; used as a ranking score. Must beat the rule-based score out of sample.
- [ ] M3. Feature-importance report: what actually drives winners in Indian markets.

## Month 5 - Learn from live reality
- [ ] L1. Calibrate the risk score (1-10) against real outcomes of tips and forwarded tips.
- [ ] L2. Paper-vs-backtest drift monitor with automatic alerts.
- [ ] L3. Tip-source scorecard -> warn about channels whose tips keep failing.
- [ ] L4. Re-test intraday strategies on the larger hourly history collected since Nov 2026.

## Month 6 - Robustness and reach
- [ ] R1. Full re-validation of everything on the extended data; rotate the holdout.
- [ ] R2. Stress tests: 2008/2020-style crashes, gap-down days; worst-case loss per trade.
- [ ] R3. Plain-language monthly "state of the system" report on Telegram.
- [ ] R4. Review of the whole roadmap: keep what worked, remove what didn't, plan the next 6 months.
