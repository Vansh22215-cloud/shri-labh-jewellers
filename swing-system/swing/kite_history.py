"""Kite Connect historical candles, used to the full (owner 19 Nov: "are we using Kite at maximum utilisation?").
Every evening on GitHub (research job), read-only market data:
  1. BACKFILL: 15-minute candles of every top-300 stock (and NIFTY 50) from 2019, ~2,000 requests a night (Kite allows
     3 a second), until complete; 5-minute candles of the last 2 years for the two windows that matter for execution
     (9:15-9:45 and 15:00-15:30).
  2. DAILY: the last 5 days for all of them.
  3. Stored compactly in data/kite_hist (GitHub's private cache - Kite data is never committed to the public repo):
     per stock and day: open, price at 3:15 and 3:20 pm, close, VWAP, first-30-minute and last-hour return,
     close vs VWAP; plus the 5-minute window bars.
  4. RESEARCH (when 80% of stocks have 2+ years): the real 3:20 pm price vs the close on VANTAGE signal days (is the
     tested "buy at 3:20 pm = the close" assumption true?), and whether intraday facts on the signal day predict
     VANTAGE trade results -> journal/kite_research.md (results only)."""
import json
import time
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from .config import DATA, ROOT, get_logger

log = get_logger()
BASE = DATA / "kite_hist"
STATE_F = BASE / "state.json"
REPORT = ROOT / "journal" / "kite_research.md"
START = pd.Timestamp("2019-01-01")
CHUNK = {"15minute": 195, "5minute": 95}           # Kite's per-request day limits (200 / 100), with margin
GAP = 0.36                                          # <= 3 requests a second


def _state():
    try:
        return json.loads(STATE_F.read_text())
    except Exception:
        return {}


def _save_state(st):
    BASE.mkdir(parents=True, exist_ok=True)
    STATE_F.write_text(json.dumps(st))


def symbols():
    try:
        u = pd.read_csv(DATA / "universe_history.csv")
        last = u[u["asof"] == u["asof"].max()]
        return ["NIFTY50"] + [str(s) for s in last.nsmallest(300, "rank")["symbol"]]
    except Exception:
        return ["NIFTY50"]


def _candles(sym, interval, fr, to):
    from . import kite
    ins = kite.instruments()
    name = kite.INDEX.get(sym, sym)
    row = ins[ins["tradingsymbol"] == name]
    if not len(row):
        return None
    tok = int(row["instrument_token"].iloc[0])
    time.sleep(GAP)
    r = kite._get(f"/instruments/historical/{tok}/{interval}",
                  params={"from": f"{fr:%Y-%m-%d} 09:00:00", "to": f"{to:%Y-%m-%d} 15:35:00"}, timeout=60)
    c = r.json()["data"]["candles"]
    if not c:
        return pd.DataFrame()
    df = pd.DataFrame([x[:6] for x in c], columns=["date", "open", "high", "low", "close", "volume"])
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
    return df


def summarise(b15):
    """15-minute bars -> one row per day."""
    if b15 is None or not len(b15):
        return pd.DataFrame()
    b = b15.copy()
    b["day"] = b["date"].dt.normalize()
    b["hm"] = b["date"].dt.hour * 60 + b["date"].dt.minute
    b["pv"] = (b["high"] + b["low"] + b["close"]) / 3 * b["volume"]
    out = []
    for d, g in b.groupby("day"):
        g = g.sort_values("hm")
        o, c = float(g["open"].iloc[0]), float(g["close"].iloc[-1])
        v = float(g["volume"].sum())
        vwap = float(g["pv"].sum() / v) if v > 0 else np.nan
        at = lambda m: float(g.loc[g["hm"] <= m, "close"].iloc[-1]) if (g["hm"] <= m).any() else np.nan
        p945, p1430 = at(9 * 60 + 30), at(14 * 60 + 15)          # close of the 9:30 bar = price at 9:45; 14:15 bar = 2:30 pm
        p1515 = float(g.loc[g["hm"] == 15 * 60 + 15, "open"].iloc[0]) if (g["hm"] == 915).any() else at(15 * 60)
        out.append({"day": d, "open": o, "close": c, "vwap": vwap, "p1515": p1515,
                    "first30_pct": (p945 / o - 1) * 100 if o else np.nan,
                    "last_hour_pct": (c / p1430 - 1) * 100 if p1430 == p1430 and p1430 else np.nan,
                    "close_vs_vwap_pct": (c / vwap - 1) * 100 if vwap == vwap and vwap else np.nan, "volume": v})
    return pd.DataFrame(out)


def windows(b5):
    """5-minute bars of 9:15-9:45 and 15:00-15:30 only (what execution research needs)."""
    if b5 is None or not len(b5):
        return pd.DataFrame()
    hm = b5["date"].dt.hour * 60 + b5["date"].dt.minute
    return b5[((hm >= 555) & (hm < 585)) | ((hm >= 900) & (hm < 930))]


def _append(path, df, key):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        old = pd.read_csv(path, parse_dates=[key])
        df = pd.concat([old[~old[key].isin(df[key])], df]).sort_values(key)
    df.to_csv(path, index=False, compression="gzip")


def step(max_requests=2000, today=None):
    """One evening's work: daily top-up for all, then backfill until the request budget is used."""
    from . import kite
    if not kite.logged_in():
        log.info("Kite history: not logged in today - skipped")
        return {"skipped": "not logged in"}
    today = pd.Timestamp(today or datetime.now().date())
    st = _state()
    used = 0
    syms = symbols()
    for sym in syms:                                   # 1) last 5 days for stocks whose history is already complete
        if used >= max_requests:
            break
        if pd.Timestamp(st.get(f"{sym}|15minute", "2000-01-01")) < today - timedelta(days=8):
            continue                                   # the backfill below reaches today for the others
        try:
            b15 = _candles(sym, "15minute", today - timedelta(days=7), today)
            b5 = _candles(sym, "5minute", today - timedelta(days=7), today)
            used += 2
            if b15 is not None and len(b15):
                _append(BASE / "summary" / f"{sym}.csv.gz", summarise(b15), "day")
            if b5 is not None and len(b5):
                _append(BASE / "m5win" / f"{sym}.csv.gz", windows(b5), "date")
        except Exception as e:
            log.warning("Kite history daily %s: %s", sym, type(e).__name__)
            if "expired" in str(e) or "not logged" in str(e) or isinstance(e, PermissionError):
                break
    for sym in syms:                                   # 2) backfill, oldest gap first
        for interval, start in (("15minute", START), ("5minute", today - timedelta(days=730))):
            k = f"{sym}|{interval}"
            done_to = pd.Timestamp(st.get(k, str((start - timedelta(days=1)).date())))
            while used < max_requests and done_to < today - timedelta(days=7):
                fr = done_to + timedelta(days=1)
                to = min(fr + timedelta(days=CHUNK[interval]), today - timedelta(days=1))
                try:
                    b = _candles(sym, interval, fr, to)
                    used += 1
                except Exception as e:
                    log.warning("Kite history backfill %s %s: %s", sym, interval, type(e).__name__)
                    _save_state(st)
                    return {"requests": used, "stopped": type(e).__name__}
                if b is not None and len(b):
                    if interval == "15minute":
                        _append(BASE / "summary" / f"{sym}.csv.gz", summarise(b), "day")
                    else:
                        _append(BASE / "m5win" / f"{sym}.csv.gz", windows(b), "date")
                done_to = to
                st[k] = str(to.date())
            if used >= max_requests:
                break
        if used >= max_requests:
            break
    _save_state(st)
    complete = sum(1 for s in syms if pd.Timestamp(st.get(f"{s}|15minute", "2000-01-01")) >= today - timedelta(days=8))
    log.info("Kite history: %d requests, %d of %d stocks complete", used, complete, len(syms))
    return {"requests": used, "complete": complete, "of": len(syms)}


def coverage():
    st = _state()
    syms = symbols()
    two_years = pd.Timestamp.now() - timedelta(days=730)
    have = 0
    for s in syms:
        f = BASE / "summary" / f"{s}.csv.gz"
        if f.exists() and pd.Timestamp(st.get(f"{s}|15minute", "2000-01-01")) > two_years:
            have += 1
    return have / max(1, len(syms))


def research():
    """3:20 pm reality check + intraday facts vs VANTAGE results (runs when coverage >= 80%)."""
    cov = coverage()
    L = [f"# Kite intraday research ({pd.Timestamp.now(tz='Asia/Kolkata'):%d %b %Y})", "",
         f"Coverage: {cov * 100:.0f}% of the top-300 stocks have 15-minute history from Kite.", ""]
    if cov < 0.8:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text("\n".join(L + ["Still downloading (about 2,000 requests an evening). Research starts at 80%."]) + "\n")
        return None
    try:
        T = pd.read_csv(ROOT.parent / "vantage-ai" / "validation" / "improve3_trades_C1.csv", parse_dates=["signal"])
    except Exception:
        return None
    rows = []
    for sym, g in T.groupby("sym"):
        f = BASE / "summary" / f"{sym}.csv.gz"
        if not f.exists():
            continue
        S = pd.read_csv(f, parse_dates=["day"]).set_index("day")
        m = g.join(S, on="signal", how="inner", rsuffix="_k")
        rows.append(m)
    if not rows:
        return None
    M = pd.concat(rows)
    M["net"] = M["exit"] / M["entry"] - 1 - 0.0075
    M["buy_320_vs_close_pct"] = (M["p1515"] / M["close_k"] - 1) * 100
    gap = M["buy_320_vs_close_pct"].dropna()
    L += ["## Is buying at 3:15-3:20 pm the same as buying at the close? (the tested assumption)",
          f"- VANTAGE signal days with Kite data: {len(gap):,}. Price at 3:15 pm vs the close: average {gap.mean():+.2f}%, "
          f"median {gap.median():+.2f}% (positive = the 3:15 pm price was higher, i.e. buying then cost more).", ""]
    L += ["## Do intraday facts on the signal day predict the trade? (top vs bottom third, after ~0.75% costs)", ""]
    for c, nm in (("close_vs_vwap_pct", "close vs the day's VWAP"), ("last_hour_pct", "last-hour move"),
                  ("first30_pct", "first-30-minute move")):
        x = M.dropna(subset=[c])
        if len(x) < 300:
            continue
        hi, lo = x[c] >= x[c].quantile(2 / 3), x[c] <= x[c].quantile(1 / 3)
        for per, P in (("before Nov 2023", x["signal"] < "2023-11-01"), ("Nov 2023+", x["signal"] >= "2023-11-01")):
            a, b = x.loc[hi & P, "net"], x.loc[lo & P, "net"]
            if len(a) > 30 and len(b) > 30:
                L.append(f"- {nm}, {per}: top third {a.mean() * 100:+.2f}% vs bottom third {b.mean() * 100:+.2f}% a trade "
                         f"(n={len(a)}/{len(b)})")
    L += ["", "Information for research; a rule needs the usual pre-registered test and the owner's yes."]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(L) + "\n")
    return M


def run():
    try:
        r = step()
        if r.get("requests"):
            research()
        return r
    except Exception as e:
        log.warning("Kite history failed: %s", type(e).__name__)
        return {"error": type(e).__name__}
