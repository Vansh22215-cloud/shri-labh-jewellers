# Market Pattern & Technical Indicator Reference Library

**Version:** 1.0.0  
**Generated:** 2026-11-04  
**Catalog size:** 52 chart patterns, 69 candlestick patterns, 176 indicators/features.

## What this is

A machine-readable starter reference for a systematic research engine. It contains a broad baseline of widely recognised chart patterns, the 61 TA-Lib candlestick recognisers plus common non-standard candle setups, and a broad indicator/feature set based on TA-Lib plus widely used additions.

It is **not literally every pattern ever named**. Different books, platforms and trading communities use different names and slightly different rules. Every non-standard variant is labelled so Claude Code can preserve it as its own version rather than silently mixing definitions.

## Files

- `manifest.json` — version, counts, sources, global safeguards and signal contract.
- `chart_patterns.json` — structures, deterministic detection outlines, confirmation, invalidation and target models.
- `candlestick_patterns.json` — names, TA-Lib IDs, candle counts, definitions and implementation guidance.
- `indicators.json` — indicator families, definitions, calculation basis, typical parameters and input requirements.

## Critical implementation requirements

1. **Do not trade a label.** Build separate detector, context filter, confirmation, entry, stop, exit and sizing modules.
2. **No look-ahead.** Swing pivots require right-side confirmation bars. A pivot detected at bar `t` with `r` confirmation bars is not tradable until bar `t+r` closes.
3. **No repainting.** Store the exact time the system could first know a pattern existed. Do not backdate it to the first candle or pivot.
4. **Exact indicator parity.** Prefer TA-Lib's canonical implementation for rows with a TA-Lib code. Compare local output against TA-Lib on test vectors before using it in research.
5. **Adaptive candle thresholds.** Candle size and shadow thresholds should be relative to recent ranges/bodies, not fixed rupee/point values.
6. **Version everything.** Any change to tolerance, pivot settings, pattern logic, indicator calculation or confirmation must create a new `rule_version`.
7. **Avoid combinatorial overfitting.** Store every test, account for multiple testing, keep untouched holdout periods and use walk-forward evaluation.
8. **Realistic execution.** Include brokerage, exchange fees, taxes, spread, slippage, liquidity/impact, lot sizes, tick sizes, trading hours, circuit limits and rejected orders appropriate to each instrument/venue.
9. **Separate universes/timeframes.** Test equities, indices, futures, options, FX and crypto separately; do not assume one signal rule transfers across markets.
10. **Treat targets as hypotheses.** Pattern target models are conventional geometry, not validated forecasts. Measure target-hit probability and adverse excursion empirically.

## Suggested JSON loading

```python
import json
from pathlib import Path

root = Path("market_pattern_library")
charts = json.loads((root / "chart_patterns.json").read_text())['items']
candles = json.loads((root / "candlestick_patterns.json").read_text())['items']
indicators = json.loads((root / "indicators.json").read_text())['items']
```

## Recommended detector output

Every detector should emit a record conforming to `manifest.json -> standard_signal_contract`. It should also persist its full parameter set, source data version, code commit, and the first bar on which the signal became knowable.

## Scope and source notes

The TA-Lib catalogue is used as a reproducible technical-function baseline. Its function pages document inputs, outputs and implementation links. The candlestick baseline includes its 61 CDL recognisers. Classic chart structures are cross-checked against StockCharts ChartSchool and TradingView's automated pattern taxonomy. Harmonic, Elliott, Wyckoff and price-action entries are included as configurable rule families because conventions differ substantially across practitioners.

A detector being present in this library does **not** imply that it has predictive value. The purpose of the research engine is to test that claim with out-of-sample data.

## Sources

- TA-Lib functions: https://ta-lib.org/functions/
- TA-Lib candlestick outputs: https://ta-lib.org/api/candlestick-outputs/
- StockCharts ChartSchool chart patterns: https://chartschool.stockcharts.com/table-of-contents/chart-analysis/chart-patterns
- TradingView All Chart Patterns: https://www.tradingview.com/support/solutions/43000706927-all-chart-patterns/
- TradingView candlestick pattern detection: https://www.tradingview.com/support/solutions/43000584462-candlestick-patterns/
- CRAN TA-Lib candlestick vignette: https://www.stat.ethz.ch/CRAN/web/packages/talib/vignettes/candlestick.html
