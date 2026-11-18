# Live review: every tip, one by one (append-only, dated)
**Source:** `swing-system/journal/all_tips.csv` and `all_tips.md`, written every evening by `swing/tracker.py`.

## 18 Nov 2026 (first full tracking run)
- **Strategy tips "a3"** (the older strategy engine, sent since 6 Nov):
  - 16 bought inside the zone, all still open.
  - Average **−1.75%**; worst AVALON −12.4%, RPTECH −9.8%, EMIL −6.3%; best GESHIP +5.7%.
  - The 6 "a3" ideas recorded but NOT sent (shadow, 4–5 Nov): average +7.2%. That is the same strategy and only 2 days earlier, so this is noise at n = 5. Watch it.
- **Strategy tips "a1"** (2–3 Nov):
  - ICICIBANK hit target 1, **+13.1%** (closed).
  - FEDERALBNK is +6.9% (open).
- **Hourly scan ideas:**
  - 18 bought, average −1.07%.
  - Mostly the same stocks as the a3 tips.
  - SHANTIGOLD −11.2% and EBGNG −8.6% are the worst.
- **VANTAGE** (17–18 Nov):
  - 16 trend tips and 1 breakout.
  - After 0–1 day: +0.2% on average; GREAVESCOT +9.5%.
- **Company of the day** (research picks, not trades): 5 of 12 up, average −1.1%.
- **Stops:** no stop-loss or target hit yet except ICICIBANK's target.

**Watch items for the coming weeks:**
1. Does "a3" keep underperforming while VANTAGE does better?
2. Does the hourly scan add anything beyond the a3 tips? It mostly repeats them.
3. Do skipped entries (opened outside the zone) do better or worse than the bought ones?

## 18 Nov 2026 (later): 13-year mistake census (`mistake_census.json`)
Share of all money lost on VANTAGE trades, holdout (all stocks / top-300):

| Cause | All stocks | Top-300 |
|---|---|---|
| Gave back a profit (up ≥ 3% then lost) | 38% | 20% |
| Market fell 3%+ | 21% | 23% |
| Slow drift | 13% | 10% |
| Never worked | 12% | 8% |
| Results during the trade | 7% (results dates for 506 companies only) | 31% |
| Gap through the stop | 7% | 5% |
| Fast stop | 1% | 3% |

**Checked, no fix:**
- **Selling trend trades when NIFTY crosses below its 50-day average** (development): those trades average +2.15% instead of +4.72%.
- **Selling before results:** the average results reaction is +0.1 to +0.3% (round 18 notes).

**Testing:** round 20, protecting profits with a break-even stop after +5% or +8%.

## 18 Nov 2026: Truth Engine luck checks (Project ALPHA input)
- **Luck check 1** (random DAYS inside VANTAGE's own stocks, same holding times):
  - VANTAGE beats random in 96–100% of worlds before 2023.
  - In the last 3 years only 72% (top-300) and 5.5% (all stocks).
  - **Timing adds little recently.**
- **Luck check 2** (random STOCKS on random days from the same universe):
  - VANTAGE beats random in 100% of 200 worlds in every period, by +2 to +6 points a trade.
  - Holdout all stocks: VANTAGE +2.63% vs random −0.89%.
  - **The edge is stock choice.**
- **Consequence:** research priority moves to stock choice (which facts in VANTAGE's choice carry the edge; whether more stocks of the same quality exist), not timing.

## 19 Nov 2026, 00:15 IST check-in
- No new live record yet. The live system's first evening run of the tracker and Learner is 19 Nov at about 18:40 IST, after the first full trading day with ₹51,000.
- The local replay is unchanged: 17 VANTAGE tips, open average +0.2%.
- **Backlog 13 progress:**
  - **(a) done:** fingerprint = strong, near-high stocks, about 3/4 of the edge.
  - **(b) answered:** about 7 matching stocks a day, so money, not candidates, is the limit.
  - **(c) answered:** VANTAGE's own timing adds about 0.75 points a trade over fingerprint-matched random picks, so it is kept.
- **Next research item:** start from the first live evening (beliefs B2 and B6 checks).

## 19 Nov 2026, 03:30 IST check-in
- No new live record (first live evening run is 19 Nov about 18:40 IST). Replay unchanged: 17 VANTAGE tips, open +0.2%.
- ATLAS parts added since the last check-in: idea ledger, missed-movers section, ranked research queue, 7-stage promotion, weekly portfolio risk, crash scenario (round 24, survives; a 10% market gap = about 15% loss in one morning).
- **Backlog 15 (missed big risers, top of the new research queue) explored on development data only:** the missed risers' look at the start (strong, 10-30% below the 52-week high, 20-day high on 2x volume) gives 7,057 cases with a 20-day result of +1.2% vs +1.5% for any stock, and is worse in 10 of 12 years. The big risers are only "obvious" in hindsight. Closed, no test (holdout not looked at). The research queue now pushes it down.
- Next: backlog 14 (live belief checks) from the first live evening.
