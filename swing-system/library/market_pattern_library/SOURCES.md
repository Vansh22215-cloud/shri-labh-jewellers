# Source and design notes

This library is a synthesis of public technical-analysis terminology and public software documentation. Formula descriptions are intentionally concise. Where calculation conventions vary or an algorithm is complex, the record directs the implementation to a canonical library or requires the exact chosen variant to be versioned.

The TA-Lib official functions catalogue currently lists the technical-function families used here and links to formulas and language implementations: https://ta-lib.org/functions/.

TA-Lib candle output documentation clarifies that a positive output is bullish, a negative output bearish, zero means no detected pattern, and detection does not itself check trend context: https://ta-lib.org/api/candlestick-outputs/.

StockCharts groups classic chart patterns into reversal and continuation families and explicitly notes that classification may depend on circumstances and can be subjective: https://chartschool.stockcharts.com/table-of-contents/chart-analysis/chart-patterns.

TradingView's automated classic chart pattern list is used as an additional cross-check: https://www.tradingview.com/support/solutions/43000706927-all-chart-patterns/.

Candlestick taxonomy and adaptive body/shadow threshold notes are cross-checked against the CRAN talib vignette describing 61 TA-Lib candlestick recognizers: https://www.stat.ethz.ch/CRAN/web/packages/talib/vignettes/candlestick.html.
