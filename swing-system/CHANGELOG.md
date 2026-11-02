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
