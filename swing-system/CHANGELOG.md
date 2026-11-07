# CHANGELOG

## 2026-11-06 (forwarded market calls)
- Bot replies redesigned: answer first, why it could work / fail, odds bar, plan, plain bottom line (D88).
- Runs pick up new code within ~10 minutes (D87).
- Bot reads chart pictures: words, pattern names, price lines (via the price scale), instrument from the scale (D86).
- Every check adds the system's own pattern scan on real prices.
- Bot understands index, forex, gold, crude and crypto views/setups, tracks them and reports right/wrong (D85).
- Stock tips forwarded to the bot now also get a message when they hit target/stop.

## 2026-11-05 (never stop)
- GitHub runs now restart themselves all day (no outside timer needed); crash-loop guard (D84).
- Telegram messages retried, plain-text fallback, every send logged; company of the day is its own retried job.
- Evening message shows how many hourly scans ran; clearer no-tips reason in aggressive mode.

## 2026-11-04 (lifelong data + library complete)
- Lifelong append-only data store (prices incl. delisted, hourly, 5-minute, news, statement years) used by research.
- Personal files hidden from the public repo/logs; backups to the owner's Telegram (D81).
- Pattern library v2 fully built: 0 items left; 34 switch on as history grows, 28 when a tick/book feed is added (D82).

## 2026-11-03 (library v2 + Claude-free)
- Owner's pattern library v2 (791 records) loaded; 492 items built (was ~230), 3,276 ideas in the factory.
- GitHub save step fixed (results were being lost); research tests ideas for up to 120 min per day on GitHub.
- Claude's scheduled sessions switched off; GitHub does everything (D80).

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

## 2026-11-03 - I5 event calendar built
- Union Budget, election results, monthly F&O expiry; 'Upcoming events' line in messages. a1 trades entered within 2 days of Budget/election: 13 trades, 69% winners (vs 47%), +Rs 171 avg - sample too small, no rule adopted.

## 2026-11-03 - T1 trade card upgrade
- Calibrated odds from all 8,694 historical a1 signals: T1 (2R) before stop 16%, T2 2.5%, T3 0.6%, stop 34%, ~50% end at the 25-day limit; by regime T1 ranges 11-25%. Cards now show these honestly with sample size, plus T3, risk:reward and cancel-if conditions.

## 2026-11-03 (automatic)
- Tested proposal R11: rejected. R11 vs a1: beat it in 6/13 walk-forward years, CAGR 7.42% vs 9.15%, worst fall -10.31% vs -9.92%, gate FAIL

## 2026-11-03 - UI1 dashboard
- Phone-friendly dashboard published (private): https://claude.ai/artifact/LKLWX4WHnvo6bvDoa6botT, fed by data/dashboard/desk.json from swing/dashboard_export.py; refreshed by scheduled runs.

## 2026-11-03 - A1 performance analytics
- a1 trades only (no liquid-fund interest), 576 trades 2013-Nov 2026: +Rs 16,780 before tax, Rs 5,647 tax, +Rs 11,132 after tax on Rs 45,000 (~Rs 800/yr); 7 losing years out of 14. Losers: 59% at the stop (avg -Rs 521), 37% at the time limit (avg -Rs 154), 4% gap-through-stop (avg -Rs 585).

## 2026-11-03 (automatic)
- Tested proposal R16: rejected. R16 vs a1: beat it in 7/13 walk-forward years, CAGR 7.25% vs 9.15%, worst fall -8.73% vs -9.92%, gate FAIL

## 2026-11-03 - S2 CANSLIM
- Point-in-time EPS growth (Yahoo reported EPS, ~208 stocks) + canslim family. R16 rejected: 7.25%/yr vs a1 9.15%, beat a1 in 7/13 years, worst fall -8.7% vs -9.9%.

## 2026-11-03 - S12 meta-system evaluated
- Top-3-families ensemble (walk-forward, yearly re-pick): 7.75%/yr, worst fall -8.4%, beat NIFTYBEES 1/10 years (gate failed). Better than the single-pick procedure (6.49%, -22.1%). Plan D72: move aggressive mode to the ensemble once live plumbing exists.

## 2026-11-04 (automatic)
- Tested proposal R12: rejected. R12 vs a1: beat it in 0/13 walk-forward years, CAGR 8.8% vs 8.8% (needs +0.40), worst fall -9.92% vs -9.92%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal R13: rejected. R13 vs a1: beat it in 5/13 walk-forward years, CAGR 7.91% vs 8.8% (needs +0.41), worst fall -13.07% vs -9.92%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal R14: rejected. R14 vs a1: beat it in 7/13 walk-forward years, CAGR 7.87% vs 8.8% (needs +0.41), worst fall -12.94% vs -9.92%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal R15: rejected. R15 vs a1: beat it in 7/13 walk-forward years, CAGR 4.36% vs 8.8% (needs +0.42), worst fall -17.46% vs -9.92%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A1: rejected. A1 vs a1: beat it in 8/13 walk-forward years, CAGR 8.06% vs 8.8% (needs +0.42), worst fall -13.66% vs -9.92%, gate FAIL

## 2026-11-04 (automatic)
- PROMOTED proposal A2 as a2 (previous a1 kept). A2 vs a1: beat it in 7/13 walk-forward years, CAGR 9.76% vs 8.8% (needs +0.43), worst fall -10.84% vs -9.92%, gate FAIL

## 2026-11-04 (automatic)
- PROMOTED proposal A3 as a3 (previous a2 kept). A3 vs a2: beat it in 8/13 walk-forward years, CAGR 12.41% vs 9.76% (needs +0.43), worst fall -10.71% vs -10.84%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A4: rejected. A4 vs a3: beat it in 0/13 walk-forward years, CAGR 4.11% vs 12.41% (needs +0.43), worst fall -18.43% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A5: rejected. A5 vs a3: beat it in 3/13 walk-forward years, CAGR 7.39% vs 12.41% (needs +0.44), worst fall -17.03% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A6: rejected. A6 vs a3: beat it in 5/13 walk-forward years, CAGR 5.11% vs 12.41% (needs +0.44), worst fall -18.63% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A7: rejected. A7 vs a3: beat it in 8/13 walk-forward years, CAGR 10.75% vs 12.41% (needs +0.44), worst fall -12.22% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A8: rejected. A8 vs a3: beat it in 7/13 walk-forward years, CAGR 6.8% vs 12.41% (needs +0.45), worst fall -18.44% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A9: rejected. A9 vs a3: beat it in 8/13 walk-forward years, CAGR 8.98% vs 12.41% (needs +0.45), worst fall -19.87% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A10: rejected. A10 vs a3: beat it in 6/13 walk-forward years, CAGR 7.92% vs 12.41% (needs +0.45), worst fall -17.2% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A11: rejected. A11 vs a3: beat it in 5/13 walk-forward years, CAGR 9.07% vs 12.41% (needs +0.45), worst fall -20.23% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A12: rejected. A12 vs a3: beat it in 7/13 walk-forward years, CAGR 9.64% vs 12.41% (needs +0.46), worst fall -13.13% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A13: rejected. A13 vs a3: beat it in 3/13 walk-forward years, CAGR 5.77% vs 12.41% (needs +0.46), worst fall -16.93% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A14: rejected. A14 vs a3: beat it in 5/13 walk-forward years, CAGR 8.17% vs 12.41% (needs +0.46), worst fall -15.74% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A15: rejected. A15 vs a3: beat it in 6/13 walk-forward years, CAGR 8.39% vs 12.41% (needs +0.46), worst fall -14.46% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A16: rejected. A16 vs a3: beat it in 7/13 walk-forward years, CAGR 6.31% vs 12.41% (needs +0.47), worst fall -20.26% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A17: rejected. A17 vs a3: beat it in 3/13 walk-forward years, CAGR 7.41% vs 12.41% (needs +0.47), worst fall -15.26% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A18: rejected. A18 vs a3: beat it in 6/13 walk-forward years, CAGR 6.24% vs 12.41% (needs +0.47), worst fall -23.34% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A19: rejected. A19 vs a3: beat it in 6/13 walk-forward years, CAGR 7.32% vs 12.41% (needs +0.47), worst fall -13.9% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A20: rejected. A20 vs a3: beat it in 6/13 walk-forward years, CAGR 9.15% vs 12.41% (needs +0.47), worst fall -12.87% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A21: rejected. A21 vs a3: beat it in 5/13 walk-forward years, CAGR 5.95% vs 12.41% (needs +0.48), worst fall -12.0% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A22: rejected. A22 vs a3: beat it in 7/13 walk-forward years, CAGR 4.54% vs 12.41% (needs +0.48), worst fall -16.83% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A23: rejected. A23 vs a3: beat it in 3/13 walk-forward years, CAGR 4.74% vs 12.41% (needs +0.48), worst fall -18.59% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A24: rejected. A24 vs a3: beat it in 3/13 walk-forward years, CAGR 4.19% vs 12.41% (needs +0.48), worst fall -16.13% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A25: rejected. A25 vs a3: beat it in 7/13 walk-forward years, CAGR 7.58% vs 12.41% (needs +0.48), worst fall -10.57% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A26: rejected. A26 vs a3: beat it in 6/13 walk-forward years, CAGR 7.34% vs 12.41% (needs +0.48), worst fall -20.09% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A27: rejected. A27 vs a3: beat it in 6/13 walk-forward years, CAGR 7.18% vs 12.41% (needs +0.48), worst fall -12.54% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A28: rejected. A28 vs a3: beat it in 4/13 walk-forward years, CAGR 9.57% vs 12.41% (needs +0.49), worst fall -14.48% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A29: rejected. A29 vs a3: beat it in 5/13 walk-forward years, CAGR 5.42% vs 12.41% (needs +0.49), worst fall -10.69% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A30: rejected. A30 vs a3: beat it in 6/13 walk-forward years, CAGR 5.39% vs 12.41% (needs +0.49), worst fall -18.58% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A31: rejected. A31 vs a3: beat it in 4/13 walk-forward years, CAGR 6.65% vs 12.41% (needs +0.49), worst fall -10.84% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A32: rejected. A32 vs a3: beat it in 5/13 walk-forward years, CAGR 5.64% vs 12.41% (needs +0.49), worst fall -15.98% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A33: rejected. A33 vs a3: beat it in 9/13 walk-forward years, CAGR 8.69% vs 12.41% (needs +0.49), worst fall -6.84% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A34: rejected. A34 vs a3: beat it in 7/13 walk-forward years, CAGR 9.07% vs 12.41% (needs +0.49), worst fall -15.59% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A35: rejected. A35 vs a3: beat it in 3/13 walk-forward years, CAGR 8.83% vs 12.41% (needs +0.50), worst fall -11.67% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A36: rejected. A36 vs a3: beat it in 7/13 walk-forward years, CAGR 6.06% vs 12.41% (needs +0.50), worst fall -19.79% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A37: rejected. A37 vs a3: beat it in 4/13 walk-forward years, CAGR 8.82% vs 12.41% (needs +0.50), worst fall -16.39% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A38: rejected. A38 vs a3: beat it in 6/13 walk-forward years, CAGR 9.31% vs 12.41% (needs +0.50), worst fall -21.31% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A39: rejected. A39 vs a3: beat it in 4/13 walk-forward years, CAGR 9.99% vs 12.41% (needs +0.50), worst fall -12.44% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A40: rejected. A40 vs a3: beat it in 6/13 walk-forward years, CAGR 8.43% vs 12.41% (needs +0.50), worst fall -12.56% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A41: rejected. A41 vs a3: beat it in 4/13 walk-forward years, CAGR 8.13% vs 12.41% (needs +0.50), worst fall -17.04% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A42: rejected. A42 vs a3: beat it in 3/13 walk-forward years, CAGR 4.5% vs 12.55% (needs +0.50), worst fall -16.61% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A43: rejected. A43 vs a3: beat it in 4/13 walk-forward years, CAGR 6.19% vs 12.55% (needs +0.50), worst fall -13.08% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A44: rejected. A44 vs a3: beat it in 8/13 walk-forward years, CAGR 8.3% vs 12.55% (needs +0.51), worst fall -17.47% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A45: rejected. A45 vs a3: beat it in 7/13 walk-forward years, CAGR 9.22% vs 12.55% (needs +0.51), worst fall -13.74% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A46: rejected. A46 vs a3: beat it in 2/13 walk-forward years, CAGR 4.62% vs 12.55% (needs +0.51), worst fall -11.83% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A47: rejected. A47 vs a3: beat it in 6/13 walk-forward years, CAGR 5.15% vs 12.55% (needs +0.51), worst fall -15.28% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A48: rejected. A48 vs a3: beat it in 7/13 walk-forward years, CAGR 14.01% vs 12.55% (needs +0.51), worst fall -9.69% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A49: rejected. A49 vs a3: beat it in 5/13 walk-forward years, CAGR 6.49% vs 12.55% (needs +0.51), worst fall -15.62% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A50: rejected. A50 vs a3: beat it in 4/13 walk-forward years, CAGR 7.33% vs 12.55% (needs +0.51), worst fall -10.82% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A51: rejected. A51 vs a3: beat it in 7/13 walk-forward years, CAGR 7.83% vs 12.55% (needs +0.51), worst fall -15.73% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A52: rejected. A52 vs a3: beat it in 6/13 walk-forward years, CAGR 6.86% vs 12.55% (needs +0.51), worst fall -0.32% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A53: rejected. A53 vs a3: beat it in 6/13 walk-forward years, CAGR 7.31% vs 12.55% (needs +0.51), worst fall -1.58% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A54: rejected. A54 vs a3: beat it in 6/13 walk-forward years, CAGR 7.04% vs 12.55% (needs +0.52), worst fall -0.61% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A55: rejected. A55 vs a3: beat it in 3/13 walk-forward years, CAGR 6.04% vs 12.55% (needs +0.52), worst fall -17.42% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A56: rejected. A56 vs a3: beat it in 6/13 walk-forward years, CAGR 7.12% vs 12.55% (needs +0.52), worst fall -2.35% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A57: rejected. A57 vs a3: beat it in 6/13 walk-forward years, CAGR 5.92% vs 12.55% (needs +0.52), worst fall -12.45% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A58: rejected. A58 vs a3: beat it in 6/13 walk-forward years, CAGR 6.87% vs 12.55% (needs +0.52), worst fall -0.88% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A59: rejected. A59 vs a3: beat it in 5/13 walk-forward years, CAGR 5.86% vs 12.55% (needs +0.52), worst fall -9.4% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A60: rejected. A60 vs a3: beat it in 6/13 walk-forward years, CAGR 10.13% vs 12.55% (needs +0.52), worst fall -18.37% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A61: rejected. A61 vs a3: beat it in 5/13 walk-forward years, CAGR 6.05% vs 12.55% (needs +0.52), worst fall -17.71% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A62: rejected. A62 vs a3: beat it in 4/13 walk-forward years, CAGR 5.61% vs 12.55% (needs +0.52), worst fall -11.68% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A63: rejected. A63 vs a3: beat it in 5/13 walk-forward years, CAGR 6.47% vs 12.55% (needs +0.52), worst fall -11.62% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A64: rejected. A64 vs a3: beat it in 6/13 walk-forward years, CAGR 5.18% vs 12.55% (needs +0.52), worst fall -22.34% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A65: rejected. A65 vs a3: beat it in 6/13 walk-forward years, CAGR 7.61% vs 12.55% (needs +0.52), worst fall -17.11% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A66: rejected. A66 vs a3: beat it in 8/13 walk-forward years, CAGR 10.41% vs 12.55% (needs +0.52), worst fall -13.93% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A67: rejected. A67 vs a3: beat it in 7/13 walk-forward years, CAGR 9.61% vs 12.55% (needs +0.53), worst fall -11.65% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A68: rejected. A68 vs a3: beat it in 6/13 walk-forward years, CAGR 9.06% vs 12.55% (needs +0.53), worst fall -12.77% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A69: rejected. A69 vs a3: beat it in 7/13 walk-forward years, CAGR 7.04% vs 12.55% (needs +0.53), worst fall -15.56% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A70: rejected. A70 vs a3: beat it in 6/13 walk-forward years, CAGR 6.92% vs 12.55% (needs +0.53), worst fall -0.24% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A71: rejected. A71 vs a3: beat it in 6/13 walk-forward years, CAGR 6.92% vs 12.55% (needs +0.53), worst fall -0.24% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A72: rejected. A72 vs a3: beat it in 4/13 walk-forward years, CAGR 6.68% vs 12.55% (needs +0.53), worst fall -9.17% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A73: rejected. A73 vs a3: beat it in 8/13 walk-forward years, CAGR 10.09% vs 12.55% (needs +0.53), worst fall -15.84% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A74: rejected. A74 vs a3: beat it in 4/13 walk-forward years, CAGR 3.44% vs 12.55% (needs +0.53), worst fall -21.25% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A75: rejected. A75 vs a3: beat it in 5/13 walk-forward years, CAGR 5.92% vs 12.55% (needs +0.53), worst fall -11.78% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A76: rejected. A76 vs a3: beat it in 7/13 walk-forward years, CAGR 8.57% vs 12.55% (needs +0.53), worst fall -10.69% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A77: rejected. A77 vs a3: beat it in 5/13 walk-forward years, CAGR 6.84% vs 12.55% (needs +0.53), worst fall -2.49% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A78: rejected. A78 vs a3: beat it in 2/13 walk-forward years, CAGR 3.87% vs 12.55% (needs +0.53), worst fall -13.53% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A79: rejected. A79 vs a3: beat it in 5/13 walk-forward years, CAGR 6.4% vs 12.55% (needs +0.53), worst fall -11.81% vs -10.71%, gate FAIL

## 2026-11-04 (automatic)
- Tested proposal A80: rejected. A80 vs a3: beat it in 3/13 walk-forward years, CAGR 7.3% vs 12.55% (needs +0.53), worst fall -13.17% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A81: rejected. A81 vs a3: beat it in 4/13 walk-forward years, CAGR 9.28% vs 12.55% (needs +0.53), worst fall -9.92% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A82: rejected. A82 vs a3: beat it in 8/13 walk-forward years, CAGR 9.86% vs 12.55% (needs +0.54), worst fall -15.06% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A83: rejected. A83 vs a3: beat it in 6/13 walk-forward years, CAGR 6.65% vs 12.55% (needs +0.54), worst fall -5.78% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A84: rejected. A84 vs a3: beat it in 7/13 walk-forward years, CAGR 7.66% vs 12.55% (needs +0.54), worst fall -10.33% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A85: rejected. A85 vs a3: beat it in 7/13 walk-forward years, CAGR 9.46% vs 12.55% (needs +0.54), worst fall -12.47% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A86: rejected. A86 vs a3: beat it in 7/13 walk-forward years, CAGR 6.38% vs 12.55% (needs +0.54), worst fall -19.25% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A87: rejected. A87 vs a3: beat it in 4/13 walk-forward years, CAGR 6.5% vs 12.55% (needs +0.54), worst fall -10.28% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A88: rejected. A88 vs a3: beat it in 8/13 walk-forward years, CAGR 9.01% vs 12.55% (needs +0.54), worst fall -13.77% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A89: rejected. A89 vs a3: beat it in 8/13 walk-forward years, CAGR 7.41% vs 12.55% (needs +0.54), worst fall -10.52% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A90: rejected. A90 vs a3: beat it in 6/13 walk-forward years, CAGR 6.37% vs 12.55% (needs +0.54), worst fall -10.2% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A91: rejected. A91 vs a3: beat it in 3/13 walk-forward years, CAGR 7.61% vs 12.55% (needs +0.54), worst fall -11.25% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A92: rejected. A92 vs a3: beat it in 6/13 walk-forward years, CAGR 8.79% vs 12.55% (needs +0.54), worst fall -16.54% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A93: rejected. A93 vs a3: beat it in 7/13 walk-forward years, CAGR 6.11% vs 12.55% (needs +0.54), worst fall -14.41% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A94: rejected. A94 vs a3: beat it in 7/13 walk-forward years, CAGR 6.94% vs 12.55% (needs +0.54), worst fall -16.6% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A95: rejected. A95 vs a3: beat it in 6/13 walk-forward years, CAGR 7.62% vs 12.55% (needs +0.54), worst fall -19.59% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A96: rejected. A96 vs a3: beat it in 8/13 walk-forward years, CAGR 11.08% vs 12.55% (needs +0.54), worst fall -12.54% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A97: rejected. A97 vs a3: beat it in 4/13 walk-forward years, CAGR 3.68% vs 12.55% (needs +0.54), worst fall -17.37% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A98: rejected. A98 vs a3: beat it in 5/13 walk-forward years, CAGR 5.78% vs 12.55% (needs +0.54), worst fall -13.92% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A99: rejected. A99 vs a3: beat it in 6/13 walk-forward years, CAGR 8.33% vs 12.55% (needs +0.54), worst fall -13.25% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A100: rejected. A100 vs a3: beat it in 4/13 walk-forward years, CAGR 4.79% vs 12.55% (needs +0.55), worst fall -18.95% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A101: rejected. A101 vs a3: beat it in 3/13 walk-forward years, CAGR 5.49% vs 12.55% (needs +0.55), worst fall -18.19% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A102: rejected. A102 vs a3: beat it in 5/13 walk-forward years, CAGR 7.75% vs 12.55% (needs +0.55), worst fall -15.58% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A103: rejected. A103 vs a3: beat it in 7/13 walk-forward years, CAGR 6.9% vs 12.55% (needs +0.55), worst fall -16.63% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A104: rejected. A104 vs a3: beat it in 8/13 walk-forward years, CAGR 11.16% vs 12.55% (needs +0.55), worst fall -12.09% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A105: rejected. A105 vs a3: beat it in 3/13 walk-forward years, CAGR 4.46% vs 12.55% (needs +0.55), worst fall -11.2% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A106: rejected. A106 vs a3: beat it in 5/13 walk-forward years, CAGR 9.45% vs 12.55% (needs +0.55), worst fall -12.0% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A107: rejected. A107 vs a3: beat it in 3/13 walk-forward years, CAGR 5.94% vs 12.55% (needs +0.55), worst fall -11.32% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A108: rejected. A108 vs a3: beat it in 5/13 walk-forward years, CAGR 7.11% vs 12.55% (needs +0.55), worst fall -6.85% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A109: rejected. A109 vs a3: beat it in 3/13 walk-forward years, CAGR 5.99% vs 12.55% (needs +0.55), worst fall -17.68% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A110: rejected. A110 vs a3: beat it in 7/13 walk-forward years, CAGR 8.16% vs 12.55% (needs +0.55), worst fall -8.13% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A111: rejected. A111 vs a3: beat it in 6/13 walk-forward years, CAGR 9.27% vs 12.55% (needs +0.55), worst fall -11.71% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A112: rejected. A112 vs a3: beat it in 3/13 walk-forward years, CAGR 4.93% vs 12.55% (needs +0.55), worst fall -13.56% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A113: rejected. A113 vs a3: beat it in 3/13 walk-forward years, CAGR 3.6% vs 12.55% (needs +0.55), worst fall -12.83% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A114: rejected. A114 vs a3: beat it in 4/13 walk-forward years, CAGR 5.59% vs 12.55% (needs +0.55), worst fall -23.5% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A115: rejected. A115 vs a3: beat it in 5/13 walk-forward years, CAGR 6.52% vs 12.55% (needs +0.55), worst fall -2.65% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A116: rejected. A116 vs a3: beat it in 5/13 walk-forward years, CAGR 7.25% vs 12.55% (needs +0.55), worst fall -19.97% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A117: rejected. A117 vs a3: beat it in 4/13 walk-forward years, CAGR 8.19% vs 12.55% (needs +0.55), worst fall -12.38% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A118: rejected. A118 vs a3: beat it in 5/13 walk-forward years, CAGR 8.68% vs 12.55% (needs +0.55), worst fall -15.52% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A119: rejected. A119 vs a3: beat it in 4/13 walk-forward years, CAGR 6.18% vs 12.55% (needs +0.55), worst fall -10.33% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A120: rejected. A120 vs a3: beat it in 5/13 walk-forward years, CAGR 6.8% vs 12.55% (needs +0.55), worst fall -2.11% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A121: rejected. A121 vs a3: beat it in 5/13 walk-forward years, CAGR 7.79% vs 12.55% (needs +0.55), worst fall -4.55% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A122: rejected. A122 vs a3: beat it in 7/13 walk-forward years, CAGR 8.21% vs 12.55% (needs +0.55), worst fall -10.06% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A123: rejected. A123 vs a3: beat it in 6/13 walk-forward years, CAGR 6.95% vs 12.55% (needs +0.56), worst fall -12.21% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A124: rejected. A124 vs a3: beat it in 6/13 walk-forward years, CAGR 7.11% vs 12.55% (needs +0.56), worst fall -0.88% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A125: rejected. A125 vs a3: beat it in 3/13 walk-forward years, CAGR 2.94% vs 12.55% (needs +0.56), worst fall -15.91% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A126: rejected. A126 vs a3: beat it in 3/13 walk-forward years, CAGR 5.83% vs 12.55% (needs +0.56), worst fall -13.15% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A127: rejected. A127 vs a3: beat it in 4/13 walk-forward years, CAGR 8.25% vs 12.55% (needs +0.56), worst fall -6.54% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A128: rejected. A128 vs a3: beat it in 5/13 walk-forward years, CAGR 4.13% vs 12.55% (needs +0.56), worst fall -18.49% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A129: rejected. A129 vs a3: beat it in 5/13 walk-forward years, CAGR 4.91% vs 12.55% (needs +0.56), worst fall -15.11% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A130: rejected. A130 vs a3: beat it in 7/13 walk-forward years, CAGR 7.16% vs 12.55% (needs +0.56), worst fall -16.32% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A131: rejected. A131 vs a3: beat it in 4/13 walk-forward years, CAGR 5.13% vs 12.55% (needs +0.56), worst fall -16.02% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A132: rejected. A132 vs a3: beat it in 5/13 walk-forward years, CAGR 8.51% vs 12.55% (needs +0.56), worst fall -20.29% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A133: rejected. A133 vs a3: beat it in 3/13 walk-forward years, CAGR 6.06% vs 12.55% (needs +0.56), worst fall -4.72% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A134: rejected. A134 vs a3: beat it in 6/13 walk-forward years, CAGR 3.93% vs 12.55% (needs +0.56), worst fall -28.26% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A135: rejected. A135 vs a3: beat it in 5/13 walk-forward years, CAGR 5.41% vs 12.55% (needs +0.56), worst fall -18.15% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A136: rejected. A136 vs a3: beat it in 5/13 walk-forward years, CAGR 8.64% vs 12.55% (needs +0.56), worst fall -18.42% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A137: rejected. A137 vs a3: beat it in 3/13 walk-forward years, CAGR 6.55% vs 12.55% (needs +0.56), worst fall -15.82% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A138: rejected. A138 vs a3: beat it in 5/13 walk-forward years, CAGR 5.68% vs 12.55% (needs +0.56), worst fall -17.35% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A139: rejected. A139 vs a3: beat it in 5/13 walk-forward years, CAGR 9.99% vs 12.55% (needs +0.56), worst fall -9.7% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A140: rejected. A140 vs a3: beat it in 4/13 walk-forward years, CAGR 8.85% vs 12.55% (needs +0.56), worst fall -12.83% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A141: rejected. A141 vs a3: beat it in 7/13 walk-forward years, CAGR 7.37% vs 12.55% (needs +0.56), worst fall -7.83% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A142: rejected. A142 vs a3: beat it in 5/13 walk-forward years, CAGR 7.47% vs 12.55% (needs +0.56), worst fall -13.04% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A143: rejected. A143 vs a3: beat it in 7/13 walk-forward years, CAGR 8.12% vs 12.55% (needs +0.56), worst fall -12.51% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A144: rejected. A144 vs a3: beat it in 6/13 walk-forward years, CAGR 8.32% vs 12.55% (needs +0.56), worst fall -11.9% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A145: rejected. A145 vs a3: beat it in 3/13 walk-forward years, CAGR 7.3% vs 12.55% (needs +0.56), worst fall -16.46% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A146: rejected. A146 vs a3: beat it in 5/13 walk-forward years, CAGR 8.28% vs 12.55% (needs +0.56), worst fall -19.87% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A147: rejected. A147 vs a3: beat it in 6/13 walk-forward years, CAGR 7.26% vs 12.55% (needs +0.56), worst fall -14.5% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A148: rejected. A148 vs a3: beat it in 3/13 walk-forward years, CAGR 5.3% vs 12.55% (needs +0.56), worst fall -17.71% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A149: rejected. A149 vs a3: beat it in 6/13 walk-forward years, CAGR 4.37% vs 12.55% (needs +0.56), worst fall -14.16% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A150: rejected. A150 vs a3: beat it in 6/13 walk-forward years, CAGR 9.25% vs 12.55% (needs +0.57), worst fall -9.6% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A151: rejected. A151 vs a3: beat it in 6/13 walk-forward years, CAGR 7.34% vs 12.55% (needs +0.57), worst fall -11.09% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A152: rejected. A152 vs a3: beat it in 3/13 walk-forward years, CAGR 5.5% vs 12.55% (needs +0.57), worst fall -16.27% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A153: rejected. A153 vs a3: beat it in 5/13 walk-forward years, CAGR 8.45% vs 12.55% (needs +0.57), worst fall -11.07% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A154: rejected. A154 vs a3: beat it in 6/13 walk-forward years, CAGR 7.76% vs 12.55% (needs +0.57), worst fall -22.66% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A155: rejected. A155 vs a3: beat it in 5/13 walk-forward years, CAGR 6.87% vs 12.55% (needs +0.57), worst fall -13.34% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A156: rejected. A156 vs a3: beat it in 5/13 walk-forward years, CAGR 8.71% vs 12.55% (needs +0.57), worst fall -23.3% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A157: rejected. A157 vs a3: beat it in 2/13 walk-forward years, CAGR 2.06% vs 12.55% (needs +0.57), worst fall -16.46% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A158: rejected. A158 vs a3: beat it in 5/13 walk-forward years, CAGR 4.32% vs 12.55% (needs +0.57), worst fall -10.72% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A159: rejected. A159 vs a3: beat it in 7/13 walk-forward years, CAGR 9.01% vs 12.55% (needs +0.57), worst fall -13.84% vs -10.71%, gate FAIL

## 2026-11-05 (automatic)
- Tested proposal A160: rejected. A160 vs a3: beat it in 4/13 walk-forward years, CAGR 8.71% vs 12.55% (needs +0.57), worst fall -16.15% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A161: rejected. A161 vs a3: beat it in 6/13 walk-forward years, CAGR 8.3% vs 12.55% (needs +0.57), worst fall -20.89% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A162: rejected. A162 vs a3: beat it in 5/13 walk-forward years, CAGR 8.16% vs 12.55% (needs +0.57), worst fall -14.48% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A163: rejected. A163 vs a3: beat it in 7/13 walk-forward years, CAGR 7.7% vs 12.55% (needs +0.57), worst fall -19.75% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A164: rejected. A164 vs a3: beat it in 3/13 walk-forward years, CAGR 4.88% vs 12.55% (needs +0.57), worst fall -16.19% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A165: rejected. A165 vs a3: beat it in 6/13 walk-forward years, CAGR 8.32% vs 12.55% (needs +0.57), worst fall -18.3% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A166: rejected. A166 vs a3: beat it in 5/13 walk-forward years, CAGR 7.37% vs 12.55% (needs +0.57), worst fall -10.64% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A167: rejected. A167 vs a3: beat it in 4/13 walk-forward years, CAGR 6.33% vs 12.55% (needs +0.57), worst fall -15.83% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A168: rejected. A168 vs a3: beat it in 7/13 walk-forward years, CAGR 10.47% vs 12.55% (needs +0.57), worst fall -13.55% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A169: rejected. A169 vs a3: beat it in 6/13 walk-forward years, CAGR 12.66% vs 12.55% (needs +0.57), worst fall -11.7% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A170: rejected. A170 vs a3: beat it in 3/13 walk-forward years, CAGR 4.26% vs 12.55% (needs +0.57), worst fall -18.37% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A171: rejected. A171 vs a3: beat it in 5/13 walk-forward years, CAGR 8.65% vs 12.55% (needs +0.57), worst fall -19.09% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A172: rejected. A172 vs a3: beat it in 5/13 walk-forward years, CAGR 6.23% vs 12.55% (needs +0.57), worst fall -16.61% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A173: rejected. A173 vs a3: beat it in 4/13 walk-forward years, CAGR 6.76% vs 12.55% (needs +0.57), worst fall -17.51% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A174: rejected. A174 vs a3: beat it in 4/13 walk-forward years, CAGR 4.57% vs 12.55% (needs +0.57), worst fall -19.04% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A175: rejected. A175 vs a3: beat it in 3/13 walk-forward years, CAGR 9.86% vs 12.55% (needs +0.57), worst fall -14.06% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A176: rejected. A176 vs a3: beat it in 6/13 walk-forward years, CAGR 9.01% vs 12.55% (needs +0.57), worst fall -14.8% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A177: rejected. A177 vs a3: beat it in 6/13 walk-forward years, CAGR 8.32% vs 12.55% (needs +0.57), worst fall -10.04% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A178: rejected. A178 vs a3: beat it in 7/13 walk-forward years, CAGR 8.85% vs 12.55% (needs +0.57), worst fall -16.68% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A179: rejected. A179 vs a3: beat it in 4/13 walk-forward years, CAGR 6.72% vs 12.55% (needs +0.57), worst fall -17.92% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A180: rejected. A180 vs a3: beat it in 7/13 walk-forward years, CAGR 6.85% vs 12.55% (needs +0.57), worst fall -17.87% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A181: rejected. A181 vs a3: beat it in 4/13 walk-forward years, CAGR 9.14% vs 12.55% (needs +0.57), worst fall -16.93% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A182: rejected. A182 vs a3: beat it in 1/13 walk-forward years, CAGR 6.78% vs 12.55% (needs +0.57), worst fall -17.01% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A183: rejected. A183 vs a3: beat it in 5/13 walk-forward years, CAGR 8.11% vs 12.55% (needs +0.58), worst fall -16.9% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A184: rejected. A184 vs a3: beat it in 5/13 walk-forward years, CAGR 7.06% vs 12.55% (needs +0.58), worst fall -17.98% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A185: rejected. A185 vs a3: beat it in 8/13 walk-forward years, CAGR 9.42% vs 12.55% (needs +0.58), worst fall -24.56% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A186: rejected. A186 vs a3: beat it in 4/13 walk-forward years, CAGR 7.17% vs 12.55% (needs +0.58), worst fall -4.81% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A187: rejected. A187 vs a3: beat it in 5/13 walk-forward years, CAGR 6.26% vs 12.55% (needs +0.58), worst fall -2.44% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A188: rejected. A188 vs a3: beat it in 6/13 walk-forward years, CAGR 6.79% vs 12.55% (needs +0.58), worst fall -1.03% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A189: rejected. A189 vs a3: beat it in 6/13 walk-forward years, CAGR 7.03% vs 12.55% (needs +0.58), worst fall -3.29% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A190: rejected. A190 vs a3: beat it in 7/13 walk-forward years, CAGR 7.25% vs 12.55% (needs +0.58), worst fall -0.54% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A191: rejected. A191 vs a3: beat it in 7/13 walk-forward years, CAGR 7.8% vs 12.55% (needs +0.58), worst fall -2.79% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A192: rejected. A192 vs a3: beat it in 5/13 walk-forward years, CAGR 7.47% vs 12.55% (needs +0.58), worst fall -2.27% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A193: rejected. A193 vs a3: beat it in 4/13 walk-forward years, CAGR 6.39% vs 12.55% (needs +0.58), worst fall -11.22% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A194: rejected. A194 vs a3: beat it in 8/13 walk-forward years, CAGR 8.96% vs 12.55% (needs +0.58), worst fall -5.03% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A195: rejected. A195 vs a3: beat it in 3/13 walk-forward years, CAGR 4.78% vs 12.55% (needs +0.58), worst fall -10.37% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A196: rejected. A196 vs a3: beat it in 4/13 walk-forward years, CAGR 4.93% vs 12.55% (needs +0.58), worst fall -11.68% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A197: rejected. A197 vs a3: beat it in 6/13 walk-forward years, CAGR 8.63% vs 12.55% (needs +0.58), worst fall -13.31% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A198: rejected. A198 vs a3: beat it in 4/13 walk-forward years, CAGR 6.68% vs 12.55% (needs +0.58), worst fall -12.72% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A199: rejected. A199 vs a3: beat it in 3/13 walk-forward years, CAGR 5.86% vs 12.55% (needs +0.58), worst fall -7.5% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A200: rejected. A200 vs a3: beat it in 6/13 walk-forward years, CAGR 8.74% vs 12.55% (needs +0.58), worst fall -11.24% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A201: rejected. A201 vs a3: beat it in 4/13 walk-forward years, CAGR 4.88% vs 12.55% (needs +0.58), worst fall -9.49% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A202: rejected. A202 vs a3: beat it in 3/13 walk-forward years, CAGR 4.66% vs 12.55% (needs +0.58), worst fall -10.77% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A203: rejected. A203 vs a3: beat it in 5/13 walk-forward years, CAGR 5.32% vs 12.55% (needs +0.58), worst fall -7.8% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A204: rejected. A204 vs a3: beat it in 7/13 walk-forward years, CAGR 7.8% vs 12.55% (needs +0.58), worst fall -1.52% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A205: rejected. A205 vs a3: beat it in 5/13 walk-forward years, CAGR 7.03% vs 12.55% (needs +0.58), worst fall -13.16% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A206: rejected. A206 vs a3: beat it in 5/13 walk-forward years, CAGR 8.18% vs 12.55% (needs +0.58), worst fall -15.53% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A207: rejected. A207 vs a3: beat it in 6/13 walk-forward years, CAGR 8.5% vs 12.55% (needs +0.58), worst fall -11.95% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A208: rejected. A208 vs a3: beat it in 5/13 walk-forward years, CAGR 6.63% vs 12.55% (needs +0.58), worst fall -10.48% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A209: rejected. A209 vs a3: beat it in 6/13 walk-forward years, CAGR 8.28% vs 12.55% (needs +0.58), worst fall -14.62% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A210: rejected. A210 vs a3: beat it in 3/13 walk-forward years, CAGR 3.42% vs 12.55% (needs +0.58), worst fall -14.91% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A211: rejected. A211 vs a3: beat it in 2/13 walk-forward years, CAGR 2.75% vs 12.55% (needs +0.58), worst fall -26.94% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A212: rejected. A212 vs a3: beat it in 3/13 walk-forward years, CAGR 1.74% vs 12.55% (needs +0.58), worst fall -19.77% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A213: rejected. A213 vs a3: beat it in 8/13 walk-forward years, CAGR 5.72% vs 12.55% (needs +0.58), worst fall -13.7% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A214: rejected. A214 vs a3: beat it in 6/13 walk-forward years, CAGR 4.35% vs 12.55% (needs +0.58), worst fall -17.95% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A215: rejected. A215 vs a3: beat it in 3/13 walk-forward years, CAGR 4.6% vs 12.55% (needs +0.58), worst fall -14.0% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A216: rejected. A216 vs a3: beat it in 6/13 walk-forward years, CAGR 6.34% vs 12.55% (needs +0.58), worst fall -13.95% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A217: rejected. A217 vs a3: beat it in 4/13 walk-forward years, CAGR 5.39% vs 12.55% (needs +0.58), worst fall -6.58% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A218: rejected. A218 vs a3: beat it in 2/13 walk-forward years, CAGR 7.13% vs 12.55% (needs +0.58), worst fall -18.41% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A219: rejected. A219 vs a3: beat it in 2/13 walk-forward years, CAGR 4.99% vs 12.55% (needs +0.58), worst fall -17.61% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A220: rejected. A220 vs a3: beat it in 7/13 walk-forward years, CAGR 6.69% vs 12.55% (needs +0.58), worst fall -8.24% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A221: rejected. A221 vs a3: beat it in 6/13 walk-forward years, CAGR 6.9% vs 12.55% (needs +0.58), worst fall -4.22% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A222: rejected. A222 vs a3: beat it in 4/13 walk-forward years, CAGR 5.16% vs 12.55% (needs +0.58), worst fall -17.78% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A223: rejected. A223 vs a3: beat it in 6/13 walk-forward years, CAGR 7.53% vs 12.55% (needs +0.59), worst fall -1.54% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A224: rejected. A224 vs a3: beat it in 4/13 walk-forward years, CAGR 5.5% vs 12.55% (needs +0.59), worst fall -12.77% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A225: rejected. A225 vs a3: beat it in 3/13 walk-forward years, CAGR 6.67% vs 12.55% (needs +0.59), worst fall -18.61% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A226: rejected. A226 vs a3: beat it in 7/13 walk-forward years, CAGR 9.01% vs 12.55% (needs +0.59), worst fall -15.54% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A227: rejected. A227 vs a3: beat it in 3/13 walk-forward years, CAGR 8.12% vs 12.55% (needs +0.59), worst fall -15.51% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A228: rejected. A228 vs a3: beat it in 4/13 walk-forward years, CAGR 5.09% vs 12.55% (needs +0.59), worst fall -24.91% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A229: rejected. A229 vs a3: beat it in 3/13 walk-forward years, CAGR 7.34% vs 12.55% (needs +0.59), worst fall -10.89% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A230: rejected. A230 vs a3: beat it in 6/13 walk-forward years, CAGR 7.47% vs 12.55% (needs +0.59), worst fall -14.43% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A231: rejected. A231 vs a3: beat it in 4/13 walk-forward years, CAGR 5.89% vs 12.55% (needs +0.59), worst fall -10.44% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A232: rejected. A232 vs a3: beat it in 5/13 walk-forward years, CAGR 13.25% vs 12.55% (needs +0.59), worst fall -11.48% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A233: rejected. A233 vs a3: beat it in 4/13 walk-forward years, CAGR 5.7% vs 12.55% (needs +0.59), worst fall -20.21% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A234: rejected. A234 vs a3: beat it in 5/13 walk-forward years, CAGR 9.15% vs 12.55% (needs +0.59), worst fall -16.58% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A235: rejected. A235 vs a3: beat it in 8/13 walk-forward years, CAGR 8.47% vs 12.55% (needs +0.59), worst fall -8.67% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A236: rejected. A236 vs a3: beat it in 7/13 walk-forward years, CAGR 10.16% vs 12.55% (needs +0.59), worst fall -13.36% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A237: rejected. A237 vs a3: beat it in 6/13 walk-forward years, CAGR 9.07% vs 12.55% (needs +0.59), worst fall -13.06% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A238: rejected. A238 vs a3: beat it in 5/13 walk-forward years, CAGR 6.94% vs 12.55% (needs +0.59), worst fall -16.55% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A239: rejected. A239 vs a3: beat it in 9/13 walk-forward years, CAGR 7.07% vs 12.55% (needs +0.59), worst fall -20.82% vs -10.71%, gate FAIL

## 2026-11-06 (automatic)
- Tested proposal A240: rejected. A240 vs a3: beat it in 6/13 walk-forward years, CAGR 8.42% vs 12.55% (needs +0.59), worst fall -13.57% vs -10.71%, gate FAIL

## 2026-11-07 (automatic)
- Weekly session aborted: sandbox tests failed. Live system untouched.
