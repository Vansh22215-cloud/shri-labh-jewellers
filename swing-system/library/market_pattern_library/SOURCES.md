# Sources and implementation references

These references are starting points for canonical formulas and taxonomy cross-checks. They do not establish that any signal is profitable. Preserve implementation/version details when parity matters.

- TA-Lib Functions: https://ta-lib.org/functions/ — widely used canonical function catalogue spanning momentum, overlap, volatility, volume, statistics, price transforms and cycle functions.
- TA-Lib Candlestick Outputs: https://ta-lib.org/api/candlestick-outputs/ — candlestick recognition output conventions; detections are descriptive and need context/confirmation.
- Pandas TA Classic: https://xgboosted.github.io/pandas-ta-classic/indicators.html — broad indicator catalogue and Python implementations; function availability and defaults can change by release.
- Tulip Indicators: https://tulipindicators.org/list — compact independent library of technical indicators useful for cross-checking.
- QuantConnect LEAN indicator reference: https://www.quantconnect.com/docs/v2/writing-algorithms/indicators/supported-indicators — implementation-oriented catalogue and supported indicator/pattern classes.
- StockCharts ChartSchool chart patterns: https://chartschool.stockcharts.com/table-of-contents/chart-analysis/chart-patterns — classic chart-pattern taxonomy and context.
- TradingView All Chart Patterns: https://www.tradingview.com/support/solutions/43000706927-all-chart-patterns/ — common automated classic formations.
- TradingView candlestick pattern detection: https://www.tradingview.com/support/solutions/43000584462-candlestick-patterns/ — common candlestick family reference.

## Definition policy

A source name alone is insufficient. For each implemented function/pattern, record exact formula, code source/version, parameters, seed/warm-up, price input, adjustment policy, session rules and reference test vectors. Community concepts such as Elliott Wave, Wyckoff phases, harmonic variants, ICT/SMC blocks, profile patterns and Gann methods often have multiple non-equivalent definitions; the local detection rule is a research convention, not a claim of universal authority.

## Data requirements

OHLCV can support many conventional indicators, but not true order-book imbalance, iceberg inference, aggressor-side delta, options surface analytics, TPO profile or official auction imbalance. For such records, mark the required data capability and skip when unavailable rather than manufacturing proxy values.
