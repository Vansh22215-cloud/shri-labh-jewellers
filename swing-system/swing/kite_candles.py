"""Kite candle library (owner 20 Nov: "download 1, 5, 15, 60-minute plus 1 day ... all available, not just 13 years").
Read-only Kite historical API, on GitHub (keys live only there), in small chunks around the clock while the day's
login is valid - never in market hours (8:45 am - 3:50 pm weekdays), at most 10 minutes per step.
  interval   stocks                                   history
  day        every NSE stock + NIFTY indices + VIX    all available (kite_daily.py: back to 2000)
  60minute   current top-300                          all available
  15minute   current top-300                          all available
  5minute    current top-300                          all available
  minute     current top-300                          last 2 years, then kept going forward
3-, 10- and 30-minute candles are built exactly from 1-, 5- and 15-minute ones (resample(); no extra downloads).
Each stock is downloaded BACKWARDS from today until Kite returns nothing (= the start of what Kite has), then topped
up forwards every day. Files: data/kite_candles/<interval>/<SYM>.parquet (GitHub's private cache, never in git).
A size guard stops the intraday downloads before GitHub's cache limit is at risk."""
import json
import time
from datetime import timedelta

import numpy as np
import pandas as pd

from .config import DATA, ROOT, get_logger

log = get_logger()
BASE = DATA / "kite_candles"
STATE_F = BASE / "state.json"
REPORT = ROOT / "journal" / "kite_candles.md"
GAP = 0.36                                           # <= 3 historical requests a second (Kite's limit)
INTERVALS = {                                        # chunk = days per request (Kite's limits, with a margin)
    "60minute": {"chunk": 395, "min_start": pd.Timestamp("2005-01-01")},
    "15minute": {"chunk": 195, "min_start": pd.Timestamp("2005-01-01")},
    "5minute": {"chunk": 95, "min_start": pd.Timestamp("2005-01-01")},
    "minute": {"chunk": 58, "min_start": None, "years": 2},
}
ORDER = ["60minute", "15minute", "5minute", "minute"]   # most useful per byte first
MAX_DATA_GB = 4.0                                    # whole data folder (GitHub keeps 10 GB of cache in all)
MAX_MINUTES = 10                                     # one step never runs longer (other jobs wait for it)
DERIVED = {"3minute": ("minute", "3min"), "10minute": ("5minute", "10min"), "30minute": ("15minute", "30min")}


def _state():
    try:
        return json.loads(STATE_F.read_text())
    except Exception:
        return {}


def _save_state(st):
    BASE.mkdir(parents=True, exist_ok=True)
    STATE_F.write_text(json.dumps(st))


def top300():
    try:
        u = pd.read_csv(DATA / "universe_history.csv")
        last = u[u["asof"] == u["asof"].max()]
        return ["NIFTY50", "BANKNIFTY"] + [str(s) for s in last.nsmallest(300, "rank")["symbol"]]
    except Exception:
        return ["NIFTY50"]


def _path(interval, sym):
    return BASE / interval / f"{sym.replace('/', '_')}.parquet"


def _fetch(sym, interval, fr, to, retries=3):
    from . import kite
    ins = kite.instruments()
    name = kite.INDEX.get(sym, sym)
    row = ins[ins["tradingsymbol"] == name]
    if not len(row):
        return None
    tok = int(row["instrument_token"].iloc[0])
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
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    df = pd.DataFrame([x[:6] for x in c], columns=["date", "open", "high", "low", "close", "volume"])
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
    df = df.set_index("date")
    return df.astype({"open": "float32", "high": "float32", "low": "float32", "close": "float32", "volume": "float64"})


def _store(interval, sym, df):
    f = _path(interval, sym)
    f.parent.mkdir(parents=True, exist_ok=True)
    if f.exists():
        old = pd.read_parquet(f)
        df = pd.concat([old[~old.index.isin(df.index)], df])
    df.sort_index().to_parquet(f, compression="zstd")


def load(sym, interval):
    """Kite candles of one stock. interval: minute, 3minute, 5minute, 10minute, 15minute, 30minute, 60minute.
    (Daily candles: kite_daily / data_prices.load.) None if not downloaded."""
    if interval in DERIVED:
        base, rule = DERIVED[interval]
        b = load(sym, base)
        if b is None or not len(b):
            return None
        g = b.resample(rule, origin="start_day", offset="15min", label="left", closed="left")   # NSE opens 9:15
        out = pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(), "low": g["low"].min(),
                            "close": g["close"].last(), "volume": g["volume"].sum()}).dropna(subset=["open"])
        return out
    f = _path(interval, sym)
    return pd.read_parquet(f) if f.exists() else None


def data_size_gb():
    tot = 0
    for p in DATA.rglob("*"):
        try:
            if p.is_file():
                tot += p.stat().st_size
        except Exception:
            pass
    return tot / 1e9


def _in_market_hours(now=None):
    """8:45 am - 3:50 pm on weekdays: no history downloads (live scans, the 3:15-3:45 buy window and VANTAGE first)."""
    now = now or pd.Timestamp.now(tz="Asia/Kolkata")
    m = now.hour * 60 + now.minute
    return now.weekday() < 5 and 8 * 60 + 45 <= m <= 15 * 60 + 50


def step(max_requests=1500, today=None):
    """One chunk of work: backwards backfill (until Kite has no more), then forward top-ups. -> summary dict."""
    from . import kite
    if not kite.logged_in():
        return {"skipped": "not logged in"}
    if _in_market_hours():
        return {"skipped": "market hours"}
    if data_size_gb() > MAX_DATA_GB:
        log.warning("Kite candles: data folder above %.1f GB - intraday downloads paused", MAX_DATA_GB)
        return {"skipped": "storage limit"}
    today = pd.Timestamp(today or pd.Timestamp.now().normalize()).normalize()
    st, used, t0 = _state(), 0, time.time()
    syms = top300()
    for interval in ORDER:
        cfg = INTERVALS[interval]
        start = cfg["min_start"] or (today - pd.DateOffset(years=cfg["years"]))
        for sym in syms:
            k = f"{interval}|{sym}"
            s = st.get(k, {})
            while True:                                          # this stock, until done or out of budget
                if used >= max_requests or time.time() - t0 > MAX_MINUTES * 60 or (used % 50 == 0 and _in_market_hours()):
                    used = max(used, max_requests)
                    break
                try:
                    if not s.get("ended"):                       # backwards: today -> as far back as Kite has
                        to = pd.Timestamp(s["oldest"]) - timedelta(days=1) if s.get("oldest") else today
                        fr = max(to - timedelta(days=cfg["chunk"]), start)
                        d = _fetch(sym, interval, fr, to)
                        used += 1
                        if d is None:
                            s.update(ended=True, newest=str(today.date()), missing=True)
                        else:
                            if len(d):
                                _store(interval, sym, d)
                                s["newest"] = max(s.get("newest", "0000"), str(d.index.max().date()))
                                s["first"] = str(d.index.min().date())
                                s["empty_runs"] = 0
                            else:
                                s["empty_runs"] = s.get("empty_runs", 0) + 1
                            s["oldest"] = str(fr.date())
                            if s["empty_runs"] >= 2 or fr <= start:   # two empty chunks back = start of Kite's history
                                s["ended"] = True
                            s.setdefault("newest", str(today.date()))
                    elif pd.Timestamp(s.get("newest", "2000-01-01")) < today:     # forwards top-up
                        fr = pd.Timestamp(s["newest"]) - timedelta(days=3)
                        d = _fetch(sym, interval, fr, today)
                        used += 1
                        if d is not None and len(d):
                            _store(interval, sym, d)
                        s["newest"] = str(today.date())
                    else:
                        break
                except Exception as e:
                    st[k] = s
                    _save_state(st)
                    log.warning("Kite candles %s %s: %s", interval, sym, type(e).__name__)
                    return {"requests": used, "stopped": type(e).__name__}
                st[k] = s
            if used >= max_requests:
                break
        if used >= max_requests:
            break
    _save_state(st)
    return {"requests": used, **progress(st, syms)}


def progress(st=None, syms=None):
    st = st if st is not None else _state()
    syms = syms or top300()
    out = {}
    for interval in ORDER:
        done = sum(1 for s in syms if st.get(f"{interval}|{s}", {}).get("ended"))
        out[interval] = f"{done}/{len(syms)}"
    out["complete"] = all(st.get(f"{i}|{s}", {}).get("ended") for i in ORDER for s in syms)
    return out


def report():
    """journal/kite_candles.md: per interval - stocks done, first day Kite has, rows, missing (not on Kite)."""
    st = _state()
    syms = top300()
    L = [f"# Kite candle library ({pd.Timestamp.now(tz='Asia/Kolkata'):%d %b %Y %H:%M} IST)", "",
         "Source: Kite Connect historical API only. Intraday: current top-300 + NIFTY 50 + NIFTY BANK. Daily for every "
         "NSE stock: journal/kite_coverage.md. 3/10/30-minute candles are built from 1/5/15-minute ones.", "",
         "| Interval | Stocks complete | Earliest day Kite gave | Median first day | Not on Kite | Size on disk |",
         "|---|---|---|---|---|---|"]
    for interval in ORDER:
        S = [st.get(f"{interval}|{s}", {}) for s in syms]
        firsts = [pd.Timestamp(x["first"]) for x in S if x.get("first")]
        size = sum(p.stat().st_size for p in (BASE / interval).glob("*.parquet")) / 1e6 if (BASE / interval).exists() else 0
        L.append(f"| {interval} | {sum(1 for x in S if x.get('ended'))}/{len(syms)} | "
                 f"{min(firsts).date() if firsts else '-'} | {pd.Series(firsts).median().date() if firsts else '-'} | "
                 f"{sum(1 for x in S if x.get('missing'))} | {size:,.0f} MB |")
    L += ["", f"Data folder total: {data_size_gb():.2f} GB (intraday downloads pause above {MAX_DATA_GB:.0f} GB)."]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(L) + "\n")
    return L
