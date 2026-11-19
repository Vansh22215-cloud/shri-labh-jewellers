# ATLAS Strategy Foundry - protocol (pre-registered 19 Nov 2026, before any run)

Owner, 19 Nov: "entirely new kinds of strategy still need a human to design them - until we have Claude, do this
at full capacity" (Claude until 3 Dec 2026; after that the Foundry must keep running by itself).

## What the Foundry builds
Complete strategies = ENTRY x FILTER x EXIT, assembled automatically from building blocks.
- Universe: point-in-time top-300 by money traded (monthly, delisted stocks included), the live universe (D144).
- Signal at a day's close, entry at the NEXT open (no look-ahead). Only the first day a condition turns true counts.
- ENTRY families: breakout of the N-day high (20/55/252); volatility squeeze then 20-day breakout; pullback to the
  50-day average in an uptrend; 2-day RSI dip in an uptrend (< 5 / < 10); 3+ down days then a strong close in an
  uptrend; gap-up of 3%+ closing strong on 2x volume; volume surge (3x) up-day of 4%+ closing near the high;
  relative-strength leader (top 10% 6-month return) pulling back for 3 days; within 2% of the 52-week high with
  top-20% strength.
- FILTERS: none; NIFTY above its 200-day average; stock above its 200-day average; market breadth above 50%.
- EXITS: (a) stop k x ATR (k = 2, 3) + time limit T (10, 20 days); (b) trailing: close below the 20-day average
  (or 10-day for short entries) + 3 x ATR stop + 60-day limit; (c) target 2R or 3R + 2 x ATR stop + 20 days.
  Stops gap-adjusted (a gap below the stop fills at the open).

## The bar (every number after verified Zerodha costs + 20.8% short-term tax, ₹51,000, 1% risk, 25% cap)
1. DEVELOPMENT (signals before 1 Nov 2023), screening all strategies:
   a) standalone account growth at least the NIFTY fund's on the same dates (13.5% a year), worst fall no deeper
      than -30%, at least 150 trades;
   b) INCREMENTAL: added to the current live system (VANTAGE live setup + live dip-buy) it raises the account's
      yearly growth by >= 1 point with the worst fall no more than 2 points deeper.
2. LUCK: the same strategy with entries moved to random days in the same stocks and years (same count, same
   exits) - 20 worlds; the real one must beat at least 18 (development, standalone growth).
3. HOLDOUT (Nov 2023 - Oct 2026), only for the 10 best development survivors (ranked by incremental gain):
   standalone >= NIFTY fund on the same dates (7.8%) AND incremental +1 point with the fall no more than 2 deeper,
   AND better than without it in at least 60% of single years (incremental, top-300).
4. FRESH (signals from 20 Nov 2026): once 100+ fresh trades exist, not worse than the current system.
A strategy passing 1-3 is proposed to the owner (as a SHADOW strategy first - silent live record), never sent as tips
without passing 4 and the owner's yes. Multiple testing is the main risk: the luck test and the untouched holdout
exist for that, and the number of strategies tried is always reported next to the number that passed.
