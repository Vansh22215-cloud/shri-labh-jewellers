# ROADMAP.md - 6-month capability plan (worked through by the deep upgrade session every 2 days)

Goal: a wider, smarter, more robust research and trading-signal system - every upgrade built with tests,
validated honestly (walk-forward, untouched holdout, costs, variant counting) and adopted only if it helps.
Each session: pick the FIRST unchecked item, build it, test it, record the result here and in CHANGELOG.md,
send a Telegram summary. Mark items [x] done or [~] built-but-did-not-help (keep the code, note why).

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
