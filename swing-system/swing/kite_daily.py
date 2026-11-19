"""Kite (exchange) daily candles for every NSE stock since 2011 (owner 19 Nov: "did the tests use accurate Kite data?
If not, do it again" - they did not: every test used Yahoo daily prices + NSE bhavcopies for delisted stocks).
  download()  - research job on GitHub, ~4,000 requests a night (3 a second) until every stock is complete,
                then the last 10 days nightly. Files: data/kite_daily/<SYM>.csv (private cache, never in git).
  frame(sym)  - Kite prices in the same shape as a Yahoo file. Splits/bonuses: Yahoo's split factors are applied
                only if Kite turns out to be unadjusted (decided from the data, audit()). Dividends: Yahoo's
                adj_close/close ratio by date, so 'adjusted' total-return series stay comparable.
  audit()     - Kite vs Yahoo close by close -> journal/kite_data_audit.md.
Use: SWING_PRICE_SOURCE=kite makes data_prices.load() read Kite first (Yahoo fills days after Kite's last day)."""
import json
import time
from datetime import timedelta

import numpy as np
import pandas as pd

from .config import DATA, ROOT, get_logger

log = get_logger()
BASE = DATA / "kite_daily"
STATE_F = BASE / "state.json"
AUDIT = ROOT / "journal" / "kite_data_audit.md"
START = pd.Timestamp("2011-01-01")
CHUNK_DAYS = 1990                     # Kite allows 2,000 days of daily candles per request
GAP = 0.36


def _state():
    try:
        return json.loads(STATE_F.read_text())
    except Exception:
        return {}


def _save_state(st):
    BASE.mkdir(parents=True, exist_ok=True)
    STATE_F.write_text(json.dumps(st))


def all_symbols():
    try:
        from .vantage import symbols
        return ["NIFTY50"] + symbols()
    except Exception:
        return ["NIFTY50"]


def _day_candles(sym, fr, to):
    from . import kite
    ins = kite.instruments()
    name = kite.INDEX.get(sym, sym)
    row = ins[ins["tradingsymbol"] == name]
    if not len(row):
        return None
    tok = int(row["instrument_token"].iloc[0])
    time.sleep(GAP)
    r = kite._get(f"/instruments/historical/{tok}/day",
                  params={"from": f"{fr:%Y-%m-%d} 00:00:00", "to": f"{to:%Y-%m-%d} 23:59:59"}, timeout=60)
    c = r.json()["data"]["candles"]
    if not c:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    df = pd.DataFrame([x[:6] for x in c], columns=["date", "open", "high", "low", "close", "volume"])
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None).dt.normalize()
    return df.set_index("date")


def _store(sym, df):
    f = BASE / f"{sym.replace('/', '_')}.csv"
    BASE.mkdir(parents=True, exist_ok=True)
    if f.exists():
        old = pd.read_csv(f, index_col="date", parse_dates=["date"])
        df = pd.concat([old[~old.index.isin(df.index)], df]).sort_index()
    df.to_csv(f, index_label="date")


def download(max_requests=4000, today=None):
    from . import kite
    if not kite.logged_in():
        return {"skipped": "not logged in"}
    today = pd.Timestamp(today or pd.Timestamp.now().normalize())
    st, used = _state(), 0
    syms = all_symbols()
    for sym in syms:
        done_to = pd.Timestamp(st.get(sym, str((START - timedelta(days=1)).date())))
        if done_to >= today - timedelta(days=1):
            continue
        while used < max_requests and done_to < today:
            fr = done_to + timedelta(days=1) if done_to >= START else START
            if done_to >= today - timedelta(days=12):
                fr = today - timedelta(days=12)            # daily top-up: re-read the last days (late corrections)
            to = min(fr + timedelta(days=CHUNK_DAYS), today)
            try:
                d = _day_candles(sym, fr, to)
                used += 1
            except Exception as e:
                log.warning("Kite daily %s: %s", sym, type(e).__name__)
                _save_state(st)
                return {"requests": used, "stopped": type(e).__name__}
            if d is None:
                st[sym] = str(today.date())                 # not a Kite instrument (e.g. delisted): skip for good
                break
            if len(d):
                _store(sym, d)
            done_to = to
            st[sym] = str(to.date())
        if used >= max_requests:
            break
    _save_state(st)
    done = sum(1 for s in syms if pd.Timestamp(st.get(s, "2000-01-01")) >= today - timedelta(days=3))
    log.info("Kite daily: %d requests, %d of %d stocks complete", used, done, len(syms))
    return {"requests": used, "complete": done, "of": len(syms)}


def coverage(today=None):
    today = pd.Timestamp(today or pd.Timestamp.now().normalize())
    st = _state()
    syms = all_symbols()
    return sum(1 for s in syms if pd.Timestamp(st.get(s, "2000-01-01")) >= today - timedelta(days=5)) / max(1, len(syms))


def _raw(sym):
    f = BASE / f"{sym.replace('/', '_')}.csv"
    if not f.exists():
        return None
    try:
        return pd.read_csv(f, index_col="date", parse_dates=["date"])
    except Exception:
        return None


_ADJ = {}


def kite_is_adjusted():
    """Decided from the data: around Yahoo split dates, is Kite's old price already divided like Yahoo's?"""
    if "v" in _ADJ:
        return _ADJ["v"]
    from . import data_prices
    votes = []
    for f in sorted(BASE.glob("*.csv"))[:800]:
        y = data_prices._load_yahoo(f.stem)
        k = _raw(f.stem)
        if y is None or k is None or "splits" not in y:
            continue
        sp = y["splits"][(y["splits"] > 0) & (y["splits"] != 1)]
        for d, factor in sp.items():
            before = k.index[(k.index < d) & (k.index >= d - timedelta(days=60))]
            yb = y["close"].reindex(before).dropna()
            if len(yb) < 10:
                continue
            ratio = float((k["close"].reindex(yb.index) / yb).median())
            votes.append(abs(ratio - 1) < abs(ratio - factor))
        if len(votes) >= 30:
            break
    _ADJ["v"] = (sum(votes) >= len(votes) / 2) if votes else True
    return _ADJ["v"]


def frame(sym):
    """Kite prices shaped like a Yahoo price file (split/bonus- and dividend-adjusted the same way)."""
    from . import data_prices
    k = _raw(sym)
    if k is None or not len(k):
        return None
    y = data_prices._load_yahoo(sym)
    k = k[["open", "high", "low", "close", "volume"]].astype(float).copy()
    if y is not None and "splits" in y and not kite_is_adjusted():
        sp = y["splits"].where((y["splits"] > 0) & (y["splits"] != 1)).dropna()
        f = pd.Series(1.0, index=k.index)
        for d, factor in sp.items():
            f[k.index < d] *= float(factor)
        for c in ("open", "high", "low", "close"):
            k[c] = k[c] / f
        k["volume"] = k["volume"] * f
    div = (y["adj_close"] / y["close"]).reindex(k.index).ffill().bfill().fillna(1.0) if y is not None and "adj_close" in y \
        else pd.Series(1.0, index=k.index)
    k["adj_close"] = k["close"] * div
    k["dividends"], k["splits"] = 0.0, 0.0
    pure = True
    if y is not None and len(y):
        before, after = y[y.index < k.index[0]], y[y.index > k.index[-1]]   # only days Kite has not given us
        if len(before) or len(after):
            pure = False
            k = pd.concat([before[k.columns.intersection(before.columns)], k, after[k.columns.intersection(after.columns)]])
    k = k.sort_index()
    k.attrs["pure_kite"] = pure
    return k


def audit():
    from . import data_prices
    rows = []
    for f in sorted(BASE.glob("*.csv")):
        sym = f.stem
        k, y = frame(sym), data_prices._load_yahoo(sym)
        if k is None or y is None:
            continue
        j = pd.concat([k["close"].rename("k"), y["close"].rename("y")], axis=1).dropna()
        j = j[j.index >= START]
        if len(j) < 50:
            continue
        diff = (j["y"] / j["k"] - 1).abs()
        rows.append({"sym": sym, "days": len(j), "off_05": float((diff > 0.005).mean()), "off_2": float((diff > 0.02).mean()),
                     "max_off": float(diff.max()), "yahoo_missing": int(len(k[k.index >= START].index.difference(y.index))),
                     "kite_missing": int(len(y[y.index >= START].index.difference(k.index)))})
    A = pd.DataFrame(rows)
    L = [f"# Kite vs Yahoo daily prices ({pd.Timestamp.now(tz='Asia/Kolkata'):%d %b %Y})", "",
         f"Kite split-adjusted by itself: {'yes' if kite_is_adjusted() else 'no (Yahoo split factors applied)'}.", ""]
    if len(A):
        L += [f"- Stocks compared: {len(A):,}; days compared: {int(A['days'].sum()):,}",
              f"- Closes differing by more than 0.5%: {A['off_05'].mean() * 100:.2f}% of days on average; more than 2%: "
              f"{A['off_2'].mean() * 100:.2f}%",
              f"- Days Kite has that Yahoo misses: {int(A['yahoo_missing'].sum()):,}; days Yahoo has that Kite misses: "
              f"{int(A['kite_missing'].sum()):,}",
              "", "Worst 15 stocks (share of days off by more than 2%):", ""]
        for r in A.sort_values("off_2", ascending=False).head(15).itertuples():
            L.append(f"- {r.sym}: {r.off_2 * 100:.1f}% of {r.days} days, largest difference {r.max_off * 100:.0f}%")
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT.write_text("\n".join(L) + "\n")
    return A



def todays_bars_from_quotes(day=None):
    """After 3:30 pm: today's OHLCV for every NSE stock from Kite quotes (500 stocks per request) into the Kite
    daily files, so the evening jobs use exchange prices for today too. -> number of stocks written."""
    from . import kite
    if not kite.logged_in():
        return 0
    day = pd.Timestamp(day or pd.Timestamp.now().normalize()).normalize()
    syms = all_symbols()
    q = kite.quotes(syms)
    n = 0
    for sym, v in q.items():
        if not v.get("volume"):
            continue
        row = pd.DataFrame({"open": [v["open"]], "high": [max(v["high"], v["last"])], "low": [min(v["low"], v["last"])],
                            "close": [v["last"]], "volume": [float(v["volume"])]}, index=pd.DatetimeIndex([day], name="date"))
        _store(sym, row)
        n += 1
    log.info("Kite daily: today's bar written for %d stocks from quotes", n)
    return n
