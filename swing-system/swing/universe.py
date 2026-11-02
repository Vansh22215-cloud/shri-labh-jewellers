"""Point-in-time liquid universe built from official NSE bhavcopies.

At each month start we rank stocks by MEDIAN daily traded value over the previous
~4 months, using only data available before that date. This includes stocks that
were later delisted/merged, which reduces survivorship bias in the backtest.

Rules (fixed in DECISIONS.md):
  * EQ series only (BE/BZ = trade-to-trade / surveillance segments are excluded)
  * traded on >= 80% of sample days in the lookback
  * first seen at least 365 days earlier (excludes very new listings)
  * median close >= Rs 50 (excludes penny stocks)
  * top N (default 500) by median traded value
"""
import pandas as pd

from .config import BHAV, DATA, get_logger

log = get_logger()
UNIVERSE_FILE = DATA / "universe_history.csv"


def load_samples():
    """All cached bhavcopy rows (EQ only) as one long table."""
    frames = []
    for f in sorted(BHAV.glob("*.csv")):
        if f.stat().st_size == 0:
            continue
        df = pd.read_csv(f, usecols=["symbol", "series", "close", "value", "date"], parse_dates=["date"])
        frames.append(df[df["series"] == "EQ"])
    if not frames:
        return pd.DataFrame(columns=["symbol", "series", "close", "value", "date"])
    return pd.concat(frames, ignore_index=True)


def universe_at(samples, when, n=500, lookback_days=120, min_price=50, min_presence=0.8,
                min_age_days=365, first_seen=None):
    when = pd.Timestamp(when)
    win = samples[(samples["date"] < when) & (samples["date"] >= when - pd.Timedelta(days=lookback_days))]
    n_days = win["date"].nunique()
    if n_days == 0:
        return pd.DataFrame(columns=["symbol", "med_value", "rank"])
    g = win.groupby("symbol").agg(med_value=("value", "median"), med_close=("close", "median"),
                                  days=("date", "nunique"))
    g = g[(g["days"] >= min_presence * n_days) & (g["med_close"] >= min_price)]
    if first_seen is None:
        first_seen = samples.groupby("symbol")["date"].min()
        # Stocks present in the very first sample were listed before our data starts: treat as old.
        first_seen[first_seen == samples["date"].min()] = pd.Timestamp("1900-01-01")
    old_enough = first_seen[first_seen <= when - pd.Timedelta(days=min_age_days)].index
    g = g[g.index.isin(old_enough)]
    g = g.sort_values("med_value", ascending=False).head(n)
    g["rank"] = range(1, len(g) + 1)
    return g.reset_index()[["symbol", "med_value", "rank"]]


def build_history(start="2013-01-01", n=500):
    """Monthly point-in-time universes from `start` to today. Saved to data/universe_history.csv."""
    samples = load_samples()
    first_seen = samples.groupby("symbol")["date"].min()
    first_seen[first_seen == samples["date"].min()] = pd.Timestamp("1900-01-01")
    months = pd.date_range(start, pd.Timestamp.today(), freq="MS")
    rows = []
    for m in months:
        u = universe_at(samples, m, n=n, first_seen=first_seen)
        u["asof"] = m
        rows.append(u)
    hist = pd.concat(rows, ignore_index=True)
    hist.to_csv(UNIVERSE_FILE, index=False)
    log.info("Universe history: %d months, %d distinct symbols", len(months), hist["symbol"].nunique())
    return hist


def load_history():
    return pd.read_csv(UNIVERSE_FILE, parse_dates=["asof"])


def current_universe(n=500):
    samples = load_samples()
    return universe_at(samples, pd.Timestamp.today() + pd.Timedelta(days=1), n=n)


def membership_mask(hist, dates, symbols):
    """Boolean DataFrame (date x symbol): was the stock in the universe on that date?"""
    hist = hist[hist["symbol"].isin(symbols)]
    piv = pd.crosstab(hist["asof"], hist["symbol"]).astype(bool)
    piv = piv.reindex(columns=symbols, fill_value=False)
    mask = piv.reindex(piv.index.union(dates)).ffill().reindex(dates).fillna(False).astype(bool)
    return mask
