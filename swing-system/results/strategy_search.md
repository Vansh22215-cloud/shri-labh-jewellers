# Strategy search (21 Nov 2026 20:16 IST) - goal ₹10,000 a day

**Data: Kite 5-minute candles only - 2,772 stocks, 2,923 days, 2015-02-03 to 2026-11-20. NIFTY options are an ESTIMATE (no expired option candles on Kite). Chosen before 2024, checked on 2024 onwards.**

## Stocks - best setting of each strategy

| Strategy | Setting | Before 2024 avg/day | Recent avg/day | Recent days in profit | Recent worst day | Passes |
|---|---|---|---|---|---|---|
| gap_fade | stop 0.015, target 0.03 | ₹+206 | ₹+11 | 47.5% | ₹-4,624 | ✅ |
| trend_1015 | stop 0.005, target 0.03 | ₹-326 | ₹-212 | 27.4% | ₹-1,272 | ❌ |
| late_momo | stop 0.015, target 0.03 | ₹-133 | ₹-222 | 39.1% | ₹-3,084 | ❌ |
| gap_go | stop 0.005, target 0.03 | ₹-301 | ₹-276 | 27.2% | ₹-1,885 | ❌ |
| rebound | stop 0.01, target 0.03 | ₹-136 | ₹-312 | 30.4% | ₹-3,254 | ❌ |
| pdh_break | stop 0.005, target 0.03 | ₹-533 | ₹-406 | 28.9% | ₹-1,918 | ❌ |
| orb | stop 0.005, target 0.02 | ₹-611 | ₹-469 | 34.4% | ₹-1,927 | ❌ |
| vwap_revert | stop 0.005, target 0.03 | ₹-486 | ₹-524 | 25.2% | ₹-1,902 | ❌ |

## NIFTY options (estimate) - best setting of each strategy

| Strategy | Setting | Before 2024 avg/day | Recent avg/day | Recent days in profit | Recent worst day | Passes |
|---|---|---|---|---|---|---|
| n_pdh_break | stop 0.2, target 1.0, vix False | ₹+282 | ₹+197 | 30.2% | ₹-6,584 | ✅ |
| n_orb | stop 0.3, target 1.0, vix True | ₹+249 | ₹+135 | 39.2% | ₹-6,211 | ✅ |
| n_trend_1015 | stop 0.2, target 1.0, vix True | ₹+93 | ₹+114 | 18.2% | ₹-2,486 | ✅ |
| n_gap_fade | stop 0.2, target 1.0, vix False | ₹+47 | ₹+20 | 15.3% | ₹-6,262 | ✅ |
| n_ema_cross | stop 0.2, target 1.0, vix False | ₹+221 | ₹-110 | 26.5% | ₹-6,300 | ❌ |

## Chosen for the practice trader

- Stocks: gap_fade (stop 0.015, target 0.03)
- NIFTY options: n_pdh_break (stop 0.2, target 1.0)
- Together, recent years: ₹+208 a day at today's size; ₹10,000 a day would need 48.1x the size; ₹50,800 allows 1.6x stocks / 2.08x options -> expected ≈ ₹427 a day (goal ₹10,000), day loss limit ₹12,500.
