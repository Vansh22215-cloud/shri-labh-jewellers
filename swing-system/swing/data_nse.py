"""Official NSE data from the public archive server (nsearchives.nseindia.com).

What we use and why:
  * Daily "bhavcopy" (official closing prices + traded value of every stock).
      - used to build a POINT-IN-TIME liquidity universe (reduces survivorship bias)
      - used to cross-check Yahoo prices against NSE official prices
  * Nifty 500 constituent list (current sector/industry labels)
  * Bulk and block deal files (shown as context in stock notes)
These are static files published for public download. We download politely
(one file at a time, small pause, cached forever on disk, never re-downloaded).
"""
import io
import time
import zipfile
from datetime import date, datetime

import pandas as pd
import requests

from .config import BHAV, EVENTS, get_logger

log = get_logger()
UA = {"User-Agent": "Mozilla/5.0 (personal research; low frequency)", "Accept": "*/*"}
HOSTS = ["https://nsearchives.nseindia.com", "https://archives.nseindia.com"]
NEW_FORMAT_FROM = date(2024, 7, 8)   # NSE switched bhavcopy format (UDiFF) on this date


def _get(path, timeout=30, tries=3):
    """Download a file from the NSE archive, trying both hostnames, with back-off."""
    for attempt in range(tries):
        for host in HOSTS:
            try:
                r = requests.get(host + path, headers=UA, timeout=timeout)
                if r.status_code == 200 and len(r.content) > 500:
                    return r.content
                if r.status_code == 404:
                    return None          # file does not exist (holiday) - not an error
            except requests.RequestException as e:
                log.debug("NSE fetch failed %s: %s", path, e)
        time.sleep(2 ** attempt)
    return None


def _bhav_path(d):
    if d >= NEW_FORMAT_FROM:
        return f"/content/cm/BhavCopy_NSE_CM_0_0_0_{d:%Y%m%d}_F_0000.csv.zip"
    mon = d.strftime("%b").upper()
    return f"/content/historical/EQUITIES/{d:%Y}/{mon}/cm{d:%d}{mon}{d:%Y}bhav.csv.zip"


def _parse_bhav(raw, d):
    z = zipfile.ZipFile(io.BytesIO(raw))
    df = pd.read_csv(z.open(z.namelist()[0]))
    df.columns = [c.strip() for c in df.columns]
    if "TckrSymb" in df.columns:  # new UDiFF format
        df = df.rename(columns={"TckrSymb": "symbol", "SctySrs": "series", "OpnPric": "open",
                                "HghPric": "high", "LwPric": "low", "ClsPric": "close",
                                "TtlTradgVol": "volume", "TtlTrfVal": "value", "ISIN": "isin"})
    else:
        df = df.rename(columns={"SYMBOL": "symbol", "SERIES": "series", "OPEN": "open", "HIGH": "high",
                                "LOW": "low", "CLOSE": "close", "TOTTRDQTY": "volume",
                                "TOTTRDVAL": "value", "ISIN": "isin"})
    df["series"] = df["series"].astype(str).str.strip()
    df = df[df["series"].isin(["EQ", "BE", "BZ"])]
    df = df[["symbol", "series", "open", "high", "low", "close", "volume", "value", "isin"]].copy()
    df["date"] = pd.Timestamp(d)
    return df


def bhavcopy(d, allow_download=True):
    """Return the official NSE bhavcopy for date d (EQ/BE rows), or None if no trading.

    Cached as data/bhavcopy/YYYYMMDD.csv; a holiday is cached as an empty marker file.
    """
    if isinstance(d, (pd.Timestamp, datetime)):
        d = d.date()
    f = BHAV / f"{d:%Y%m%d}.csv"
    if f.exists():
        if f.stat().st_size == 0:
            return None
        return pd.read_csv(f, parse_dates=["date"])
    if not allow_download:
        return None
    raw = _get(_bhav_path(d))
    if raw is None:
        # Only remember "no file" for dates safely in the past (today's file may come later).
        if (date.today() - d).days > 3:
            f.write_text("")
        return None
    try:
        df = _parse_bhav(raw, d)
    except Exception as e:
        log.warning("Could not parse bhavcopy %s: %s", d, e)
        return None
    df.to_csv(f, index=False)
    time.sleep(0.3)  # be polite to NSE
    return df


def download_bhav_dates(dates, label="bhavcopy"):
    out, n = [], len(dates)
    for i, d in enumerate(dates):
        df = bhavcopy(d)
        if df is not None:
            out.append(df)
        if i % 50 == 0:
            log.info("%s: %d/%d", label, i, n)
    return out


def nifty500_list():
    """Current Nifty 500 constituents with industry. Cached; refreshed weekly."""
    f = EVENTS / "nifty500.csv"
    if f.exists() and (time.time() - f.stat().st_mtime) < 7 * 86400:
        return pd.read_csv(f)
    raw = _get("/content/indices/ind_nifty500list.csv")
    if raw is None:
        if f.exists():
            log.warning("Nifty 500 list download failed; using cached copy")
            return pd.read_csv(f)
        return pd.DataFrame(columns=["Company Name", "Industry", "Symbol", "Series", "ISIN Code"])
    df = pd.read_csv(io.BytesIO(raw))
    df.to_csv(f, index=False)
    return df


def deals():
    """Today's bulk + block deals (NSE publishes only the latest day). Appended to a local history."""
    hist_f = EVENTS / "deals_history.csv"
    frames = []
    for kind in ("bulk", "block"):
        raw = _get(f"/content/equities/{kind}.csv")
        if raw is None:
            continue
        try:
            df = pd.read_csv(io.BytesIO(raw))
            df.columns = [c.strip() for c in df.columns]
            if "Symbol" in df.columns and len(df) and str(df.iloc[0, 0]).upper() != "NO RECORDS":
                df["kind"] = kind
                frames.append(df)
        except Exception as e:
            log.warning("deal file %s unreadable: %s", kind, e)
    new = pd.concat(frames) if frames else pd.DataFrame()
    if hist_f.exists():
        old = pd.read_csv(hist_f)
        new = pd.concat([old, new]).drop_duplicates()
    if len(new):
        new.to_csv(hist_f, index=False)
    return new
