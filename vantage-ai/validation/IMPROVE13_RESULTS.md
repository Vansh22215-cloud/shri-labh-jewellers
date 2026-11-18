# Round 13 results: pyramiding winning trend trades (18 Nov 2026): ✅ PASSED (modest, consistent)
**Rules:** `IMPROVE13_PREREGISTRATION.md` (built from development-only exploration in `recycle_explore.py`). **Data:** `improve13_results.json`.

## ₹45,000 account, median of 15 random-order runs
Each cell: yearly growth / worst fall / new trades a week.

| | Today | With P1 (add a second lot when a trend trade is up ≥ 8% at day 15) |
|---|---|---|
| Top-300, development | 19.0% / −17.1% / 4.2 | **20.4%** / −17.1% / 4.8 |
| Top-300, holdout | 14.7% / −20.1% / 2.7 | **15.8%** / −20.8% / 2.8 |
| All stocks, development | 34.7% / −17.0% / 12.6 | **35.7%** / −18.9% / 14.3 |
| All stocks, holdout | 11.5% / −24.1% / 3.3 | **13.7%** / −25.1% / 3.5 |

## Robustness (post hoc, `improve13_robust.py`; not used to choose the rule)
- **Nearby triggers** (day 10 / 15 / 20, thresholds 5 / 8 / 12%): every one improves yearly growth, by +0.2 to +4.5 points.
- **Share of paired runs where P1 beats today:**
  - development: 67–100%
  - holdout: 53–67% (only 3 years, so more noise)

## Why it works
- A trend trade that is clearly working keeps earning more per day than a new signal (1.1–1.5× in the development data).
- Losing trades are not worse than new ones, so cutting them gains nothing (E2 and the exploration agree).

## Verdict
- A real but modest gain of about +1–2 points of yearly growth, with about the same worst fall.
- **Not applied:** it changes live tips, so it needs the owner's yes.
