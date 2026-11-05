"""Hourly (60-minute) NSE prices from Yahoo Finance for intraday research.

Yahoo keeps ~730 days of hourly bars. NSE hourly bars start at 09:15, 10:15, ... 15:15
(the last one is 15 minutes long) -> 7 bars a day. Cached per stock in data/intraday/.
Today's bars are dropped until the market has closed (incomplete).
"""
import time

import numpy as np
import pandas as pd
import yfinance as yf

from .config import DATA, get_logger
from .data_prices import yahoo_ticker

log = get_logger()
INTRA = DATA / "intraday"
INTRA.mkdir(parents=True, exist_ok=True)


def _clean(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]].dropna(subset=["close"])
    idx = df.index
    if idx.tz is not None:
        idx = idx.tz_convert("Asia/Kolkata").tz_localize(None)
    df.index = idx
    now = pd.Timestamp.now(tz="Asia/Kolkata").tz_localize(None)
    if now.hour < 16:   # market not finished today -> drop today's partial bars
        df = df[df.index.normalize() < now.normalize()]
    return df[~df.index.duplicated(keep="last")].sort_index()


def download(symbols, batch=25):
    for i in range(0, len(symbols), batch):
        chunk = symbols[i:i + batch]
        tick = {yahoo_ticker(s): s for s in chunk}
        for attempt in range(3):
            try:
                raw = yf.download(list(tick), period="730d", interval="60m", group_by="ticker",
                                  auto_adjust=False, threads=True, progress=False)
                break
            except Exception as e:
                log.warning("hourly batch failed: %s", e)
                time.sleep(5 * 2 ** attempt)
        else:
            continue
        for t, s in tick.items():
            try:
                df = _clean(raw[t].copy() if len(tick) > 1 else raw.copy())
            except KeyError:
                continue
            if len(df) < 500:
                continue
            f = INTRA / f"{s}.csv"
            if f.exists():   # keep older cached history beyond Yahoo's 730-day window
                old = pd.read_csv(f, index_col=0, parse_dates=True)
                df = pd.concat([old[old.index < df.index.min()], df])
            df.to_csv(f)
        log.info("hourly data %d/%d", min(i + batch, len(symbols)), len(symbols))
        time.sleep(2)


def load_cube(symbols):
    """Return (days, symbols, arrays) where arrays[k] has shape (n_days, n_symbols, 7) for k in o,h,l,c,v."""
    frames = {}
    for s in symbols:
        f = INTRA / f"{s}.csv"
        df = pd.read_csv(f, index_col=0, parse_dates=True) if f.exists() else None
        try:   # lifelong store: hourly bars older than Yahoo's ~730-day window
            from .archive import hourly_history
            old = hourly_history(s)
            if old is not None and len(old):
                old = old[["open", "high", "low", "close", "volume"]]
                df = old if df is None else pd.concat([old[old.index < df.index.min()], df]).sort_index()
        except Exception:
            pass
        if df is not None and len(df):
            frames[s] = df
    syms = sorted(frames)
    days = sorted(set().union(*[set(df.index.normalize()) for df in frames.values()]))
    days = pd.DatetimeIndex(days)
    dpos = {d: i for i, d in enumerate(days)}
    cube = {k: np.full((len(days), len(syms), 7), np.nan) for k in ("o", "h", "l", "c", "v")}
    for j, s in enumerate(syms):
        df = frames[s]
        mins = df.index.hour * 60 + df.index.minute
        slot = ((mins - 555) // 60).astype(int)
        ok = (slot >= 0) & (slot <= 6) & ((mins - 555) % 60 == 0)
        df, slot = df[ok], slot[ok]
        di = np.array([dpos[d] for d in df.index.normalize()])
        for k, col in (("o", "open"), ("h", "high"), ("l", "low"), ("c", "close"), ("v", "volume")):
            cube[k][di, j, slot] = df[col].values
    # require a full day: first bar and last bar present
    full = ~np.isnan(cube["o"][:, :, 0]) & ~np.isnan(cube["c"][:, :, 6])
    for k in cube:
        cube[k][~full] = np.nan
    return days, syms, cube
