# Claude Code Handoff — Market Research Library v2.0.0

You are building an autonomous **research and backtesting system**, not an automatic live-trading bot. Start by treating this folder as a catalogue of candidate hypotheses.

## First action

Read `README.md`, `manifest.json`, `signal_schema.json` and `research_engine_contract.json`. Load all five item catalogues and `aliases.json`. Validate JSON schemas, duplicate IDs, unresolved aliases, missing required fields and references. Create a machine-readable validation report.

## Catalogue counts

- Chart patterns: 148
- Candlestick patterns: 130
- Technical indicators: 324
- Market structure/liquidity events: 85
- Quant research features: 104

## Required architecture

1. `data/`: vendor adapters, point-in-time symbols/universes, OHLCV, corporate actions, derivatives and optional specialist feeds.
2. `catalogue/`: load JSON records, canonical IDs, aliases, versioning and capability flags (`ohlcv`, `intraday`, `options`, `order_book`, `breadth`).
3. `indicators/`: deterministic feature implementations with unit tests and reference parity where available.
4. `detectors/`: event/pattern recognition with `first_knowable_at`; no future pivots or unfinished higher-timeframe candles.
5. `strategies/`: combinable rules but avoid brute-force unrestricted Cartesian products. Use a predeclared hypothesis search space.
6. `backtest/`: event-driven execution, realistic fill rules, fees/taxes, spread, slippage, market impact, lot/tick size and exchange sessions.
7. `validation/`: chronological train/validation/test, nested walk-forward, robustness, multiple-testing accounting and untouched holdout.
8. `experiments/`: immutable run metadata, code commit, parameters, data versions, all outcomes including failures.
9. `scheduler/`: daily ingestion, quality checks, feature refresh, evaluation, reports and alerts.
10. `dashboard/`: net-of-cost leaderboard with trade count, confidence intervals, drawdown, stability and regime breakdowns.

## Prioritise implementation

**Phase A — OHLCV core:** classic chart formations, TA-Lib candlestick recognisers, common moving averages, RSI/MACD/ADX/ATR/Bollinger/Donchian, volume and basic volatility.

**Phase B — structure:** confirmed pivots, HH/HL/LH/LL, BOS/CHoCH, range breaks, gap/FVG, liquidity sweeps and session references. All need point-in-time confirmation.

**Phase C — quantitative context:** returns, normalisation, volatility regimes, relative strength, breadth and cross-asset features.

**Phase D — specialist feeds:** options IV/Greeks/skew, volume profile/TPO, order book, signed trades, futures basis/open interest and auction imbalances. Do not fake these from OHLCV.

## Acceptance tests

- Every detector output has canonical ID, rule version, parameters, instrument, timeframe, event timestamp, first-knowable timestamp and data version.
- No signals use unfinished bars, future data, survivorship-biased universes or retrospective anchors.
- Indicator output matches a documented implementation on test vectors; warm-up and missing-value rules are tested.
- Backtest fills occur after the signal could be known and respect trading hours, liquidity and execution costs.
- Final holdout is untouched by model/parameter selection.
- Every experiment is saved; failed experiments are not deleted.
- Leaderboard ranks net-of-cost out-of-sample robustness, not in-sample win rate alone.

## Important

Do not claim this is literally every pattern ever published. Names and definitions differ by school/platform. Ask the owner before introducing a new definition that conflicts with an existing ID. Keep variants separately versioned. Never recommend live trades or enable brokerage execution until paper-trading, operational risk and explicit approval requirements are met.
