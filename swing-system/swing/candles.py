"""Kite candle library - the ONLY price data in the system (owner 20 Nov: "download all stocks' candles for all
minutes, hours and 1 day from Kite"; Yahoo removed).

  interval   stocks                                         history
  day        every NSE stock + NIFTY 50, NIFTY BANK, VIX    everything Kite has (floor 2000-01-01)
  60minute   every NSE stock + NIFTY 50, NIFTY BANK         everything Kite has (floor 2005-01-01)
  15minute   "                                              "
  5minute    "                                              "
  minute     "                                              "
  30minute   every NSE stock + NIFTY 50, NIFTY BANK         everything Kite has (owner 20 Nov: download each as it is)
  (1-minute history skipped by the owner; only 3- and 10-minute candles are built, from 1- and 5-minute.)

How: read-only Kite historical API, at most ~3 requests a second, in ~10-minute chunks whenever the day's Kite
login is valid and NEVER 8:45 am - 3:50 pm on weekdays (live scanning comes first). Each stock is read BACKWARDS
from today until Kite returns nothing twice (= the start of what Kite has), then topped up forwards every evening
(which also replaces today's live-built candles with Kite's official ones). Order: day for all stocks, then
60-minute for all, then 15, 5, 1 - so the most useful history is complete first.
Storage: data/candles/<interval>/<SYM>.parquet in GitHub's PRIVATE cache, never in git. Downloads pause above
MAX_DATA_GB so the cache cannot overflow; results/candle_library.md shows progress, first day per interval, and
stocks Kite does not have.
Splits/bonuses: Kite candles are used as Kite gives them; load(adjusted=True) divides the older candles of a stock
by any clear split/bonus ratio found in its own daily Kite candles (no other source)."""
import json
import time
from datetime import timedelta

import numpy as np
import pandas as pd

from .config import DATA, RESULTS, get_logger

log = get_logger()
from .r2 import root as _kite_root
BASE = _kite_root() / "candles"          # private R2 bucket copy when set up (r2.py), else the GitHub cache folder
STATE_F = BASE / "state.json"
REPORT = RESULTS / "candle_library.md"
GAP = 0.36                                           # <= 3 historical requests a second (Kite's limit)
INTERVALS = {                                        # chunk = days per request (Kite's limits, with a margin)
    "day": {"chunk": 1990, "floor": pd.Timestamp("2000-01-01")},
    "60minute": {"chunk": 395, "floor": pd.Timestamp("2005-01-01")},
    "15minute": {"chunk": 195, "floor": pd.Timestamp("2005-01-01")},
    "30minute": {"chunk": 195, "floor": pd.Timestamp("2005-01-01")},
    "5minute": {"chunk": 95, "floor": pd.Timestamp("2005-01-01")},
    "minute": {"chunk": 58, "floor": pd.Timestamp("2005-01-01")},
}
ORDER = ["day", "5minute", "60minute", "30minute", "15minute"]   # owner 20 Nov: every one downloaded from Kite as
                                 # it is (not built from others). 5-minute first (the tests need it), then the small
                                 # ones, so the storage limit - if ever reached - stops the biggest last. 1-minute: skipped.
DERIVED = {"3minute": ("minute", "3min"), "10minute": ("5minute", "10min")}   # only these two are built
ALL_INTERVALS = ["minute", "3minute", "5minute", "10minute", "15minute", "30minute", "60minute", "day"]
INDICES = {"NIFTY50": "NIFTY 50", "BANKNIFTY": "NIFTY BANK", "INDIAVIX": "INDIA VIX"}
MAX_DATA_GB = 9.5 if _kite_root() != DATA else 8.5  # R2: stay inside Cloudflare's free 10 GB; GitHub cache: 10 GB
MAX_MINUTES = 10                                     # one step never runs longer (other jobs wait for it)
COLS = ["open", "high", "low", "close", "volume"]


# ----------------------------------------------------------------------------- state and symbols
def _state():
    try:
        return json.loads(STATE_F.read_text())
    except Exception:
        return {}


def _save_state(st):
    BASE.mkdir(parents=True, exist_ok=True)
    tmp = STATE_F.with_suffix(".tmp")
    tmp.write_text(json.dumps(st))
    tmp.replace(STATE_F)


def symbols(interval="day"):
    """Every NSE stock Kite lists today, plus the indices (VIX: daily only)."""
    from . import kite
    idx = list(INDICES) if interval == "day" else ["NIFTY50", "BANKNIFTY"]
    return idx + kite.equity_symbols()


def _path(interval, sym):
    return BASE / interval / f"{sym.replace('/', '_')}.parquet"


def _token(sym):
    from . import kite
    ins = kite.instruments()
    row = ins[ins["tradingsymbol"] == INDICES.get(sym, sym)]
    return int(row["instrument_token"].iloc[0]) if len(row) else None


def _fetch(sym, interval, fr, to, retries=3):
    """Kite candles from fr to to (inclusive days) -> DataFrame (may be empty); None if Kite has no such instrument."""
    from . import kite
    tok = _token(sym)
    if tok is None:
        return None
    for a in range(retries):
        time.sleep(GAP * (1 + 3 * a))
        try:
            r = kite._get(f"/instruments/historical/{tok}/{interval}",
                          params={"from": f"{fr:%Y-%m-%d} 00:00:00", "to": f"{to:%Y-%m-%d} 23:59:59"}, timeout=60)
            c = r.json()["data"]["candles"]
            break
        except Exception as e:
            if "429" in str(e) or "Too Many" in str(e):
                continue                                  # rate limited: wait longer, try again
            raise
    else:
        raise RuntimeError("rate limited")
    if not c:
        return pd.DataFrame(columns=COLS)
    df = pd.DataFrame([x[:6] for x in c], columns=["date"] + COLS)
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
    if interval == "day":
        df["date"] = df["date"].dt.normalize()
    df = df.set_index("date")
    return df.astype({"open": "float32", "high": "float32", "low": "float32", "close": "float32", "volume": "float64"})


def store(interval, sym, df):
    """Merge candles into the library (new candles replace old ones with the same time)."""
    f = _path(interval, sym)
    f.parent.mkdir(parents=True, exist_ok=True)
    if f.exists():
        old = pd.read_parquet(f)
        df = pd.concat([old[~old.index.isin(df.index)], df])
    tmp = f.with_suffix(".tmp")
    df.sort_index().to_parquet(tmp, compression="zstd")
    tmp.replace(f)


# ----------------------------------------------------------------------------- reading
def raw(sym, interval="day"):
    if interval in DERIVED and not _path(interval, sym).exists():
        base, rule = DERIVED[interval]
        b = raw(sym, base)
        return resample(b, rule) if b is not None and len(b) else None
    f = _path(interval, sym)
    return pd.read_parquet(f) if f.exists() else None


def resample(b, rule):
    """Exact bigger candles from smaller ones, aligned to NSE's 9:15 open."""
    g = b.resample(rule, origin="start_day", offset="15min", label="left", closed="left")
    return pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(), "low": g["low"].min(),
                         "close": g["close"].last(), "volume": g["volume"].sum()}).dropna(subset=["open"])


STD_RATIOS = (2.0, 3.0, 4.0, 5.0, 10.0, 1.5, 5 / 3, 2.5)


def split_factors(sym):
    """{date: ratio} of clear splits/bonuses, found in the stock's own Kite DAILY candles: an overnight drop whose
    open and close both sit within a few % of a standard ratio of the previous close."""
    k = raw(sym, "day")
    out = {}
    if k is None or len(k) < 2:
        return out
    pc = k["close"].shift()
    for d, o, c, p in zip(k.index[1:], k["open"].values[1:], k["close"].values[1:], pc.values[1:]):
        if not p or p != p:
            continue
        for r in STD_RATIOS:
            if abs(o * r / p - 1) < 0.04 and abs(c * r / p - 1) < 0.06:
                out[d] = r
                break
    return out


def load(sym, interval="day", adjusted=True, start=None, end=None):
    """Kite candles of one stock/index at any interval (minute, 3/5/10/15/30/60minute, day). None if not downloaded.
    adjusted=True: older candles divided by clear split/bonus ratios (prices) and multiplied (volume)."""
    d = raw(sym, interval)
    if d is None or not len(d):
        return None
    d = d[COLS].astype("float64")
    if adjusted:
        sf = split_factors(sym)
        if sf:
            f = pd.Series(1.0, index=d.index)
            for day, r in sf.items():
                f[d.index < day] *= r
            for c in ("open", "high", "low", "close"):
                d[c] = d[c] / f
            d["volume"] = d["volume"] * f
    if start is not None:
        d = d[d.index >= pd.Timestamp(start)]
    if end is not None:
        d = d[d.index <= pd.Timestamp(end)]
    d.attrs.update(source="Kite", interval=interval, splits=len(split_factors(sym)) if adjusted else 0)
    return d


# ----------------------------------------------------------------------------- downloading
def data_size_gb():
    tot = 0
    for p in _kite_root().rglob("*"):
        try:
            if p.is_file():
                tot += p.stat().st_size
        except Exception:
            pass
    return tot / 1e9


def in_market_hours(now=None):
    """8:45 am - 3:50 pm on weekdays: no history downloads (live scanning first)."""
    now = now or pd.Timestamp.now(tz="Asia/Kolkata")
    m = now.hour * 60 + now.minute
    if not (8 * 60 + 45 <= m <= 15 * 60 + 50) or now.weekday() >= 5:
        return False
    from .market_days import is_trading_day
    return is_trading_day(now.date())                    # NSE holidays: downloads may run all day


def step(max_requests=1500, today=None, intervals=None):
    """One chunk of work: backwards until Kite has no more, then forward top-ups. -> summary dict."""
    from . import kite
    if not kite.logged_in():
        return {"skipped": "not logged in"}
    if in_market_hours():
        return {"skipped": "market hours"}
    today = pd.Timestamp(today or pd.Timestamp.now().normalize()).normalize()
    st, used, t0 = _state(), 0, time.time()
    full = False
    for interval in intervals or ORDER:
        if interval != "day" and data_size_gb() > MAX_DATA_GB:
            log.warning("Candles: data above %.1f GB - %s and smaller paused (storage)", MAX_DATA_GB, interval)
            st["_storage_full"] = str(today.date())
            break
        cfg = INTERVALS[interval]
        for sym in symbols(interval):
            k = f"{interval}|{sym}"
            s = st.get(k, {})
            while True:
                if used >= max_requests or time.time() - t0 > MAX_MINUTES * 60 or (used % 50 == 0 and in_market_hours()):
                    full = True
                    break
                if interval != "day" and used % 200 == 199 and data_size_gb() > MAX_DATA_GB:
                    st["_storage_full"] = str(today.date())
                    full = True
                    break
                try:
                    if not s.get("ended"):                       # backwards: today -> as far back as Kite has
                        to = pd.Timestamp(s["oldest"]) - timedelta(days=1) if s.get("oldest") else today
                        fr = max(to - timedelta(days=cfg["chunk"]), cfg["floor"])
                        d = _fetch(sym, interval, fr, to)
                        used += 1
                        if d is None:
                            s.update(ended=True, newest=str(today.date()), missing=True)
                        else:
                            if len(d):
                                store(interval, sym, d)
                                s["newest"] = max(s.get("newest", "0000"), str(d.index.max().date()))
                                s["first"] = str(d.index.min().date())
                                s["empty_runs"] = 0
                            else:
                                s["empty_runs"] = s.get("empty_runs", 0) + 1
                            s["oldest"] = str(fr.date())
                            if s["empty_runs"] >= 2 or fr <= cfg["floor"]:   # 2 empty chunks = start of Kite's history
                                s["ended"] = True
                            s.setdefault("newest", str(today.date()))
                    elif pd.Timestamp(s.get("newest", "2000-01-01")) < today:     # forwards top-up
                        fr = pd.Timestamp(s["newest"]) - timedelta(days=3)
                        d = _fetch(sym, interval, fr, today)
                        used += 1
                        if d is not None and len(d):
                            store(interval, sym, d)
                        s["newest"] = str(today.date())
                    else:
                        break
                except Exception as e:
                    st[k] = s
                    _save_state(st)
                    log.warning("Candles %s %s: %s", interval, sym, type(e).__name__)
                    return {"requests": used, "stopped": type(e).__name__}
                st[k] = s
            if full:
                break
        if full:
            break
    if "_storage_full" in st and data_size_gb() <= MAX_DATA_GB:
        st.pop("_storage_full")
    _save_state(st)
    return {"requests": used, **progress(st)}


def progress(st=None):
    st = st if st is not None else _state()
    out = {}
    for interval in ORDER:
        syms = symbols(interval)
        done = sum(1 for s in syms if st.get(f"{interval}|{s}", {}).get("ended"))
        out[interval] = f"{done}/{len(syms)}"
        out[interval + "_complete"] = bool(syms) and done == len(syms)
    out["complete"] = all(out[i + "_complete"] for i in ORDER)
    out["storage_full"] = bool(st.get("_storage_full"))
    return out


def complete(interval="day"):
    """All of Kite's history for this interval is downloaded and up to date (within 5 days)."""
    interval = DERIVED.get(interval, (interval,))[0]
    st = _state()
    syms = symbols(interval)
    if not syms:
        return False
    recent = (pd.Timestamp.now().normalize() - timedelta(days=5)).date()
    return all(st.get(f"{interval}|{s}", {}).get("ended") and str(st[f"{interval}|{s}"].get("newest", "")) >= str(recent)
               for s in syms)


def report():
    """results/candle_library.md: per interval - stocks done, first day Kite gave, not on Kite, size."""
    st = _state()
    L = [f"# Kite candle library ({pd.Timestamp.now(tz='Asia/Kolkata'):%d %b %Y %H:%M} IST)", "",
         "Source: Kite Connect historical API only (no other price source). Every NSE stock Kite lists + indices. "
         "Day, 5, 15, 30 and 60-minute candles are downloaded from Kite as they are; only 3- and 10-minute are built (from 1- and 5-minute).", "",
         "| Interval | Stocks complete | Earliest day Kite gave | Median first day | Not on Kite | Size on disk |",
         "|---|---|---|---|---|---|"]
    for interval in ORDER:
        syms = symbols(interval)
        S = [st.get(f"{interval}|{s}", {}) for s in syms]
        firsts = [pd.Timestamp(x["first"]) for x in S if x.get("first")]
        folder = BASE / interval
        size = sum(p.stat().st_size for p in folder.glob("*.parquet")) / 1e6 if folder.exists() else 0
        L.append(f"| {interval} | {sum(1 for x in S if x.get('ended'))}/{len(syms)} | "
                 f"{min(firsts).date() if firsts else '-'} | {pd.Series(firsts).median().date() if firsts else '-'} | "
                 f"{sum(1 for x in S if x.get('missing'))} | {size:,.0f} MB |")
    L += ["", f"Data folder total: {data_size_gb():.2f} GB (smaller intervals pause above {MAX_DATA_GB:.0f} GB"
              + (" - **storage limit reached: the owner decides where to keep more**" if st.get("_storage_full") else "")
              + ")."]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(L) + "\n")
    return L
