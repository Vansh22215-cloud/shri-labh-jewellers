# Claude Code handoff: ingest this reference library

Use this folder as the initial source-of-truth catalogue for the trading research project.

## Required behaviour

1. Load `manifest.json`, `chart_patterns.json`, `candlestick_patterns.json`, and `indicators.json` without dropping fields.
2. Preserve each stable `id`, `canonical_code`, category, formula description, detection outline, confirmation rule, invalidation rule and caveat.
3. Build an internal registry from the JSON records. Do not hard-code a second, divergent catalogue in source files.
4. For any TA-Lib `canonical_code`, prefer the canonical TA-Lib implementation and verify numerical parity. Do not pretend that a prose description is an exact formula where it says to use a canonical implementation.
5. For non-standard patterns, turn each heuristic into a deterministic, configurable rule and stamp the exact rule version. Keep variants separate.
6. Implement detectors as event-time systems: signals are emitted only when all required bars are closed and all pivots are confirmed. Never backdate an event to a pivot that was only knowable later.
7. Add tests for boundary conditions, missing data, zero-range candles, corporate actions, session gaps, timezone/session resets and warm-up periods.
8. Before any strategy testing, create a rule audit report showing: catalogue item, implemented/not implemented, code reference, parameters, tests, known limitations and exact formula/variant.
9. Do not silently skip catalogue entries. Mark each as `implemented`, `not_applicable_to_dataset`, `blocked_by_data`, or `not_yet_implemented` with a reason.
10. Do not make profitability claims from detector unit tests. Predictive testing belongs to a later, separate backtesting stage with realistic costs and out-of-sample validation.

## Important distinctions

- A pattern detector describes price structure; it is not automatically an entry signal.
- A confirmation rule is not the same as an entry execution rule.
- A price target derived from a pattern is a conventional projection, not an expected return guarantee.
- Higher-timeframe data must be aligned from the last fully closed higher-timeframe candle only.
- If data is OHLCV-only, do not claim true bid/ask aggressor volume, order-flow delta or footprint accuracy.

## First implementation milestone

Build a catalogue browser/API and detector registry first. The first milestone is complete only when every record can be loaded, validated, queried by category/id, and reported in the implementation audit. Do not start brute-force strategy combinations until this audit is complete.
