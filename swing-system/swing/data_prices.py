"""Daily prices from Yahoo Finance (free) with a local cache, plus liquid-fund NAV.

Adjustment: Yahoo's Open/High/Low/Close are already adjusted for splits and bonuses.
"Adj Close" additionally adjusts for dividends. We multiply O/H/L/C by
(Adj Close / Close) so that every price series is a total-return series.
For the most recent day the factor is 1, so live trade plans use real prices.

Yahoo terms: personal, non-commercial use; we make batched, low-frequency requests
(one batch per night) and cache everything, so each price is downloaded once.
"""
import time

import numpy as np
import pandas as pd
import requests
import yfinance as yf

from .config import DATA, PRICES, get_logger

log = get_logger()

INDEX_TICKERS = {
    "NIFTY50": "^NSEI",
    "NIFTYBEES": "NIFTYBEES.NS",
    "NIFTYBANK": "^NSEBANK",
    "NIFTYIT": "^CNXIT",
    "NIFTYAUTO": "^CNXAUTO",
    "NIFTYFMCG": "^CNXFMCG",
    "NIFTYPHARMA": "^CNXPHARMA",
    "NIFTYMETAL": "^CNXMETAL",
    "NIFTYENERGY": "^CNXENERGY",
    "NIFTYREALTY": "^CNXREALTY",
    "NIFTYINFRA": "^CNXINFRA",
    "NIFTYPSUBANK": "^CNXPSUBANK",
    "INDIAVIX": "^INDIAVIX",
}
COLS = ["open", "high", "low", "close", "adj_close", "volume", "dividends", "splits"]


def yahoo_ticker(symbol):
    return INDEX_TICKERS.get(symbol, f"{symbol}.NS")


def _path(symbol):
    safe = symbol.replace("/", "_")
    return PRICES / f"{safe}.csv"


def _clean(df):
    df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close",
                            "Adj Close": "adj_close", "Volume": "volume",
                            "Dividends": "dividends", "Stock Splits": "splits"})
    for c in COLS:
        if c not in df.columns:
            df[c] = 0.0 if c in ("dividends", "splits") else np.nan
    df = df[COLS].copy()
    df.index = pd.to_datetime(df.index)
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    df.index = df.index.normalize()
    df.index.name = "date"
    df = df[~df.index.duplicated(keep="last")].dropna(subset=["close"])
    df["adj_close"] = df["adj_close"].fillna(df["close"])
    return df.sort_index()


def _download_batch(tickers, **kw):
    """yf.download with retries; returns {ticker: DataFrame}."""
    for attempt in range(4):
        try:
            raw = yf.download(tickers, auto_adjust=False, actions=True, group_by="ticker",
                              threads=True, progress=False, **kw)
            out = {}
            for t in tickers:
                try:
                    sub = raw[t] if len(tickers) > 1 else raw
                    if isinstance(sub.columns, pd.MultiIndex):
                        sub.columns = sub.columns.get_level_values(-1)
                    sub = sub.dropna(how="all")
                    if len(sub):
                        out[t] = _clean(sub)
                except KeyError:
                    pass
            return out
        except Exception as e:
            log.warning("Yahoo batch failed (attempt %d): %s", attempt + 1, e)
            time.sleep(5 * 2 ** attempt)
    return {}


def load(symbol):
    f = _path(symbol)
    if not f.exists():
        return None
    return pd.read_csv(f, index_col="date", parse_dates=["date"])


def save(symbol, df):
    df.to_csv(_path(symbol))


def keep_older_history(old, new, min_overlap=20):
    """Never lose history: if a fresh Yahoo download starts later than what we already had (Yahoo trimmed it),
    keep our older rows. Their adjusted close is rescaled to the new adjustment basis at the overlap."""
    if old is None or not len(old) or not len(new) or old.index.min() >= new.index.min():
        return new
    ov = old.index.intersection(new.index)
    older = old[old.index < new.index.min()].copy()
    if len(ov) >= min_overlap:
        ratio = (new.loc[ov, "adj_close"] / new.loc[ov, "close"]).median() / \
                (old.loc[ov, "adj_close"] / old.loc[ov, "close"]).median()
        if np.isfinite(ratio) and ratio > 0:
            older["adj_close"] = older["adj_close"] * ratio
    log.info("Kept %d older bars Yahoo no longer returns", len(older))
    return pd.concat([older, new]).sort_index()


def download_full(symbols, start="2011-01-01", batch=40):
    """Download complete history for symbols (used on first run and after corporate actions)."""
    got = 0
    for i in range(0, len(symbols), batch):
        chunk = symbols[i:i + batch]
        tick = {yahoo_ticker(s): s for s in chunk}
        res = _download_batch(list(tick), start=start)
        for t, df in res.items():
            save(tick[t], keep_older_history(load(tick[t]), df))
            got += 1
        log.info("Yahoo full history: %d/%d symbols", min(i + batch, len(symbols)), len(symbols))
        time.sleep(1.5)
    return got


NO_YAHOO = DATA / "no_yahoo_data.json"


def _skip_missing(symbols, retry_days=30):
    """Delisted/renamed stocks have no Yahoo data; remember them and retry only monthly."""
    import json
    try:
        seen = json.loads(NO_YAHOO.read_text())
    except Exception:
        seen = {}
    today = pd.Timestamp.today()
    keep = [s for s in symbols if s not in seen or (today - pd.Timestamp(seen[s])).days > retry_days]
    return keep, seen


def _remember_missing(symbols, seen):
    import json
    for s in symbols:
        if load(s) is None:
            seen[s] = str(pd.Timestamp.today().date())
    NO_YAHOO.write_text(json.dumps(seen, indent=0))


def update(symbols, start="2011-01-01", batch=60):
    """Incremental nightly update. Re-downloads full history for a symbol when a new
    split/bonus/dividend appears or when the overlap with the cache disagrees
    (Yahoo re-adjusts old prices after corporate actions)."""
    missing = [s for s in symbols if load(s) is None]
    need_full, seen = _skip_missing(missing)
    have = [s for s in symbols if s not in missing]
    for i in range(0, len(have), batch):
        chunk = have[i:i + batch]
        tick = {yahoo_ticker(s): s for s in chunk}
        res = _download_batch(list(tick), period="1mo")
        for t, new in res.items():
            s = tick[t]
            old = load(s)
            overlap = old.index.intersection(new.index)
            ok = len(overlap) > 0
            if ok:
                a, b = old.loc[overlap, "adj_close"], new.loc[overlap, "adj_close"]
                ok = bool((abs(a / b - 1) < 0.005).all())
            fresh_events = new.index[(new["splits"] > 0) | (new["dividends"] > 0)]
            if len(fresh_events) and fresh_events.max() > old.index.max():
                ok = False
            if not ok:
                need_full.append(s)
                continue
            merged = pd.concat([old[~old.index.isin(new.index)], new]).sort_index()
            save(s, merged)
        time.sleep(1.0)
    if need_full:
        log.info("Full re-download for %d symbols (new/changed adjustments)", len(need_full))
        download_full(need_full, start=start)
        _remember_missing(need_full, seen)


def adjusted(df):
    """Return total-return-adjusted OHLC + volume + raw close (for cross-checks and plans)."""
    f = (df["adj_close"] / df["close"]).replace([np.inf, -np.inf], np.nan).fillna(1.0)
    out = pd.DataFrame({
        "open": df["open"] * f, "high": df["high"] * f, "low": df["low"] * f,
        "close": df["adj_close"], "volume": df["volume"], "raw_close": df["close"],
    }, index=df.index)
    return out


def panel(symbols, start=None):
    """Wide DataFrames (date x symbol) for open/high/low/close/volume/raw_close."""
    frames = {}
    for s in symbols:
        df = load(s)
        if df is None or len(df) == 0:
            continue
        a = adjusted(df)
        if start is not None:
            a = a[a.index >= pd.Timestamp(start)]
        frames[s] = a
    if not frames:
        return {}
    out = {}
    for col in ["open", "high", "low", "close", "volume", "raw_close"]:
        out[col] = pd.DataFrame({s: f[col] for s, f in frames.items()}).sort_index()
    return out


LIQUID_FUND_CODE = 118701  # Nippon India Liquid Fund - Direct Plan - Growth (AMFI code), via mfapi.in


def liquid_fund_nav():
    """Daily NAV of a large liquid fund; used to credit idle cash. Cached; fails gracefully."""
    f = DATA / "liquid_fund_nav.csv"
    try:
        if not f.exists() or (time.time() - f.stat().st_mtime) > 86400:
            r = requests.get(f"https://api.mfapi.in/mf/{LIQUID_FUND_CODE}", timeout=30)
            r.raise_for_status()
            rows = r.json()["data"]
            nav = pd.Series({pd.to_datetime(x["date"], dayfirst=True): float(x["nav"]) for x in rows})
            nav.sort_index().rename("nav").to_csv(f, index_label="date")
    except Exception as e:
        log.warning("Liquid fund NAV download failed (%s); using cache or 6%% p.a. fallback", e)
    if f.exists():
        return pd.read_csv(f, index_col="date", parse_dates=["date"])["nav"]
    idx = pd.bdate_range("2010-01-01", pd.Timestamp.today())
    return pd.Series((1 + 0.06) ** (np.arange(len(idx)) / 252), index=idx, name="nav")


def repair_isolated_spikes(df, tol=0.3):
    """Fix bars (1-2 days) that are wildly off from BOTH neighbours while the neighbours agree,
    e.g. NIFTYBEES on 19-20 Dec 2019 quoted at 1/10th of the real price on Yahoo.
    Used ONLY for the benchmark; suspicious stock data is quarantined instead."""
    df = df.copy()
    c = df["close"]
    fixed = []
    for w in (1, 2):
        prev, nxt = c.shift(1), c.shift(-w)
        neighbours_agree = (prev / nxt - 1).abs() < 0.05
        off = ((c / prev - 1).abs() > tol) & neighbours_agree
        for d in c.index[off]:
            i = c.index.get_loc(d)
            ratio = prev.iloc[i] / c.iloc[i]
            for j in range(i, i + w):
                for col in ("open", "high", "low", "close", "adj_close"):
                    df.iloc[j, df.columns.get_loc(col)] *= ratio
                fixed.append(str(c.index[j].date()))
        c = df["close"]
    if fixed:
        log.warning("Benchmark data repaired on %s (isolated bad quotes)", ", ".join(sorted(set(fixed))))
    return df


def benchmark():
    """NIFTYBEES, total-return adjusted, with isolated bad quotes repaired."""
    return adjusted(repair_isolated_spikes(load("NIFTYBEES")))


def patch_today_from_intraday(symbol, day):
    """If the daily history lacks `day` (Yahoo sometimes publishes an empty daily bar), rebuild that day's bar
    from 5-minute data: open = first, high = max, low = min, close = last, volume = sum. Returns True if patched."""
    df = load(symbol)
    day = pd.Timestamp(day).normalize()
    if df is not None and len(df) and df.index[-1] >= day:
        return False
    try:
        raw = yf.download(yahoo_ticker(symbol), period="5d", interval="5m", progress=False, auto_adjust=False)
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)
        raw = raw.dropna(subset=["Close"])
        idx = raw.index.tz_convert("Asia/Kolkata").tz_localize(None) if raw.index.tz is not None else raw.index
        bars = raw[idx.normalize() == day]
        if bars.empty:
            return False
        row = pd.DataFrame({"open": [bars["Open"].iloc[0]], "high": [bars["High"].max()], "low": [bars["Low"].min()],
                            "close": [bars["Close"].iloc[-1]], "adj_close": [bars["Close"].iloc[-1]],
                            "volume": [bars["Volume"].sum()], "dividends": [0.0], "splits": [0.0]},
                           index=pd.DatetimeIndex([day], name="date"))
        save(symbol, pd.concat([df, row]) if df is not None else row)
        log.warning("%s: daily bar for %s rebuilt from 5-minute data (Yahoo daily bar was missing)", symbol, day.date())
        return True
    except Exception as e:
        log.warning("intraday patch failed for %s: %s", symbol, e)
        return False


def patch_missing_day_batch(symbols, day, batch=200):
    """Batch version of patch_today_from_intraday for many stocks (one 5-minute download per 200 symbols)."""
    day = pd.Timestamp(day).normalize()
    need = [s for s in symbols if (load(s) is not None and load(s).index[-1] < day)]
    fixed = 0
    for i in range(0, len(need), batch):
        chunk = need[i:i + batch]
        tick = {yahoo_ticker(s): s for s in chunk}
        try:
            raw = yf.download(list(tick), period="5d", interval="5m", group_by="ticker", progress=False,
                              auto_adjust=False, threads=True)
        except Exception as e:
            log.warning("batch intraday patch failed: %s", e)
            continue
        for t, s in tick.items():
            try:
                g = (raw[t] if len(tick) > 1 else raw).dropna(subset=["Close"])
            except KeyError:
                continue
            if g.empty:
                continue
            idx = g.index.tz_convert("Asia/Kolkata").tz_localize(None) if g.index.tz is not None else g.index
            b = g[idx.normalize() == day]
            if b.empty:
                continue
            df = load(s)
            row = pd.DataFrame({"open": [b["Open"].iloc[0]], "high": [b["High"].max()], "low": [b["Low"].min()],
                                "close": [b["Close"].iloc[-1]], "adj_close": [b["Close"].iloc[-1]],
                                "volume": [b["Volume"].sum()], "dividends": [0.0], "splits": [0.0]},
                               index=pd.DatetimeIndex([day], name="date"))
            save(s, pd.concat([df, row]))
            fixed += 1
    if fixed:
        log.warning("%d stocks: daily bar for %s rebuilt from 5-minute data (Yahoo daily bars were missing)",
                    fixed, day.date())
    return fixed
