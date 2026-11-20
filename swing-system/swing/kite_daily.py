"""Kite (exchange) daily candles for every NSE stock + NIFTY 50 / NIFTY BANK / INDIA VIX, all Kite has (back to 2000) (owner 19 Nov: "did the tests use accurate Kite data?
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
START = pd.Timestamp("2000-01-01")    # owner 20 Nov: all Kite has, not just 13 years
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
        return ["NIFTY50"] + symbols() + ["BANKNIFTY", "INDIAVIX"]
    except Exception:
        return ["NIFTY50", "BANKNIFTY", "INDIAVIX"]


EXTRA_INDEX = {"INDIAVIX": "INDIA VIX"}         # daily history only (owner 20 Nov: indices + VIX too)


def _day_candles(sym, fr, to):
    from . import kite
    ins = kite.instruments()
    name = {**kite.INDEX, **EXTRA_INDEX}.get(sym, sym)
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
    used += backfill(st, syms, max_requests - used) if used < max_requests else 0
    _save_state(st)
    done = sum(1 for s in syms if pd.Timestamp(st.get(s, "2000-01-01")) >= today - timedelta(days=3))
    log.info("Kite daily: %d requests, %d of %d stocks complete", used, done, len(syms))
    return {"requests": used, "complete": done, "of": len(syms)}


def backfill(st, syms, budget):
    """Owner 20 Nov ("all available, not just 13 years"): stocks first downloaded from 2011 are read further back,
    chunk by chunk, until Kite returns nothing or 2000-01-01 is reached. State: st["back|SYM"] = True when done."""
    used = 0
    for sym in syms:
        if used >= budget or st.get("back|" + sym) or sym not in st:
            continue
        k = _raw(sym)
        while used < budget:
            first = k.index.min() if k is not None and len(k) else None
            if first is None or first <= START + timedelta(days=7):
                st["back|" + sym] = True
                break
            to = first - timedelta(days=1)
            fr = max(START, to - timedelta(days=CHUNK_DAYS))
            try:
                d = _day_candles(sym, fr, to)
                used += 1
            except Exception as e:
                log.warning("Kite daily backfill %s: %s", sym, type(e).__name__)
                return used
            if d is None or not len(d):
                st["back|" + sym] = True                   # nothing older on Kite = the start of its history
                break
            _store(sym, d)
            k = _raw(sym)
    return used


def history_complete(today=None):
    """All Kite has, for (almost) every stock: up to date AND read back as far as Kite goes (owner 20 Nov: start
    the backtests only once everything is downloaded)."""
    st = _state()
    syms = [s for s in all_symbols() if s in st]
    return coverage(today) >= 0.999 and all(st.get("back|" + s) for s in syms)


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


STD_RATIOS = (2.0, 3.0, 4.0, 5.0, 10.0, 1.5, 5 / 3, 2.5)   # clear split/bonus ratios only (1:4, 1:5 bonuses could be
                                                      # confused with a real 17-20% crash - left to the audit to flag)


def split_factors_from_prices(k):
    """Kite-only corporate-action detection (strict mode; no Yahoo): an overnight drop whose open AND close both sit
    within 4% of a standard split/bonus ratio of the previous close, with volume not collapsing -> a split/bonus on
    that day (the same idea NSE's own adjusted previous close uses). -> {date: factor}"""
    out = {}
    pc = k["close"].shift()
    for d in k.index[1:]:
        p = pc.get(d)
        if not p or p != p:
            continue
        o, c = k.at[d, "open"], k.at[d, "close"]
        for r in STD_RATIOS:
            if abs(o * r / p - 1) < 0.04 and abs(c * r / p - 1) < 0.06:
                out[d] = r
                break
    return out


def frame_strict(sym):
    """STRICT KITE (owner 19 Nov): Kite exchange candles only - no Yahoo days, no Yahoo adjustments. Splits/bonuses:
    none if Kite is already adjusted (decided from the data), else detected from Kite's own prices. Price-only
    (no dividends), the same for NIFTY. attrs: source, first/last day, corporate-action method, splits found."""
    k = _raw(sym)
    if k is None or not len(k):
        return None
    k = k[["open", "high", "low", "close", "volume"]].astype(float).sort_index().copy()
    adj = kite_is_adjusted()
    found = {} if adj else split_factors_from_prices(k)
    if found:
        f = pd.Series(1.0, index=k.index)
        for d, r in found.items():
            f[k.index < d] *= r
        for c in ("open", "high", "low", "close"):
            k[c] = k[c] / f
        k["volume"] = k["volume"] * f
    k["adj_close"] = k["close"]
    k["dividends"], k["splits"] = 0.0, 0.0
    k.attrs.update(source="kite", first=str(k.index[0].date()), last=str(k.index[-1].date()),
                   ca=("kite-adjusted" if adj else f"detected from Kite prices ({len(found)} split/bonus)"), pure_kite=True)
    return k


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
        k, y = frame_strict(sym), data_prices._load_yahoo(sym)     # verify exactly what strict research uses
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



COVERAGE = ROOT / "journal" / "kite_coverage.md"


def coverage_report():
    """FIRST STEP of the strict re-run: is Kite's history complete enough? Nothing is claimed before this.
    Calendar = the days Kite has for NIFTY 50. Checked for every stock that was ever in the top-300 and every
    stock on today's NSE list: on Kite or not, first and last Kite day, missing days inside its own Kite span."""
    import json as _j
    st = _state()
    cal = _raw("NIFTY50")
    out = {"made": str(pd.Timestamp.now(tz="Asia/Kolkata"))[:16]}
    L = [f"# Kite data coverage ({out['made']} IST)", "",
         "Verified before any result is reported (owner 19 Nov). Strict Kite mode: no Yahoo days, no Yahoo adjustments.", ""]
    if cal is None or not len(cal):
        L.append("Kite NIFTY 50 history not downloaded yet - coverage cannot be verified.")
        COVERAGE.write_text("\n".join(L) + "\n")
        return {"ok": False}
    days = cal.index[cal.index >= START]
    try:
        u = pd.read_csv(DATA / "universe_history.csv", parse_dates=["asof"])
        top_ever = u[u["rank"] <= 300].groupby("symbol")["asof"].min()
    except Exception:
        top_ever = pd.Series(dtype="datetime64[ns]")
    try:
        dl = set(pd.read_csv(DATA / "delisted_prices.csv.gz", usecols=["symbol"])["symbol"])
    except Exception:
        dl = set()
    rows = []
    for sym in sorted(set(all_symbols()) | set(top_ever.index)):
        k = _raw(sym)
        r = {"sym": sym, "top300_ever": sym in top_ever.index, "on_kite": k is not None and len(k) > 0,
             "delisted_nse": sym in dl}
        if r["on_kite"]:
            kd = k.index[k.index >= START]
            span = days[(days >= kd.min()) & (days <= kd.max())] if len(kd) else days[:0]
            r.update(first=kd.min(), last=kd.max(), n=len(kd), missing=int(len(span.difference(kd))),
                     covers_top300_start=(kd.min() <= top_ever.get(sym, pd.Timestamp("2100-01-01"))) if sym in top_ever.index else None)
        rows.append(r)
    C = pd.DataFrame(rows)
    K = C[C["on_kite"]]
    T = C[C["top300_ever"]]
    tk = T[T["on_kite"]]
    out.update(stocks=len(C), on_kite=int(C["on_kite"].sum()), top300_ever=len(T), top300_on_kite=len(tk),
               top300_delisted_nse=int((~T["on_kite"] & T["delisted_nse"]).sum()),
               top300_missing_both=int((~T["on_kite"] & ~T["delisted_nse"]).sum()),
               kite_first_day=str(K["first"].min().date()) if len(K) else None,
               kite_last_day=str(K["last"].max().date()) if len(K) else None,
               stocks_from_2013=int((K["first"] <= pd.Timestamp("2013-01-31")).sum()) if len(K) else 0,
               missing_stock_days=int(K["missing"].sum()) if len(K) else 0,
               days_on_kite=int(K["n"].sum()) if len(K) else 0,
               top300_kite_covers_membership=int(tk["covers_top300_start"].fillna(False).sum()),
               kite_adjusted=bool(kite_is_adjusted()), calendar_days=len(days))
    pct = lambda a, b: f"{a / b * 100:.1f}%" if b else "-"
    L += ["| Check | Result |", "|---|---|",
          f"| Stocks checked (today's NSE list + every past top-300 member) | {out['stocks']:,} |",
          f"| On Kite | {out['on_kite']:,} ({pct(out['on_kite'], out['stocks'])}) |",
          f"| Kite date range | {out['kite_first_day']} to {out['kite_last_day']} ({out['calendar_days']:,} NIFTY trading days) |",
          f"| Stocks with Kite data from Jan 2013 or earlier | {out['stocks_from_2013']:,} |",
          f"| Missing stock-days inside each stock's own Kite span | {out['missing_stock_days']:,} of {out['days_on_kite'] + out['missing_stock_days']:,} ({pct(out['missing_stock_days'], out['days_on_kite'] + out['missing_stock_days'])}) |",
          f"| Past top-300 members | {out['top300_ever']:,} |",
          f"| ... on Kite | {out['top300_on_kite']:,} (Kite data reaches back to their first top-300 month: {out['top300_kite_covers_membership']:,}) |",
          f"| ... not on Kite because delisted (left out of research - owner 20 Nov) | {out['top300_delisted_nse']:,} |",
          f"| ... on neither (dropped and listed) | {out['top300_missing_both']:,} |",
          f"| Splits/bonuses | {'Kite data is already adjusted (checked against Yahoo split dates)' if out['kite_adjusted'] else 'Kite data is NOT adjusted: detected from Kite prices (clear ratios only)'} |", ""]
    miss = C[C["top300_ever"] & ~C["on_kite"] & ~C["delisted_nse"]]["sym"].tolist()
    if miss:
        L += ["Past top-300 members with no data from either source: " + ", ".join(miss[:60]), ""]
    worst = K.sort_values("missing", ascending=False).head(15)
    L += ["Most missing days inside a stock's own Kite span:", ""] + \
         [f"- {r.sym}: {r.missing} of {r.n + r.missing} days ({r.first.date()} to {r.last.date()})" for r in worst.itertuples() if r.missing]
    complete = out["stocks_from_2013"] and out["top300_kite_covers_membership"] >= 0.9 * max(1, out["top300_on_kite"])
    L += ["", f"**13 years complete on Kite: {'yes for ' + str(out['stocks_from_2013']) + ' stocks' if complete else 'NOT verified'}** "
              "(the claim is made only for what this table shows)."]
    out["thirteen_years_ok"] = bool(complete)
    COVERAGE.parent.mkdir(parents=True, exist_ok=True)
    COVERAGE.write_text("\n".join(L) + "\n")
    C.to_csv(BASE / "coverage_by_stock.csv", index=False)
    _j.dump(out, open(BASE / "coverage.json", "w"), indent=1, default=str)
    return out
