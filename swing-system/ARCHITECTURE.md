# ARCHITECTURE.md - Personal AI Trading Intelligence Desk (design, 2026-11-03)

Research and paper-trading only. Live order execution is NOT built and stays disabled until the owner explicitly
approves it in writing (and even then needs a paid broker API). Research, not advice.

## 1. Desks (how a fund is organised -> how this system is organised)
| Fund team            | Our module                                   | Status |
|----------------------|----------------------------------------------|--------|
| Data engineering     | swing/data_*.py, update.py, health.py        | built: prices, NSE bhavcopy, delivery, results dates, fundamentals, hourly bars |
| Market intelligence  | intel/ (new): FII-DII positioning, F&O OI, global markets, news, events | planned (week 1-2) |
| Quant research       | families.py (25+ strategies), search.py, validate.py, research.py | built; library of famous methods running |
| Machine learning     | ml/ (new): feature store, walk-forward models, calibrated probabilities | planned (week 3) |
| Portfolio & risk     | strategy.py sizing, backtest.py, risk_score.py; new: daily loss limit, heat, abnormal-market detector | partly built |
| Trading desk (ideas) | nightly.py, live_scan.py, meta-system (S12)  | built (single strategy); meta-system planned |
| Performance & learning | journal.py, tipcheck.py, weekly.py, research sessions | built; new analytics planned |
| Product / UI         | Telegram cards + web DASHBOARD (Artifact, phone-friendly, refreshed hourly) | dashboard planned (week 2) |

## 2. Data sources - free vs paid (checked 2026-11-03)
FREE and used/planned:
- NSE archive: daily bhavcopy, delivery (MTO), participant-wise OI (FII/DII/Pro/Client futures & options
  positions), F&O end-of-day bhavcopy (futures/options prices + open interest), bulk/block deals, Nifty 500 list.
- Yahoo Finance: daily + 5-minute + hourly stock prices, NSE sector indices, India VIX, GLOBAL markets
  (S&P 500, Nasdaq, Nikkei, Hang Seng, crude oil, USD/INR, US 10-year yield, gold), fundamentals, results dates.
- AMFI (mfapi.in): liquid-fund NAV.  Telegram Bot API: delivery.
- News headlines: Economic Times / Moneycontrol RSS (headlines only, personal use; scored by Claude in sessions).
NOT available free from this cloud (blocked or paid):
- Live option chain & market depth (NSE website API blocks automated access) -> needs a broker/data API.
- Tick/real-time streaming -> Kite Connect (Rs 500/month), TrueData / Global Datafeeds (paid, ~Rs 1,000+/month).
- Historical intraday options data -> paid vendors.  BSE-only stocks: mostly illiquid; BSE API blocks scripts.
The owner has decided NOT to buy Kite Connect for now (D65). Options work is therefore END-OF-DAY.

## 3. A trade recommendation (target format)
Stock/instrument, BUY/SELL, entry range, stop-loss, T1/T2/T3, risk:reward, position size, capital at risk,
expected holding period, PROBABILITY of T1-before-stop (calibrated from walk-forward trades of the same
setup in similar market regimes, with the sample size shown), confidence score (from model validation, not
opinion), risk score 1-10, supporting evidence, and INVALIDATION conditions ("idea is void if ...").
If nothing qualifies: "No good opportunities today".

## 4. Validation rules (unchanged, non-negotiable)
Costs incl. Zerodha charges + slippage (+ STCG tax in performance reports), next-bar execution, gap-through-stop,
walk-forward selection, untouched holdout, variant counting with a stricter bar, pre-registered ideas only,
no live change from a handful of trades. Untested = never presented as profitable.

## 5. Risk rules
1% risk per trade, max 25% capital per position, max 4 open trades, no leverage, 4-week pause at -10%, hard stop at
-20%; NEW: daily loss limit (stop new trades for the day after -2% realised), abnormal-market detector (VIX spike,
Nifty gap > 2%, data outage) -> no new trades; no tips when data health fails.
