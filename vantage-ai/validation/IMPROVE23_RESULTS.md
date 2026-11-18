# Round 23 results: the Prosecutor attacks the live ₹2 cr/day floor (18 Nov 2026): ⚠️ FRAGILE
**Trade set:** all stocks (U2). ₹45,000 account. Each cell: yearly growth / worst fall / trades a week.

| Floor | Development | Holdout | All years |
|---|---|---|---|
| None | 40.5 / −18.1 / 16.1 | **11.8 / −20.7** / 4.0 | 31.6 / −17.7 |
| ₹1 cr | 28.0 / −17.2 | 7.5 / −28.2 | 22.6 |
| **₹2 cr (live)** | 24.9 / −18.5 / 6.7 | 10.5 / −26.8 / 3.6 | 20.7 |
| ₹3 cr | 24.1 / −17.0 | 7.7 / −27.6 | 19.6 |
| ₹5 cr | 23.1 / −16.5 | 8.8 / −24.6 | 19.1 |

## 23b: no floor, but thin stocks pay an extra 1% (wider spreads)
| | Development | Holdout | All years |
|---|---|---|---|
| ₹2 cr floor | 24.9 / −18.5 | 10.5 / −26.8 | 20.7 |
| No floor, +1% for thin stocks | 36.9 / −22.8 | 10.0 / −20.3 | 29.8 |

## Verdict
- **Not robust:** the neighbouring floors jump around (noise), and "no floor" beats ₹2 cr at the account level.
- **After realistic thin-stock costs** it is about equal in the holdout, with a smaller worst fall without the floor. Development is inflated for small stocks, because delisted small caps are missing.
- **Risks no test captures:** circuit lock-ins and operators in thin stocks.

**Decision:**
- Keep the floor for execution safety.
- Belief B6 is downgraded to "contested".
- The live record decides: rejected thin signals are already followed (`vantage_rejected.csv`), and the Learner's B6 check compares them after 20.

## Fingerprint (backlog 13a, `fingerprint.json`)
**VANTAGE picks** (median percentile among all top-300 stocks that day):

| Fact | Percentile |
|---|---|
| 6-month return | 71 |
| Closeness to the 52-week high | 82 |
| 1-month return | 77 |
| Volatility | 52 (average) |
| Liquidity | 53 (average) |

**Random stocks with the same fingerprint** (≈ 7 a day) earn:
- development: +3.3% vs VANTAGE +4.1%
- holdout: +2.1% vs VANTAGE +2.9%

So "strong, near-high stocks" explains about three-quarters of VANTAGE's edge, and its own rules add about 0.75 points a trade (beating the matched random picks in 98–100% of worlds). More candidates of this kind exist than money to buy them; money, not ideas, remains the limit.
