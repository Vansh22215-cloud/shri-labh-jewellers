# ATLAS Strategy Foundry - results (19 Nov 2026)

Protocol: FOUNDRY_PROTOCOL.md (+ addenda 1-2, each committed before its run). Script: foundry.py.
All numbers after verified Zerodha costs + 20.8% tax, ₹51,000 account, 1% risk, 25% cap.

## Run 1: 336 strategies (12 entries x 4 filters x 7 short exits) - 0 passed development
Short trades (10-20 days) earned +0.5-0.9% a trade before tax: less than the ₹51,000 account's round-trip cost (~0.75%) plus tax. Best standalone: 8.7% a year (squeeze breakout, trailing exit).

## Run 2: 640 strategies (16 entries x 4 filters x 10 exits incl. long holds)
- Development survivors (standalone >= NIFTY fund 13.5%, fall >= -30%, and +1 point next to the live system): **1**
- That one: *within 2% of the 52-week high with top-20% strength, only when NIFTY is above its 200-day average; 4 ATR stop, 5R target, up to 120 days* - development 17.3% a year alone (fall -29.8%), +2.8 points next to the live system.
- Luck: beat random OTHER stocks on the same days 20 of 20 (its stock choice adds value); lost to random days in the same stocks 0 of 20 (timing adds nothing - the same lesson as VANTAGE).
- **Holdout (Nov 2023 - Oct 2026): failed** - 4.5% a year alone (NIFTY fund 7.8%); next to the live system 8.9% vs 12.5% without it; better in 6 of 14 years.

## Lesson: the exit matters more than the entry at this account size
The long exit (4 ATR stop, 5R target, 120 days) turned ordinary entries into +7-10% a trade (before tax). Best standalone (development):

| Strategy | Dev alone (growth / fall) | Next to live system (+points) | Trades | Win % | Avg / trade |
|---|---|---|---|---|---|
| within 2% of 52-week high, top-20% strength | NIFTY above 200-day | target 5R, stop 4 ATR, 120 days | 17.33% / -29.79% | +2.82 | 8,352 | 45.1 | +7.96% |
| within 2% of 52-week high, top-20% strength | no filter | target 5R, stop 4 ATR, 120 days | 16.71% / -32.08% | -0.60 | 9,084 | 46.1 | +8.13% |
| within 2% of 52-week high, top-20% strength | stock above 200-day | target 5R, stop 4 ATR, 120 days | 16.71% / -32.08% | -0.60 | 9,084 | 46.1 | +8.13% |
| strength leader pulling back 3 days | stock above 200-day | target 5R, stop 4 ATR, 120 days | 15.34% / -42.94% | +0.32 | 4,802 | 48.5 | +9.38% |
| strength leader pulling back 3 days | no filter | target 5R, stop 4 ATR, 120 days | 15.26% / -43.19% | +0.03 | 4,818 | 48.4 | +9.33% |
| strength leader pulling back 3 days | breadth above 50% | target 5R, stop 4 ATR, 120 days | 15.03% / -35.11% | +1.03 | 3,756 | 48.3 | +10.16% |
| strength leader pulling back 3 days | NIFTY above 200-day | target 5R, stop 4 ATR, 120 days | 14.85% / -45.04% | -0.25 | 3,905 | 47.5 | +9.44% |
| breakout 52-week high | NIFTY above 200-day | target 5R, stop 4 ATR, 120 days | 14.46% / -34.97% | +0.18 | 10,802 | 46.3 | +7.22% |
| breakout 52-week high | breadth above 50% | target 5R, stop 4 ATR, 120 days | 14.13% / -32.74% | +1.75 | 10,415 | 47.2 | +7.58% |
| breakout 52-week high | no filter | target 5R, stop 4 ATR, 120 days | 13.63% / -36.63% | -0.92 | 11,402 | 46.8 | +7.31% |

Tried so far: 976 strategies; passed every step: 0. The Foundry keeps running weekly (fresh trades from 20 Nov 2026 are the final judge).
