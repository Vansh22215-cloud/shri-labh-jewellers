# Owner's three investigations (19 Nov 2026) - findings and evidence (no live change; waiting for approval)

## 1. Every charge, fee and tax, checked and applied

Source: zerodha.com/charges (fetched 19 Nov 2026); tax: Income-tax Act s.111A / s.112A as summarised by public tax guides (verify before filing).

| Item | Official | Test before | Test now | Where applied |
|---|---|---|---|---|
| Brokerage (delivery) | ₹0 | 0 | 0 | - |
| STT | 0.1% buy + 0.1% sell | 0.1% + 0.1% | same | every buy and sell value |
| NSE transaction | 0.00307% | 0.00297% | **0.00307%** | each side |
| SEBI | ₹10 / crore | same | same | each side |
| Stamp duty | 0.015% buy | same | same | buy value |
| GST | 18% on brokerage + SEBI + transaction | same | same | on those charges |
| DP charge | ₹15.34 per stock, per day it is sold, any quantity | ₹15.93 per lot | **₹15.34 once per stock per sale day** | each sale |
| AMC (BSDA, holdings < ₹4 lakh) | ₹0 | - | ₹0 | - |
| Slippage (not a fee, an assumption) | - | 0.1% each side | 0.1% each side | every buy and sell price |
| Short-term tax (s.111A, held < 1 year) | 20% + 4% cess | 20%, calendar year | **20.8%, financial year April-March**, losses offset and carried forward | yearly, on net realised profit |
| NIFTY fund long-term tax (s.112A) | 12.5% + 4% cess above ₹1.25 lakh gain | - | applied once at the sale | benchmark |

Not modelled (stated, not hidden): surcharge (only at high incomes), the basic-exemption benefit for low total income, advance-tax timing, Zerodha's female-holder DP discount, interest on idle cash (0%).

## 2. NIFTY on identical terms

Same ₹51,000, same first buy date and same last sale date as the system; NIFTY fully invested from day 1; total return = price + dividend yield (assumption 1.1-1.5% a year, the free data has no dividends) - 0.05% fund fee; stamp + DP on the fund; long-term tax at the sale.

| Setup / period (dates) | System after costs + tax | System, monthly capital | System before tax | NIFTY fund after tax (div 1.1 / 1.3 / 1.5%) | NIFTY price only |
|---|---|---|---|---|---|
| VANTAGE live setup, dev (2013-01-22 to 2024-02-15) | 14.4% (₹226,417), fall -20.1% | 14.9% | 17.1% | 13.3 / 13.5 / 13.7% (₹207,250) | 12.3% |
| VANTAGE live setup, holdout (2023-11-01 to 2026-10-29) | 11.9% (₹71,476), fall -24.4% | 14.4% | 15.1% | 7.6 / 7.8 / 8.0% (₹63,910) | 6.5% |
| VANTAGE + live dip-buy, dev (2013-01-14 to 2024-02-15) | 15.1% (₹242,251), fall -21.6% | 16.0% | 18.2% | 13.3 / 13.5 / 13.7% (₹208,049) | 12.4% |
| VANTAGE + live dip-buy, holdout (2023-11-01 to 2026-10-29) | 11.5% (₹70,622), fall -23.9% | 15.8% | 15.4% | 7.6 / 7.8 / 8.0% (₹63,910) | 6.5% |

Notes:
- The system is invested about 89-91% of the time on average; its idle cash earns 0% here (a liquid fund would add a little).
- NIFTY's worst fall in these windows: -38% (2013-2024, the 2020 crash) and -16% (2023-2026). The system's worst fall is measured at each sale (deeper intra-trade falls possible, round 24).
- **End-date sensitivity:** NIFTY rose about 10% between 29 Oct and 16 Nov 2026. Comparisons ending 18 Nov (as in my earlier answers, 10.9% a year) are not on identical dates; on the system's own last sale date (29 Oct) NIFTY made 6.5% a year (price) / 7.8% (total return, after tax).
- My earlier '13.5% / 11%' NIFTY figures were price-only and used different end dates.

## 3. Do changing behaviour groups improve selection, with membership from information before each trade only?

Every year the groups are re-fitted on trades signalled before that year only; groups are scored on trades closed before that year; that year's trades are predicted. Three memberships, all from the past.

| Membership | Top-300: spread / years + | All: spread / years + | Top-300 dev (rule vs now) | Top-300 holdout | All dev | All holdout | Luck worlds (top-300 holdout) | Bar |
|---|---|---|---|---|---|---|---|---|
| DYNAMIC (behaviour at the signal) | 1.42 / 9 of 11 | 2.57 / 9 of 11 | 13.5% vs 13.3% | 11.5% vs 8.1% | 35.0% vs 29.6% | 13.1% vs 2.2% | [10.4, 8.7, 8.2] | fail |
| PREVIOUS (group of the stock's previous trade) | 1.39 / 6 of 11 | 1.52 / 8 of 11 | 13.3% vs 13.3% | 12.0% vs 8.1% | 34.4% vs 29.6% | 0.8% vs 2.2% | [9.3, 10.6, 9.8] | fail |
| MODAL (the stock's usual group so far) | 1.79 / 9 of 11 | 1.16 / 9 of 11 | 13.6% vs 13.3% | 9.3% vs 8.1% | 34.7% vs 29.6% | -0.2% vs 2.2% | [8.3, 5.5, 9.1] | fail |

Account columns: yearly growth after verified costs + 20.8% tax, 'take the best group first when money is short', fixed ₹51,000 sizing, plain next-open VANTAGE trades (the lab's common base).

**Findings:**
- **The predictive value survives the strict test.** With groups re-learned from the past only, the current-behaviour group still separates better from worse trades (top-300 1.42 points a trade, 9 of 11 years; all stocks 2.57, 9 of 11).
- **Changing (current) membership beats sticky membership.** DYNAMIC is the only one that improves the all-stocks holdout (13.1% vs 2.2%); PREVIOUS and MODAL lose there.
- **On the account it still fails the pre-registered bar:** in the top-300 development years it adds only +0.2 points (bar +1). In the top-300 holdout it adds +3.4 points (11.5% vs 8.1%) and beats all 3 luck worlds (max 10.4%).
- So: a real but inconsistent effect for the stocks you trade - strong recently, flat in 2013-2023. It stays a research lead, re-tested weekly. No rule is proposed.
