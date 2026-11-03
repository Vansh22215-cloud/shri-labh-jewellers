# CHANGELOG

## 2026-11-02
- v1 created (see DECISIONS.md D13-D20). Parameters fixed from textbook values before any backtest.
- Proposal P1 (exclude stocks with results due within 5 trading days) registered before testing.

## 2026-11-02 (automatic)
- Tested proposal P1: rejected. P1: gate FAIL, beat live in 7/13 walk-forward periods, WF CAGR 7.13% vs live 6.79%, WF maxDD -17.35% vs -21.74%

## 2026-11-02 (automatic)
- Weekly session summary:
  - Sandbox tests: 27 passed in 0.58s
  - Live v1 re-validated: gate FAILED
  - Paper check for v1: {'closed': 0} - fewer than 20 closed trades, too early to judge (no action).
  - Rejected P1: gate FAIL, beat live in 7/13 walk-forward periods, WF CAGR 7.13% vs live 6.79%, WF maxDD -17.35% vs -21.74%
  - Claude review: 0 reviewed trades closed - too few to judge; it remains an explainer only.
  - Holdout unchanged (starts 2025-05-01)
  - Variants tried so far: 2

## 2026-11-02 - Strategy search (556 variants, 10 families)
- Walk-forward search (D37-D42): picks beat NIFTYBEES in 2 of 10 years; holdout pick +5.4% vs NIFTYBEES -2.4%
  but below the liquid fund +9.8%; worst fall 20.2%; t-stat -1.95. **Search gate FAILED. Nothing promoted.**
- Even with hindsight, only 2 of 556 variants (0.4%) grew faster than NIFTYBEES over 2013-Apr 2025, and none
  beat it convincingly (best t-stat about 0). Best families on average: low-volatility momentum, momentum leaders.
- Live version stays v1 (not validated) -> reports say "No tips: strategy not validated. Use the index fund."

## 2026-11-03 - Short-term and intraday searches (your request: trades of hours to a few days)
- Short-term (1-5 day holds, 10 patterns incl. inside-day, gap-and-go, strong close, 3-day pullback; 2% risk x 6
  trades allowed): 1,080 variants. Walk-forward picks beat NIFTYBEES in 1 of 10 years, -2.9%/yr vs +13%/yr;
  holdout -13.2%; worst fall -38.8%. **Gate FAILED.** Median variant lost 20-30% a year: frequent trading pays
  STT, DP charges and slippage on every trade (e.g. best 3-day-pullback variant: +23%/yr before charges, +7% after).
- Intraday (hourly bars, Nov 2023-Nov 2026, 150 stocks, Zerodha MIS charges, no leverage): 120 variants; only
  5.8% made money; walk-forward picks lost Rs 985 on Rs 45,000; holdout -2.6%. **Gate FAILED.**
- Nothing promoted. Reports still say "No tips: strategy not validated."

## 2026-11-03 (automatic)
- Weekly session summary:
  - Sandbox tests: 62 passed in 8.27s
  - Live v1 re-validated: gate FAILED
  - Paper check for v1: {'closed': 0} - fewer than 20 closed trades, too early to judge (no action).
  - Strategy search (556 variants, 2026-11-02): walk-forward picks beat NIFTYBEES in 2 of 10 years; gate FAILED; short-term search gate FAILED; intraday search gate FAILED - nothing promoted.
  - Claude review: 0 reviewed trades closed - too few to judge; it remains an explainer only.
  - Holdout unchanged (starts 2025-05-01)
  - Variants tried so far: 1754

## 2026-11-03 - Re-run on clean data (ETFs/funds removed, D62)
- Swing search: still FAILED (2 of 10 years); same pick S385/a1; holdout +7.6% (was +5.4%).
- Short-term search: still FAILED (0 of 10 years); holdout -3.2%.
- Regime study refreshed: a1 trades average +0.07R; in today's market type (downtrend, calm, weak breadth) past
  trades won 43%.

## 2026-11-03 (automatic)
- Tested proposal R1: rejected. R1 vs a1: beat it in 4/13 walk-forward years, CAGR 8.43% vs 9.15%, worst fall -12.66% vs -9.92%, gate FAIL
