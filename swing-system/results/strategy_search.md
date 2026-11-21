# Strategy search (21 Nov 2026 23:58 IST) - goal ₹10,000 a day

**Data: Kite 5-minute candles only - 2,772 stocks, 2,923 days, 2015-02-03 to 2026-11-20. NIFTY options are an ESTIMATE (no expired option candles on Kite). Chosen before 2024, checked on 2024 onwards.**

## Stocks - best setting of each strategy

| Strategy | Setting | Before 2024 avg/day | Recent avg/day | Recent days in profit | Recent worst day | Passes |
|---|---|---|---|---|---|---|
| gap_fade | stop 0.015, target 0.03 | ₹+205 | ₹+9 | 47.7% | ₹-4,624 | ✅ |
| rs_divergence | stop 0.015, target 0.03 | ₹-372 | ₹-181 | 43.1% | ₹-4,613 | ❌ |
| trend_1015 | stop 0.005, target 0.03 | ₹-326 | ₹-212 | 27.4% | ₹-1,272 | ❌ |
| late_momo | stop 0.015, target 0.03 | ₹-133 | ₹-222 | 39.1% | ₹-3,084 | ❌ |
| trend_pullback | stop 0.015, target 0.03 | ₹-668 | ₹-268 | 42.8% | ₹-4,654 | ❌ |
| gap_go | stop 0.005, target 0.03 | ₹-302 | ₹-269 | 27.4% | ₹-1,885 | ❌ |
| rebound | stop 0.01, target 0.03 | ₹-137 | ₹-313 | 30.2% | ₹-3,254 | ❌ |
| pdh_break | stop 0.005, target 0.03 | ₹-533 | ₹-406 | 28.9% | ₹-1,918 | ❌ |
| orb | stop 0.005, target 0.02 | ₹-611 | ₹-469 | 34.4% | ₹-1,927 | ❌ |
| vwap_revert | stop 0.005, target 0.03 | ₹-486 | ₹-524 | 25.2% | ₹-1,902 | ❌ |

## NIFTY options (estimate) - best setting of each strategy

| Strategy | Setting | Before 2024 avg/day | Recent avg/day | Recent days in profit | Recent worst day | Passes |
|---|---|---|---|---|---|---|
| n_trend_pullback | stop 0.2, target 2.0, vix False, exit keep | ₹+523 | ₹+418 | 40.8% | ₹-6,295 | ✅ |
| n_pdh_break | stop 0.2, target 2.0, vix False, exit keep | ₹+456 | ₹+388 | 39.8% | ₹-6,584 | ✅ |
| n_orb | stop 0.3, target 2.0, vix False, exit keep | ₹+458 | ₹+244 | 45.1% | ₹-6,220 | ✅ |
| n_ema_cross | stop 0.2, target 2.0, vix False, exit keep | ₹+478 | ₹+167 | 38.7% | ₹-6,300 | ✅ |
| n_trend_1015 | stop 0.2, target 2.0, vix False, exit keep | ₹+258 | ₹+17 | 21.6% | ₹-3,146 | ✅ |
| n_gap_fade | stop 0.3, target 2.0, vix False, exit keep | ₹+83 | ₹-2 | 25.4% | ₹-6,184 | ❌ |

## Stocks with the owner's 1% stop-loss (only these can be switched on)

Switched on only if it earns at least ₹100 a day both before 2024 and from 2024.

| Strategy | Target | Before 2024 avg/day | Recent avg/day | Recent days in profit | Recent worst day | Usable |
|---|---|---|---|---|---|---|
| gap_fade | 0.03 | ₹+131 | ₹+47 | 44.6% | ₹-3,255 | ❌ |
| trend_1015 | 0.03 | ₹-344 | ₹-142 | 39.5% | ₹-2,191 | ❌ |
| gap_go | 0.03 | ₹-379 | ₹-220 | 38.3% | ₹-3,256 | ❌ |
| late_momo | 0.03 | ₹-137 | ₹-225 | 35.7% | ₹-2,170 | ❌ |
| rs_divergence | 0.03 | ₹-380 | ₹-271 | 39.4% | ₹-3,252 | ❌ |
| trend_pullback | 0.03 | ₹-699 | ₹-282 | 41.4% | ₹-3,254 | ❌ |
| rebound | 0.03 | ₹-137 | ₹-313 | 30.2% | ₹-3,254 | ❌ |
| orb | 0.02 | ₹-679 | ₹-499 | 35.8% | ₹-3,254 | ❌ |
| pdh_break | 0.03 | ₹-589 | ₹-517 | 37.6% | ₹-3,277 | ❌ |
| vwap_revert | 0.03 | ₹-539 | ₹-581 | 36.4% | ₹-3,347 | ❌ |

## Every stock strategy by market condition (1% stop) - D179

Allowed where it earned ≥ ₹100 a trade before 2024 (clearly: t ≥ 2, ≥ 100 trades) AND from 2024 (≥ 40 trades). Condition = trade with / against NIFTY's move so far + yesterday's India VIX.

| Strategy | Target | Market | VIX | Trades before 2024 | ₹/trade before | Trades 2024+ | ₹/trade 2024+ | t | Allowed |
|---|---|---|---|---|---|---|---|---|---|
| gap_fade | 0.03 | NIFTY flat | VIX below 14 | 4,090 | ₹-15 | 2,831 | ₹+16 | -0.8 | ❌ |
| gap_fade | 0.01 | NIFTY flat | VIX 20+ | 4,906 | ₹-18 | 324 | ₹-16 | -1.4 | ❌ |
| gap_fade | 0.03 | NIFTY flat | VIX 14-20 | 8,193 | ₹+45 | 2,753 | ₹-19 | 3.2 | ❌ |
| rebound | 0.03 | against NIFTY | VIX 14-20 | 472 | ₹-19 | 125 | ₹+151 | -0.3 | ❌ |
| rebound | 0.02 | against NIFTY | VIX 14-20 | 472 | ₹-25 | 125 | ₹+249 | -0.5 | ❌ |
| gap_fade | 0.02 | with NIFTY | VIX below 14 | 982 | ₹+44 | 1,068 | ₹-26 | 1.3 | ❌ |
| late_momo | 0.03 | with NIFTY | VIX 20+ | 8,777 | ₹-31 | 683 | ₹+74 | -2.9 | ❌ |
| gap_fade | 0.01 | with NIFTY | VIX below 14 | 982 | ₹-32 | 1,068 | ₹-29 | -1.2 | ❌ |
| gap_fade | 0.02 | NIFTY flat | VIX below 14 | 4,090 | ₹-40 | 2,831 | ₹-11 | -2.4 | ❌ |
| gap_fade | 0.02 | with NIFTY | VIX 20+ | 3,457 | ₹-35 | 504 | ₹-41 | -1.8 | ❌ |
| late_momo | 0.02 | with NIFTY | VIX 20+ | 8,777 | ₹-41 | 683 | ₹+27 | -4.2 | ❌ |
| gap_fade | 0.02 | NIFTY flat | VIX 14-20 | 8,193 | ₹+12 | 2,753 | ₹-43 | 1.0 | ❌ |
| gap_fade | 0.03 | against NIFTY | VIX 20+ | 1,841 | ₹-34 | 327 | ₹-43 | -1.1 | ❌ |
| gap_fade | 0.03 | with NIFTY | VIX below 14 | 982 | ₹+35 | 1,068 | ₹-44 | 0.9 | ❌ |
| gap_fade | 0.02 | against NIFTY | VIX 14-20 | 2,008 | ₹-55 | 521 | ₹+14 | -1.6 | ❌ |
| late_momo | 0.03 | with NIFTY | VIX 14-20 | 14,678 | ₹-26 | 4,042 | ₹-55 | -3.4 | ❌ |
| gap_fade | 0.03 | against NIFTY | VIX 14-20 | 2,008 | ₹-58 | 521 | ₹+26 | -1.6 | ❌ |
| late_momo | 0.02 | with NIFTY | VIX 14-20 | 14,678 | ₹-39 | 4,042 | ₹-61 | -5.6 | ❌ |
| rebound | 0.01 | against NIFTY | VIX 14-20 | 472 | ₹-62 | 125 | ₹+5 | -1.5 | ❌ |
| gap_fade | 0.02 | against NIFTY | VIX 20+ | 1,841 | ₹-26 | 327 | ₹-65 | -1.0 | ❌ |
| gap_fade | 0.03 | NIFTY flat | VIX 20+ | 4,906 | ₹+90 | 324 | ₹-73 | 4.7 | ❌ |
| trend_1015 | 0.03 | NIFTY flat | VIX 14-20 | 8,306 | ₹-73 | 2,211 | ₹-30 | -6.1 | ❌ |
| late_momo | 0.01 | with NIFTY | VIX 20+ | 8,777 | ₹-73 | 683 | ₹-42 | -9.0 | ❌ |
| gap_fade | 0.01 | NIFTY flat | VIX below 14 | 4,090 | ₹-70 | 2,831 | ₹-74 | -5.2 | ❌ |
| gap_fade | 0.02 | NIFTY flat | VIX 20+ | 4,906 | ₹+48 | 324 | ₹-74 | 3.0 | ❌ |

No stock strategy earned in any market condition in both periods.

## Chosen for the practice trader

- Stocks: none passed - stock trades stay paused
- NIFTY options (best): n_trend_pullback (stop 0.2, target 2.0)
- NIFTY strategies that may fire (first signal takes the slot, max 2 a day): n_trend_pullback (stop 0.2, target 2.0, exit keep), n_ema_cross (stop 0.2, target 2.0, exit keep), n_orb (stop 0.3, target 2.0, exit keep), n_pdh_break (stop 0.2, target 2.0, exit keep)
- Expected at the live size (₹1,000 a stock trade, ₹2,500 an option trade, ₹3,000 day loss limit): ≈ ₹+348 a day from 2024 (goal ₹10,000)
