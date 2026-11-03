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

## 2026-11-03 (automatic)
- Tested proposal R2: rejected. R2 vs a1: beat it in 8/13 walk-forward years, CAGR 4.41% vs 9.15%, worst fall -18.36% vs -9.92%, gate FAIL

## 2026-11-03 (automatic)
- Tested proposal R3: rejected. R3 vs a1: beat it in 5/13 walk-forward years, CAGR 7.65% vs 9.15%, worst fall -13.22% vs -9.92%, gate FAIL

## 2026-11-03 (automatic)
- Tested proposal R4: rejected. R4 vs a1: beat it in 6/13 walk-forward years, CAGR 5.56% vs 9.15%, worst fall -11.31% vs -9.92%, gate FAIL

## 2026-11-03 (automatic)
- Tested proposal R5: rejected. R5 vs a1: beat it in 7/13 walk-forward years, CAGR 7.1% vs 9.15%, worst fall -16.83% vs -9.92%, gate FAIL

## 2026-11-03 (automatic)
- Tested proposal R6: rejected. R6 vs a1: beat it in 2/13 walk-forward years, CAGR 7.87% vs 9.15%, worst fall -15.71% vs -9.92%, gate FAIL

## 2026-11-03 (automatic)
- Tested proposal R9: rejected. R9 vs a1: beat it in 6/13 walk-forward years, CAGR 6.97% vs 9.15%, worst fall -13.32% vs -9.92%, gate FAIL

## 2026-11-03 - Research round 1 (R1-R6, R9 vs a1): all rejected
- R1 sector filter 8.4%/yr, R2 volume 4.4%, R3 trail after T1 7.7%, R4 RS>60 5.6%, R5 ATR<4% 7.1%,
  R6 results exclusion 7.9%, R9 max 1 per industry 7.0% - vs a1 9.15%/yr (2013-Apr 2025), a1 worst fall -9.9%.
- Checked for bugs: none. Lesson: a1's result is sensitive to small rule changes (4-9%/yr range), so part of its
  backtest is likely luck; expect live results below the backtest. Keep risk per trade at 1%.

## 2026-11-03 (automatic)
- Tested proposal R7: rejected. R7 vs a1: beat it in 7/13 walk-forward years, CAGR 4.28% vs 9.15%, worst fall -11.89% vs -9.92%, gate FAIL

## 2026-11-03 (automatic)
- Tested proposal R8: rejected. R8 vs a1: beat it in 6/13 walk-forward years, CAGR 4.64% vs 9.15%, worst fall -10.85% vs -9.92%, gate FAIL

## 2026-11-03 (automatic)
- Tested proposal R10: rejected. R10 vs a1: beat it in 4/13 walk-forward years, CAGR 3.6% vs 9.15%, worst fall -13.21% vs -9.92%, gate FAIL

## 2026-11-03 - Research round 2 (vs a1): all rejected
- R7 delivery filter 4.3%/yr, R8 high-delivery breakout family 4.6%, R10 nearer targets (1R/2R) 3.6% - vs a1 9.15%.
- ROADMAP D1 (delivery data) and P2 (industry limit) built and tested: did not help a1 -> marked [~].

## 2026-11-03 - Strategy library + combined fair search (684 variants, D66 selection rule)
- Library (8 famous methods, 128 variants): best families by median - sector rotation 10.4%/yr, Minervini 9.6%,
  PEAD 9.4% (Sharpe 2.0, few trades), 12-1 momentum 8.9%. Hindsight-best variants made Rs 150-250 per trade vs a1 Rs 33.
- Combined fair walk-forward search (all 684, pick by excess-over-liquid-fund Sharpe): FAILED - beat NIFTYBEES in
  3/10 years, 6.5%/yr, worst fall -22%. Today's fair pick is S385 = a1 itself, so tips stay on a1.
- Lesson: methods that look best in hindsight do not stay best year to year (the yearly re-pick chases last
  period's winner). Next: the meta-system S12 (combine signals of several families instead of picking one).

## 2026-11-03 - Intelligence desk: I1 + I2 built
- I1 FII/DII/Pro/Client positioning (NSE participant OI since 2013): "Big money" line in messages; idea R12 queued.
- I2 F&O end-of-day intelligence (from Jul 2024): long/short build-up, PCR, max pain, OI support/resistance shown
  on trade cards; options checker now uses NSE's real expiry dates (Nov 2026 expiry is 23 Nov, not 24).

## 2026-11-03 - I3 global markets built
- S&P 500, Nasdaq, Dow, US VIX, Nikkei, Hang Seng, FTSE, Brent, gold, USD/INR, US 10y. Nifty open gap after S&P moves (2015-2026): S&P < -1.5% -> -0.68% avg gap (180 days), > +1.5% -> +0.68% (151 days). Idea R13 pre-registered.

## 2026-11-03 - I4 news built
- Headlines from ET, Moneycontrol, Business Standard, Mint matched to stocks; red-flag words (fraud, raid, SEBI order, downgrade, default...) raise caution on trade cards and tip checks.
