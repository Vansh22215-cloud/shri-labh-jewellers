"""GLOBAL markets overnight -> impact on India (ROADMAP I3).

Daily closes from Yahoo: S&P 500, Nasdaq, Dow, US VIX, Nikkei, Hang Seng, FTSE, crude (Brent), gold, USD/INR,
US 10-year yield. US markets close after Indian markets, so the US session of the previous US trading day is
known before NSE opens. We measure, from history, how Nifty's OPEN gap followed overnight S&P moves.
"""
import numpy as np
import pandas as pd

from . import data_prices
from .config import get_logger

log = get_logger()
GLOBAL = {"SP500": "^GSPC", "NASDAQ": "^IXIC", "DOW": "^DJI", "USVIX": "^VIX", "NIKKEI": "^N225",
          "HANGSENG": "^HSI", "FTSE": "^FTSE", "BRENT": "BZ=F", "GOLD": "GC=F", "USDINR": "INR=X", "US10Y": "^TNX"}
data_prices.INDEX_TICKERS.update(GLOBAL)   # so they are downloaded/updated with the index data


def refresh(first_time=False):
    syms = list(GLOBAL)
    if first_time or any(data_prices.load(s) is None for s in syms):
        data_prices.download_full(syms, start="2011-01-01")
    else:
        data_prices.update(syms)


def us_return_before(indian_dates):
    """For each Indian trading date D: S&P 500 close-to-close return of the last US session BEFORE D."""
    sp = data_prices.load("SP500")
    if sp is None:
        return pd.Series(np.nan, index=indian_dates)
    r = sp["close"].pct_change()
    idx = pd.DatetimeIndex(indian_dates)
    pos = r.index.searchsorted(idx) - 1          # last US date strictly before D
    vals = np.where(pos >= 0, r.values[np.clip(pos, 0, len(r) - 1)], np.nan)
    return pd.Series(vals, index=idx)


def gap_study():
    """How did Nifty open after S&P moves? Returns a small table (average Nifty open gap by S&P bucket)."""
    n = data_prices.load("NIFTY50")
    gap = (n["open"] / n["close"].shift(1) - 1) * 100
    us = us_return_before(n.index) * 100
    df = pd.DataFrame({"us": us, "gap": gap}).dropna()
    df = df[df.index >= "2015-01-01"]
    b = pd.cut(df["us"], [-99, -1.5, -0.5, 0.5, 1.5, 99], labels=["< -1.5%", "-1.5 to -0.5%", "flat", "+0.5 to +1.5%", "> +1.5%"])
    t = df.groupby(b, observed=True)["gap"].agg(["count", "mean"]).round(2)
    return t, round(float(df["us"].corr(df["gap"])), 2)


def overnight_line():
    parts = []
    for k, lab in (("SP500", "S&P 500"), ("NASDAQ", "Nasdaq"), ("NIKKEI", "Nikkei"), ("HANGSENG", "Hang Seng"),
                   ("BRENT", "Brent crude"), ("USDINR", "USD/INR"), ("USVIX", "US VIX")):
        d = data_prices.load(k)
        if d is None or len(d) < 2:
            continue
        c = d["close"].dropna()
        parts.append(f"{lab} {c.iloc[-1]:,.2f} ({(c.iloc[-1] / c.iloc[-2] - 1) * 100:+.1f}%)" if k == "USDINR"
                     else f"{lab} {(c.iloc[-1] / c.iloc[-2] - 1) * 100:+.1f}%")
    return "Global: " + ", ".join(parts) if parts else ""
