"""'Follow the smart money': NSE bulk & block deals by funds and well-known investors (owner's request 2026-11-03).

Rules (fixed, DECISIONS D68):
  * Net buyers only (a client that bought and sold the same stock the same day is netted; intraday churn drops out)
  * High-frequency / proprietary trading firms are ignored (they flip within the day)
  * Buyer is an institution (fund, insurance, AMC, FPI, bank) or a well-known investor
  * Net buy value >= Rs 5 crore, stock in our liquid top-500 universe
  * 'Trend OK' when the stock is above its 50- and 200-day averages
Each flagged deal is logged to journal/smart_money.csv so its real outcome can be measured. This is NOT a validated
strategy yet: free deal history starts now, so it is shown as an idea with a risk score, not as a tested tip.
"""
import re

import pandas as pd

from . import data_prices
from .config import DATA, JOURNAL

LOG = JOURNAL / "smart_money.csv"
HFT = ["GRAVITON", "QE SECURITIES", "JUNOMONETA", "SILVERLEAF", "HRTI", "IRAGE", "NK SECURITIES", "ALPHAGREP",
       "TOWER RESEARCH", "ELIXIR WEALTH", "PACE STOCK BROKING", "MICROCURVES", "PUNIT", "SHARE INDIA", "F3 ADVISORS",
       "ACE BULLION", "STOCKSIPS", "NEXTBILLION", "MANSI SHARE", "ESTEE ADVISORS", "XTX", "JUMP TRADING", "QUADEYE",
       "APOLLO GLOBAL TRADE", "MATHISYS", "ARTHAMAAP", "NUVAMA WEALTH AND INVESTMENT", "PRABHUDAS",
       "BROKING", "SHARE BROKERS", "STOCK BROKERS", "STOCKBROKING", "ARIHANT CAPITAL", "RAJASTHAN GLOBAL SECURITIES"]
INSTITUTION = ["MUTUAL FUND", " MF", "ASSET MANAGEMENT", "INSURANCE", "LIFE ", "PENSION", "FUND", "TRUSTEE",
               "INVESTMENT", "SOVEREIGN", "MONETARY AUTHORITY", "GOVERNMENT OF", "BANK", "CAPITAL", "PARTNERS",
               "ADVISORS", "HOLDINGS", "PTE", "LLC", "PLC", "S.A.", "SICAV", "TRUST"]
FAMOUS = ["DAMANI", "KACHOLIA", "KEDIA", "DOLLY KHANNA", "MUKUL AGRAWAL", "MUKUL MAHAVIR AGRAWAL", "SINGHANIA",
          "ABAKKUS", "PORINJU", "DHAWAN", "NEMISH", "KELA", "JHUNJHUNWALA", "RARE ENTERPRISES", "BHANSALI", "BIYANI",
          "GOLDMAN SACHS", "MORGAN STANLEY", "NOMURA", "BLACKROCK", "VANGUARD", "GIC", "ABU DHABI", "NORGES", "SBI ",
          "HDFC MUTUAL", "ICICI PRUDENTIAL", "NIPPON", "KOTAK MAHINDRA MUTUAL", "AXIS MUTUAL", "MIRAE", "PPFAS",
          "MOTILAL OSWAL MUTUAL", "TATA MUTUAL", "DSP", "UTI ", "LIC ", "LIFE INSURANCE CORPORATION"]


def who(name):
    n = " " + str(name).upper() + " "
    if any(h in n for h in HFT):
        return None
    if any(f in n for f in FAMOUS):
        return "well-known investor/fund"
    if any(i in n for i in INSTITUTION):
        return "institution"
    return None


def todays_buys(deals, universe_syms, min_value_cr=5.0):
    if deals is None or len(deals) == 0:
        return pd.DataFrame()
    d = deals.copy()
    d.columns = [c.strip() for c in d.columns]
    d["date"] = pd.to_datetime(d["Date"], format="%d-%b-%Y", errors="coerce")
    d = d[d["date"] == d["date"].max()]
    d["qty"] = pd.to_numeric(d["Quantity Traded"], errors="coerce")
    d["px"] = pd.to_numeric(d["Trade Price / Wght. Avg. Price"], errors="coerce")
    d["sgn"] = d["Buy/Sell"].astype(str).str.upper().str.startswith("B").map({True: 1, False: -1})
    d["value"] = d["qty"] * d["px"] * d["sgn"]
    g = d.groupby(["Symbol", "Client Name"]).agg(net_value=("value", "sum"), date=("date", "first"),
                                                 avg_px=("px", "mean")).reset_index()
    g["type"] = g["Client Name"].map(who)
    g = g[g["type"].notna() & (g["net_value"] >= min_value_cr * 1e7) & g["Symbol"].isin(universe_syms)]
    if g.empty:
        return g
    out = []
    for _, r in g.iterrows():
        px = data_prices.load(r["Symbol"])
        if px is None or len(px) < 200:
            continue
        c = px["close"]
        trend = bool(c.iloc[-1] > c.rolling(50).mean().iloc[-1] > c.rolling(200).mean().iloc[-1])
        out.append({"date": str(r["date"].date()), "symbol": r["Symbol"], "buyer": r["Client Name"], "type": r["type"],
                    "net_buy_cr": round(r["net_value"] / 1e7, 1), "deal_price": round(r["avg_px"], 2),
                    "close": round(float(c.iloc[-1]), 2), "trend_ok": trend})
    res = pd.DataFrame(out)
    if len(res):
        old = pd.read_csv(LOG) if LOG.exists() else pd.DataFrame()
        pd.concat([old, res]).drop_duplicates(subset=["date", "symbol", "buyer"]).to_csv(LOG, index=False)
    return res.sort_values("net_buy_cr", ascending=False) if len(res) else res
