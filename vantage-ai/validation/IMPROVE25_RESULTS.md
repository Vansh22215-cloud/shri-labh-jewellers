# Round 25 results (19 Nov 2026): compounding (size on the account's current value)

| Setup / period | Fixed ₹51,000 | Current value | Updated monthly |
|---|---|---|---|
| Live setup C+A top-300, development | 20.5% / -14.7% | 21.4% / -22.1% | 21.6% / -20.5% |
| Live setup C+A top-300, holdout | 18.8% / -19.8% | 20.5% / -19.1% | 20.1% / -18.7% |
| All stocks, development | 40.1% / -19.8% | 46.1% / -33.9% | 42.5% / -37.8% |
| All stocks, holdout | 11.3% / -22.2% | 11.0% / -24.0% | 6.5% / -25.0% |

Verdict: **does not pass the bar** (falls deeper in development, no gain for all stocks in the holdout).
Lesson: the fixed-₹51,000 tests made later years look safer than they are (as the account grows, fixed trades
become a small share of it). Updating the capital setting once a month is what a real account does; for top-300
stocks it adds about 1-1.5 points a year. It is advice for the owner's own /capital setting, not a rule change.
