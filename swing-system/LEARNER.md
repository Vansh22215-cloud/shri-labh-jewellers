# The two engines (owner, 18 Nov 2026)
> "One, where trades are found, and the other, where whichever trade is given is tracked and we learn from it: what's right, what's wrong and everything."

## Engine 1: the Finder (finds trades)
VANTAGE (live, 3:20 pm buy-now, 3:40 pm close scan), ADD MORE, the monthly basket, and the other tip channels. A rule changes only after a pre-registered 13-year test passes and the owner says yes.

## Engine 2: the Learner (learns from every trade given)
It runs every evening after the price update (`scripts/run_nightly.py`).

1. **Track every idea:** `swing/tracker.py` → `journal/all_tips.csv`.
   - Every source is covered: strategy tips, hourly scan, VANTAGE, the live engine, live and 3:20 pm alerts, company of the day, the monthly basket, and the silent promoter record.
   - One rule set: bought or skipped, stop-loss or target, result after 0.35% costs, open ideas at today's close.
2. **Understand each idea:** `swing/learning.py`.
   - **The situation on its day** (known that day only): market rising or falling, market calm or jumpy, the stock's liquidity, its distance from the 52-week high, results within 5 days, the weekday.
   - **Its journey:** the best and worst point since buying, and the result in units of risk.
3. **Live vs the test:** each VANTAGE type is judged against its 13-year profile (`vantage-ai/validation/tested_profile.json`: win %, average, typical best and worst point, stop rate).
   - After 20 closed tips the verdict is "on track", "watch" or "below expected" (outside the 90% expected range).
   - Before that, "early warning" if more than a quarter of open tips are already deeper than 90% of tested trades.
4. **When it works and when not:** the result by situation for every source → `journal/learning.md`.
5. **Mistakes: why each losing idea lost.** Every closed loss and every open idea down 3% or more gets one plain diagnosis:
   - never worked (a selection mistake)
   - gave back a profit (an exit mistake)
   - stopped out within 3 days (timing)
   - opened below the stop-loss (overnight risk)
   - the market fell 3%+ (not the stock)
   - a results shock
   - a slow drift

   It also reports repeat stocks (sent 3+ times, across channels) and skipped ideas (missed winners or avoided losses). When one cause explains 40%+ of a source's losses (≥ 10 losses), that becomes a research item.
6. **Lessons → research, never straight into tips:**
   - Gaps of ≥ 3 points between situations (≥ 10 ideas each) go to `journal/learning_queue.csv`.
   - The 3-hourly research check-in reads them, logs them in `vantage-ai/validation/LIVE_REVIEW.md`, and tests them on 13 years before anything changes.
7. **The owner hears:**
   - a short "📒 Weekly learning" message every Saturday, including the main mistake, the worst ideas and the repeat stocks;
   - an instant "⚠️ Learning check" only when a tip type is clearly below its tested range (once per type).

## The loop
The Finder sends a tip → the Learner tracks and explains it → its lessons become research items → passed tests (with the owner's yes) improve the Finder → repeat.

## Rule
Any new tip type must be added to `swing/tracker.py` in the same change that starts sending it.

## Privacy
Market ideas only. Nothing about the owner's trades, quantities, money or holdings is written or saved.

## Project ALPHA additions (18 Nov 2026, from the owner's input)
- **Truth Engine (adversarial):** luck checks against random worlds (`vantage-ai/validation/luck_check*.py`).
  - VANTAGE's edge is WHICH stocks it picks: it beats random stocks on random days in 100% of 200 worlds, every period.
  - It is not WHEN: timing inside the same stocks adds little since 2023.
  - Research now targets stock choice first.
- **Experience memory:** `vantage-ai/validation/experiments.json` lists every experiment ever tested (75), with its verdict and reason, plus the cross-cutting lessons. Never re-test a failed idea without a new reason.
- **Strategy lifecycle:** `swing-system/strategies/registry.json` lists every strategy (live / watch / shadow / candidate / retired) with its evidence. The Learner reports live results per strategy.
- **Market memory:** `vantage-ai/validation/situation_memory.json` covers 12 day types (NIFTY trend × calm/jumpy × breadth) with how VANTAGE tips did on each over 13 years.
  - The Learner tags every tip with its day type and names today's.
  - Panic days (falling, jumpy, weak breadth) were the best days in both periods.
- **Counterfactuals:** signals the scanner rejected (thin stock, kill switch) go to `data/private/vantage_rejected.csv` and are followed like every other idea ("rejected by VANTAGE"), as are blocked repeats and skipped zone tips.
- **Holdout caution:** the Nov 2023+ period has been the exam for about 70 ideas. Passes also need development, year-by-year and stress checks. The live record is the truly unseen test.
