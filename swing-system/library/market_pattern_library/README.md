# Market Pattern & Technical Research Library

**Version:** 2.0.0  
**Generated:** 2026-11-03  

## Catalogue coverage

| Catalogue | Entries |
|---|---:|
| Chart patterns and price formations | 148 |
| Candlestick patterns / variants | 130 |
| Technical indicators | 324 |
| Market structure, liquidity and auction events | 85 |
| Quantitative research features | 104 |
| **Total records** | **791** |

This is a large research catalogue, not a claim that every proprietary, regional, discretionary or renamed pattern in existence has been captured. Many named concepts have conflicting textbook/platform definitions. Definitions are versioned and must not be silently merged.

## Files

- `manifest.json` — version, counts, datasets and global safeguards.
- `chart_patterns.json` — structure, deterministic detection outline, confirmation, invalidation and conventional target models.
- `candlestick_patterns.json` — TA-Lib recognisers plus additional textbook/community variants.
- `indicators.json` — indicators across trend, momentum, volatility, volume, statistics, cycles, breadth, options and market microstructure.
- `market_structure_events.json` — HH/HL/LH/LL, BOS/CHoCH/MSS, liquidity sweeps, FVGs, blocks, profile and session events.
- `quant_research_features.json` — returns, candle anatomy, volume, liquidity, calendar, cross-asset, derivatives and execution features.
- `aliases.json` — common shorthand/name-to-canonical mappings.
- `research_engine_contract.json` — testing, validation, logging and daily-cycle requirements for Claude Code.
- `catalog_index.csv` — flat searchable index across all catalogues.
- `signal_schema.json` — baseline signal record contract.
- `SOURCES.md` — external reference catalogues and implementation notes.
- `CLAUDE_CODE_HANDOFF.md` — implementation brief and first tasks.

## Critical cautions

1. **A pattern name is not an edge.** A catalogue item is a hypothesis/specification, not proof of predictive power.
2. Separate detector, context filter, confirmation, entry, stop, exit, position sizing and fill simulation.
3. **No look-ahead or repainting.** Swing pivots become available only after right-side confirmation bars; higher-timeframe candles only after close.
4. Use point-in-time universes, delisted securities, corporate actions and correct session calendars.
5. Include realistic brokerage, taxes, spread, slippage, impact, lot/tick sizes, liquidity limits, circuits and rejected fills.
6. Do not test every parameter combination blindly. Use predeclared search spaces, temporal validation, multiple-testing controls and untouched holdouts.
7. Save all experiment results, including failures. Version data, code, parameters, costs and rules.
8. Treat Elliott, harmonic, Wyckoff, ICT/SMC, order-block, profile and discretionary formations as definition-sensitive. Record exact chosen convention and confidence.
9. Options IV, order-flow, volume profile and market microstructure items require specialised data; OHLCV proxies are not equivalent.
10. Conventional measured-move targets are hypotheses. Measure outcomes and adverse/favourable excursion empirically.

## Suggested Claude Code build order

1. Load and validate every JSON file; build ID/alias registry and duplicate checks.
2. Implement only deterministic, OHLCV-compatible indicators and patterns first. Add unit tests against reference outputs.
3. Implement point-in-time event logic and first-knowable timestamps.
4. Build a vectorised event-driven backtester with instrument/session/cost models.
5. Add chronological walk-forward evaluation, holdout protection and experiment ledger.
6. Add specialised data adapters for profile, options, breadth, futures and order flow only when data is actually available.
7. Schedule daily runs and publish a leaderboard with sample sizes, confidence intervals and net-of-cost metrics.

## Machine-readable loading

```python
import json
from pathlib import Path
root = Path("market_pattern_library")
charts = json.loads((root / "chart_patterns.json").read_text())["items"]
candles = json.loads((root / "candlestick_patterns.json").read_text())["items"]
indicators = json.loads((root / "indicators.json").read_text())["items"]
market_events = json.loads((root / "market_structure_events.json").read_text())["items"]
features = json.loads((root / "quant_research_features.json").read_text())["items"]
```
