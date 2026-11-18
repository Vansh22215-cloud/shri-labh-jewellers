# Per-signal likely-win %: results (18 Nov 2026): ❌ FAILED, the type average stays
**Rules:** `CALIB_PREREGISTRATION.md`. **Code:** `calib.py`. **Data:** `calib_results.json`.

The model was trained on signals before Nov 2023 and checked on 1,519 later signals.

## Holdout: all signals, five groups from lowest to highest predicted chance
| Group | Predicted | Actually won |
|---|---|---|
| 1 | 36.6% | 33.2% |
| 2 | 42.3% | 38.8% |
| 3 | 44.6% | 37.6% (off by 7 points) |
| 4 | 46.6% | 48.4% |
| 5 | 57.6% | 54.6% |

- The spread between the groups comes almost entirely from the signal **type**: dip-buys win ~80%, breakouts ~35%.
- Accuracy (Brier score): 0.2359 for the model vs 0.2363 for the plain type table. This is no real improvement.

## Within the trend-follow type (RCP, about 75% of signals)
Actual win % by predicted group: 41.6, 37.9, 40.5, 50.0, 44.0. There is **no steady pattern**.

## The company's own past record
Its coefficient in the model is slightly **negative**: a company's earlier VANTAGE results do not predict its next one. The typical company has only 5 signals in 13 years.

## Conclusion
- Nothing known on the signal day reliably separates winners from losers within a signal type.
- Showing a different % per company would be false precision.

**Applied (D130):** the messages now say plainly that the % is the record of that signal type. They also show:
- the last 3 years separately,
- the average result per trade,
- the company's own past signals, as information only.
