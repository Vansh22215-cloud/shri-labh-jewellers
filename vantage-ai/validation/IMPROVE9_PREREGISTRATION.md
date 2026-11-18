# Round 9: event signals from NSE disclosures (written 18 Nov 2026, BEFORE any return was computed)
**Owner, 18 Nov:** download the history for #4, #5, #8 and #9, and test them. #10 (pledging) is added because the insider data contains pledge disclosures.

## Data
Downloaded from NSE into `swing-system/data/events/history/`, not in git:

| # | Data | Period |
|---|---|---|
| #4 / #10 | Insider and promoter disclosures | 2015 → |
| #5 | Bulk deals | 2013 → |
| #9 | Buyback announcements | 2013 → |
| #8 | Index replacements (`index_changes.csv`) | 2017 → |

- **Prices:** `swing.data_prices` adjusted daily bars.
- **Costs:** 0.35% per trade.
- **Development** = events before 1 Nov 2023. **Holdout** = 1 Nov 2023 →.
- **Liquidity filter for every event:** 20-day average traded value ≥ ₹2 cr on the event day, the same as the live floor.

## Standalone event trade (the same for #4, #5, #9)
- **Entry:** the open of the first trading day after the event became public. Disclosures and deals are published after the close.
- **Exit:** the open 5 trading days later.
- **No stop-loss.** This matches the short event windows in the papers.
- **One trade per stock at a time.**
- **PASS requires all of the following:**
  - Holdout profit per trade ≥ +1.0% after costs.
  - Profit factor ≥ 1.3 in both periods.
  - At least 40 holdout trades.
  - Development profit per trade > 0.

## Events
- **#4 Promoter buying:** a disclosure with person category "Promoters" or "Promoter Group", mode "Market Purchase", type "Buy", and value ≥ ₹10 lakh. Event date = the NSE disclosure date (`date` field). Several disclosures for the same stock on one day count as one event.
- **#5 Bulk-deal buy:**
  - A BUY bulk deal worth ≥ ₹1 crore (quantity × price).
  - The same client did not also SELL that stock on the same day. Same-day churn is excluded.
  - Event date = the deal date.
- **#9 Buyback announcement:**
  - The first announcement in 60 days for a company whose subject is "Buyback", "Public Announcement - Buyback of Shares", or "Outcome of Board Meeting" with "buy" and "back" in the text.
  - Event date = the announcement time. If it is at or after 15:30, the event counts from the next trading day.
- **#8 Index inclusion:**
  - **Indices:** Nifty 50, Nifty Next 50, Nifty 100, Nifty 200, Nifty 500, Nifty Midcap 150, Nifty Smallcap 250. These are the passively tracked broad indices.
  - **Trade:** buy at the open of the first trading day after the announcement. Sell at the close of the last trading day before the effective date, which is when index funds buy.
  - A stock added to several indices on one announcement is one trade.
  - **PASS bar:** the same as the standalone trade, but with ≥ 60 holdout trades.

## Boosts and flags for VANTAGE BUY signals (both trade sets: top-300 and all stocks)
- **#4b:** a VANTAGE BUY with a #4 promoter-buy event in the prior 20 trading days, vs other BUYs of the same stocks' universe.
  - PASS: ≥ +1.0 point per trade better in both periods and both trade sets, with ≥ 50 trades each.
- **#5b:** the same comparison with a #5 event in the prior 10 trading days.
- **#10 Pledge warning:** a VANTAGE BUY with a promoter "Pledge Creation" disclosure in the prior 60 trading days.
  - PASS (as a warning): ≥ 1.0 point per trade WORSE in both periods and both trade sets, with ≥ 50 trades each.

## After the test
Nothing is applied without the owner's yes.
