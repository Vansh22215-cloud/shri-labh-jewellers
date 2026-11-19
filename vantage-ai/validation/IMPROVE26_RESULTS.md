# Round 26 results (19 Nov 2026): which stocks should VANTAGE scan?

Plan: IMPROVE26_PREREGISTRATION.md (holdout already seen in round 23, so judged by years since 2018 + the known survivorship reason).

| Period (sizing) | Top-300 | All stocks >= ₹2 cr (live now) | Mix (top-300 first) |
|---|---|---|---|
| dev fixed | 18.9% / -17.5% | 23.2% / -17.8% | 22.2% / -16.0% |
| holdout fixed | 14.8% / -20.6% | 7.2% / -27.5% | 7.5% / -29.3% |
| all years fixed | 16.1% / -16.5% | 19.0% / -19.2% | 18.7% / -17.8% |
| dev current | 21.6% / -21.9% | 24.0% / -24.4% | 22.5% / -18.8% |
| holdout current | 16.9% / -20.4% | 8.9% / -25.7% | 8.6% / -25.0% |
| all years current | 19.3% / -21.1% | 20.7% / -26.3% | 19.1% / -23.5% |

Year by year (growth / worst fall, fixed sizing):

| Year | Top-300 | All >= ₹2 cr | Mix |
|---|---|---|---|
| 2013 | 1.9% / -16.8% | 2.8% / -8.6% | 2.7% / -8.9% |
| 2014 | 45.9% / -11.5% | 50.4% / -8.6% | 52.6% / -7.4% |
| 2015 | -1.6% / -10.6% | -4.2% / -11.7% | -1.6% / -11.1% |
| 2016 | 13.4% / -10.3% | 10.5% / -15.7% | 14.9% / -15.7% |
| 2017 | 42.2% / -3.1% | 61.5% / -2.9% | 56.8% / -2.4% |
| 2018 | -16.2% / -19.4% | -25.0% / -28.4% | -24.1% / -28.1% |
| 2019 | 10.3% / -9.2% | 6.8% / -13.4% | 12.3% / -10.8% |
| 2020 | 57.2% / -10.4% | 50.9% / -15.0% | 40.1% / -14.5% |
| 2021 | 32.3% / -7.7% | 80.3% / -5.5% | 65.0% / -4.2% |
| 2022 | 1.5% / -15.2% | -6.5% / -21.1% | -2.9% / -18.6% |
| 2023 | 72.2% / -5.2% | 59.8% / -11.8% | 54.0% / -11.5% |
| 2024 | 22.0% / -11.5% | 23.6% / -9.0% | 8.4% / -11.0% |
| 2025 | -3.8% / -12.6% | -21.2% / -24.0% | -16.2% / -20.0% |
| 2026 | 5.1% / -9.0% | 11.3% / -13.6% | 8.0% / -12.7% |

Since 2018 top-300 had the higher growth in **6 of 9 years** (bar: 60%), and in the holdout both higher growth (14.8% vs 7.2%) and a smaller worst fall (-20.6% vs -27.5%).
In the bad years the difference is largest: 2018 -16% vs -25%, 2022 +1.5% vs -6.5%, 2025 -3.8% vs -21.2%. All stocks win in small-cap boom years (2017, 2021).
Development favours all stocks (23.2% vs 18.9%), but development is inflated for small stocks (delisted small caps missing, round 23).

**Verdict: the decision rule written before this run is met. Proposed to the owner (needs his yes): VANTAGE BUYs only for the monthly top-300 by money traded** (setting `vantage_universe: top300`, built and tested, off until yes).
The mix (top-300 first) does not help. Signals outside the top 300 keep being followed silently (vantage_rejected.csv) so the live record can correct this decision.
