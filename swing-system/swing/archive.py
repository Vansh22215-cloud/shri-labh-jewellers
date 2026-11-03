"""Lifelong data store: everything the system collects is kept forever and used, so the research data grows every
day instead of being a fixed 13-year window.

Why it is needed (free data sources forget things):
  * Yahoo drops delisted stocks and re-adjusts old prices -> we keep each day's bars as they were (survivorship-safe
    record from now on, and a fallback when Yahoo loses a stock's history).
  * Yahoo keeps only ~730 days of hourly bars and ~60 days of 5-minute bars -> archived daily, so intraday research
    (VWAP, opening range, volume profile, session events) gets a longer history every day.
  * Yahoo statements cover only ~4 years -> every year ever seen is kept, so company analysis gets longer histories.
  * the news store keeps 60 days -> archived per day forever.

Layout (inside data/, which lives in the private GitHub Actions cache - the repository itself is public, and the
market data must not be redistributed there):
  data/archive/<dataset>/<YYYY>/<YYYY-MM-DD>.csv.gz     append-only, one file per day (eod, hourly, m5, news)
  data/archive/fundamentals/<SYMBOL>.json.gz              every statement year ever seen
Rules: never delete, never overwrite a row that is already stored (new rows are added). Monthly bundles are sent to
the owner's Telegram as an off-GitHub backup, and a forwarded bundle is restored by the bot (swing/bot.py).
"""
import gzip
import io
import json
import tarfile
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from .config import ARCHIVE, DATA, FUND, PRIVATE, get_logger

log = get_logger()
DAILY = ("eod", "hourly", "m5", "news")
KEYS = {"eod": ["symbol"], "hourly": ["symbol", "ts"], "m5": ["symbol", "ts"], "news": ["title"]}


# ----------------------------------------------------------------------------- low-level append-only store
def day_file(ds, day):
    d = pd.Timestamp(day)
    return ARCHIVE / ds / f"{d:%Y}" / f"{d:%Y-%m-%d}.csv.gz"


def write_day(ds, day, df):
    """Add rows for one day. Existing rows are kept as they are (append-only); returns rows added."""
    if df is None or not len(df):
        return 0
    f = day_file(ds, day)
    f.parent.mkdir(parents=True, exist_ok=True)
    keys = KEYS[ds]
    if f.exists():
        old = pd.read_csv(f)
        known = set(map(tuple, old[keys].astype(str).values))
        new = df[[tuple(r) not in known for r in df[keys].astype(str).values]]
        if not len(new):
            return 0
        out = pd.concat([old, new], ignore_index=True)
    else:
        new, out = df, df
    tmp = f.with_suffix(".tmp")
    out.to_csv(tmp, index=False, compression="gzip")
    tmp.replace(f)                                     # atomic: a crash never leaves a half-written day
    return len(new)


def days(ds):
    return sorted(pd.Timestamp(p.name[:10]) for p in (ARCHIVE / ds).glob("*/*.csv.gz"))


def read(ds, start=None, end=None):
    fs = sorted((ARCHIVE / ds).glob("*/*.csv.gz"))
    if start is not None:
        fs = [f for f in fs if f.name[:10] >= str(pd.Timestamp(start).date())]
    if end is not None:
        fs = [f for f in fs if f.name[:10] <= str(pd.Timestamp(end).date())]
    if not fs:
        return pd.DataFrame()
    parts = []
    for f in fs:
        x = pd.read_csv(f)
        x["date"] = f.name[:10]
        parts.append(x)
    return pd.concat(parts, ignore_index=True)


# ----------------------------------------------------------------------------- recorders (run every evening)
def record_eod(lookback=10):
    """Each stock's last `lookback` daily bars, exactly as stored today (raw + adjusted close)."""
    from .config import PRICES
    rows = []
    for f in PRICES.glob("*.csv"):
        try:
            df = pd.read_csv(f, index_col="date", parse_dates=["date"]).tail(lookback)
        except Exception:
            continue
        df = df.reset_index()
        df["symbol"] = f.stem
        rows.append(df)
    if not rows:
        return 0
    all_ = pd.concat(rows, ignore_index=True)
    n = 0
    for d, g in all_.groupby("date"):
        n += write_day("eod", d, g.drop(columns=["date"]))
    return n


def record_hourly(lookback_days=14):
    from .intraday_data import INTRA
    rows = []
    for f in INTRA.glob("*.csv"):
        try:
            df = pd.read_csv(f, index_col=0, parse_dates=True)
        except Exception:
            continue
        df = df[df.index >= df.index.max().normalize() - pd.Timedelta(days=lookback_days)]
        df = df.reset_index().rename(columns={df.index.name or "index": "ts"})
        df.columns = ["ts"] + list(df.columns[1:])
        df["symbol"] = f.stem
        rows.append(df)
    if not rows:
        return 0
    all_ = pd.concat(rows, ignore_index=True)
    all_["day"] = pd.to_datetime(all_["ts"]).dt.normalize()
    n = 0
    for d, g in all_.groupby("day"):
        n += write_day("hourly", d, g.drop(columns=["day"]).assign(ts=lambda x: x["ts"].astype(str)))
    return n


def record_m5(symbols, batch=40):
    """5-minute bars of the last 5 completed sessions (Yahoo keeps only ~60 days, so we keep them)."""
    import yfinance as yf
    from .data_prices import yahoo_ticker
    now = pd.Timestamp.now(tz="Asia/Kolkata").tz_localize(None)
    n = 0
    for i in range(0, len(symbols), batch):
        chunk = symbols[i:i + batch]
        tick = {yahoo_ticker(s): s for s in chunk}
        try:
            raw = yf.download(list(tick), period="5d", interval="5m", group_by="ticker", progress=False,
                              auto_adjust=False, threads=True)
        except Exception as e:
            log.warning("5-minute archive download failed: %s", e)
            continue
        rows = []
        for t, s in tick.items():
            try:
                df = raw[t] if isinstance(raw.columns, pd.MultiIndex) else raw
            except KeyError:
                continue
            df = df.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]].dropna(subset=["close"])
            if not len(df):
                continue
            idx = df.index.tz_convert("Asia/Kolkata").tz_localize(None) if df.index.tz is not None else df.index
            df.index = idx
            if now.hour < 16:
                df = df[df.index.normalize() < now.normalize()]          # only completed sessions
            df = df.reset_index()
            df.columns = ["ts"] + list(df.columns[1:])
            df["symbol"] = s
            rows.append(df)
        if rows:
            all_ = pd.concat(rows, ignore_index=True)
            all_["day"] = pd.to_datetime(all_["ts"]).dt.normalize()
            for d, g in all_.groupby("day"):
                n += write_day("m5", d, g.drop(columns=["day"]).assign(ts=lambda x: x["ts"].astype(str)))
        time.sleep(1)
    return n


def record_news():
    from .intel_news import STORE
    if not STORE.exists():
        return 0
    df = pd.read_csv(STORE)
    if not len(df):
        return 0
    df["day"] = pd.to_datetime(df["published"], utc=True, errors="coerce").dt.tz_convert("Asia/Kolkata").dt.normalize()
    df = df.dropna(subset=["day"])
    n = 0
    for d, g in df.groupby("day"):
        n += write_day("news", d.tz_localize(None), g.drop(columns=["day"]))
    return n


def _fund_file(sym):
    return ARCHIVE / "fundamentals" / f"{sym}.json.gz"


def fundamentals_years(sym):
    f = _fund_file(sym)
    if not f.exists():
        return {}
    return json.loads(gzip.decompress(f.read_bytes()))


def record_fundamentals(max_age_days=2):
    """Keep every statement year ever seen per company (Yahoo shows only the latest ~4)."""
    n = 0
    cutoff = time.time() - max_age_days * 86400
    for f in FUND.glob("*.json"):
        if f.stat().st_mtime < cutoff:
            continue
        try:
            snap = json.loads(f.read_text())
        except Exception:
            continue
        ann = snap.get("annual") or {}
        if not ann:
            continue
        kept = fundamentals_years(f.stem)
        changed = False
        for y, row in ann.items():
            if row.get("revenue") and (y not in kept or kept[y] != row):
                if y in kept and kept[y] != row:
                    kept.setdefault("_restated", {})[y] = kept[y]      # keep the earlier version too
                kept[y] = row
                changed = True
        if changed:
            g = _fund_file(f.stem)
            g.parent.mkdir(parents=True, exist_ok=True)
            g.write_bytes(gzip.compress(json.dumps(kept).encode()))
            n += 1
    return n


def run_daily():
    """Evening job: store everything collected today. Each part is independent (one failing never stops the rest)."""
    out = {}
    for name, fn in (("eod", record_eod), ("hourly", record_hourly), ("news", record_news),
                     ("fundamentals", record_fundamentals)):
        try:
            out[name] = fn()
        except Exception as e:
            log.warning("archive %s failed: %s", name, e)
            out[name] = f"failed ({type(e).__name__})"
    try:
        syms = [s.strip() for s in (DATA / "intraday_universe.txt").read_text().split() if s.strip()]
        out["m5"] = record_m5(sorted(set(syms) | {"NIFTY50"}))
    except Exception as e:
        log.warning("archive m5 failed: %s", e)
        out["m5"] = f"failed ({type(e).__name__})"
    log.info("Archive: rows added %s", out)
    return out


# ----------------------------------------------------------------------------- using the archive
def fill_panel(P, symbols, min_days=60):
    """Add stocks that Yahoo no longer has (delisted / dropped), and bars after the end of a stock's Yahoo history,
    from the archive. Only fills where Yahoo has nothing - Yahoo's own (re-adjusted) history is never replaced."""
    from .data_prices import adjusted
    eod = read("eod")
    if not len(eod) or not P:
        return P
    eod["date"] = pd.to_datetime(eod["date"])
    eod = eod[eod["symbol"].isin(set(symbols))]
    have = set(P["close"].columns)
    added = 0
    frames = {}
    for s, g in eod.groupby("symbol"):
        g = g.drop_duplicates("date", keep="first").set_index("date").sort_index()
        if s in have:
            last = P["close"][s].last_valid_index()
            g = g[g.index > last] if last is not None else g
            if not len(g):
                continue
        elif len(g) < min_days:
            continue
        for c in ("adj_close", "dividends", "splits"):
            if c not in g:
                g[c] = g["close"] if c == "adj_close" else 0.0
        frames[s] = adjusted(g)
    if not frames:
        return P
    idx = P["close"].index.union(pd.DatetimeIndex(sorted({d for f in frames.values() for d in f.index})))
    for col in P:
        P[col] = P[col].reindex(idx)
        for s, f in frames.items():
            if col in f:
                if s not in P[col]:
                    P[col][s] = f[col].reindex(idx)
                else:
                    P[col][s] = P[col][s].fillna(f[col].reindex(idx))
    added = len([s for s in frames if s not in have])
    if frames:
        log.info("Archive filled %d stocks Yahoo no longer has, and recent gaps for %d more", added, len(frames) - added)
    return P


def hourly_history(sym):
    """Archived hourly bars for one stock (older than Yahoo's ~730-day window)."""
    fs = sorted((ARCHIVE / "hourly").glob("*/*.csv.gz"))
    parts = []
    for f in fs:
        x = pd.read_csv(f)
        x = x[x["symbol"] == sym]
        if len(x):
            parts.append(x)
    if not parts:
        return None
    df = pd.concat(parts).drop(columns=["symbol"])
    df["ts"] = pd.to_datetime(df["ts"])
    return df.drop_duplicates("ts").set_index("ts").sort_index()


def m5_bars(start=None, end=None, symbols=None):
    df = read("m5", start, end)
    if len(df) and symbols is not None:
        df = df[df["symbol"].isin(set(symbols))]
    if len(df):
        df["ts"] = pd.to_datetime(df["ts"])
    return df


def stats():
    out = {}
    for ds in DAILY:
        d = days(ds)
        out[ds] = {"days": len(d), "first": str(d[0].date()) if d else None, "last": str(d[-1].date()) if d else None}
    out["fundamentals"] = {"companies": len(list((ARCHIVE / "fundamentals").glob("*.json.gz")))}
    out["size_mb"] = round(sum(p.stat().st_size for p in ARCHIVE.rglob("*") if p.is_file()) / 1e6, 1)
    return out


def stats_line():
    s = stats()
    return (f"Lifelong data store: {s['eod']['days']} days of daily bars, {s['hourly']['days']} of hourly, "
            f"{s['m5']['days']} of 5-minute, {s['news']['days']} of news, {s['fundamentals']['companies']} companies' "
            f"statement history ({s['size_mb']} MB). It grows every trading day.")


# ----------------------------------------------------------------------------- backups to the owner's Telegram
def _tar(paths, out, base=DATA):
    with tarfile.open(out, "w:gz") as t:
        for p in paths:
            if p.exists():
                t.add(p, arcname=str(p.relative_to(base)))
    return out


def backup_private():
    """Your trades + forwarded tips, as one small file for your own Telegram chat (weekly)."""
    out = DATA / f"swing-backup-private-{date.today()}.tar.gz"
    return _tar([PRIVATE], out)


def backup_month(month):
    """All archive files of one calendar month (YYYY-MM) + statement history, for an off-GitHub copy."""
    files = []
    for ds in DAILY:
        files += sorted((ARCHIVE / ds).glob(f"{month[:4]}/{month}-*.csv.gz"))
    files += sorted((ARCHIVE / "fundamentals").glob("*.json.gz"))
    out = DATA / f"swing-archive-{month}.tar.gz"
    return _tar(files, out)


def send_backups(settings, force_month=False):
    """Weekly: private backup. First weekly run of a month (or force): last month's archive bundle."""
    from .telegram import send_document
    notes = []
    p = backup_private()
    notes.append("private backup: " + send_document(settings, p, "Backup of your trades and forwarded tips. Keep it; "
                                                    "forward it back to the bot to restore.", mime="application/gzip"))
    p.unlink(missing_ok=True)
    today = date.today()
    if force_month or today.day <= 7:
        prev = (today.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
        p = backup_month(prev)
        if p.stat().st_size > 45e6:
            notes.append(f"archive {prev}: {p.stat().st_size / 1e6:.0f} MB is over Telegram's limit - kept on GitHub only")
        else:
            notes.append(f"archive {prev}: " + send_document(settings, p, f"Data archive for {prev} (prices, hourly, "
                                                             "5-minute, news, statements). Forward back to restore.",
                                                             mime="application/gzip"))
        p.unlink(missing_ok=True)
    return notes


def restore(tar_path):
    """Restore a backup sent by send_backups. Only files under private/ and archive/ are accepted; existing archive
    days are merged (never overwritten), private files are restored only if missing."""
    n = 0
    with tarfile.open(tar_path, "r:gz") as t:
        for m in t.getmembers():
            name = Path(m.name)
            if not m.isfile() or name.is_absolute() or ".." in name.parts or name.parts[0] not in ("private", "archive"):
                continue
            data = t.extractfile(m).read()
            dest = DATA / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            if name.parts[0] == "archive" and len(name.parts) == 4 and name.parts[1] in DAILY:
                n +=write_day(name.parts[1], name.name[:10], pd.read_csv(io.BytesIO(data), compression="gzip"))
            elif not dest.exists():
                dest.write_bytes(data)
                n += 1
    return n
