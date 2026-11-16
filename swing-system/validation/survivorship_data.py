"""Audit 17 Nov: SURVIVORSHIP repair for the backtests.

Yahoo has no history for delisted / merged / collapsed companies, so 28% of the 2013 top-300 universe (6% of 2023)
had NO price data and silently dropped out of every backtest - the classic survivorship bias.
This script rebuilds their DAILY prices from NSE's official daily bhavcopies (public archive) and adjusts them for
splits / bonuses with NSE's own previous-close field (on an ex-date NSE publishes the ADJUSTED previous close):
    factor_t = PREVCLOSE_t / CLOSE_(t-1); all prices before t are multiplied by it (back-adjustment).
Output: data/delisted_prices.csv.gz (symbol, date, open, high, low, close, volume, adj_close) - read by
data_prices.load() as a fallback when Yahoo has nothing. Resumable (keeps a list of finished dates).
Usage: python validation/survivorship_data.py
"""
import io
import json
import sys
import time
import zipfile
from datetime import date

import pandas as pd

ROOT = "/home/user/shri-labh-jewellers/swing-system"
sys.path.insert(0, ROOT)
from swing import data_nse, data_prices  # noqa: E402

OUT = f"{ROOT}/data/delisted_prices.csv.gz"
RAW = f"{ROOT}/data/delisted_raw.csv"
DONE = f"{ROOT}/data/delisted_done.json"


def needed():
    u = pd.read_csv(f"{ROOT}/data/universe_history.csv")
    syms = sorted(set(u[u["rank"] <= 500]["symbol"].astype(str)))
    out = []
    for s in syms:
        d = data_prices.load(s, allow_fallback=False) if "allow_fallback" in data_prices.load.__code__.co_varnames \
            else data_prices.load(s)
        if d is None or len(d) == 0:
            out.append(s)
    return set(out)


def parse(raw, d, syms):
    z = zipfile.ZipFile(io.BytesIO(raw))
    df = pd.read_csv(z.open(z.namelist()[0]))
    df.columns = [c.strip() for c in df.columns]
    if "TckrSymb" in df.columns:
        df = df.rename(columns={"TckrSymb": "symbol", "SctySrs": "series", "OpnPric": "open", "HghPric": "high",
                                "LwPric": "low", "ClsPric": "close", "PrvsClsgPric": "prev", "TtlTradgVol": "volume"})
    else:
        df = df.rename(columns={"SYMBOL": "symbol", "SERIES": "series", "OPEN": "open", "HIGH": "high", "LOW": "low",
                                "CLOSE": "close", "PREVCLOSE": "prev", "TOTTRDQTY": "volume"})
    df["series"] = df["series"].astype(str).str.strip()
    df = df[df["series"].isin(["EQ", "BE", "BZ"]) & df["symbol"].astype(str).isin(syms)]
    df = df[["symbol", "open", "high", "low", "close", "prev", "volume"]].copy()
    df["date"] = str(d)
    return df


# bonus a:b -> b/(a+b); split x->y -> y/x
SPLIT_RATIOS = [1 / 2, 1 / 3, 1 / 4, 1 / 5, 1 / 10, 2 / 3, 2 / 5, 3 / 5, 1 / 6, 1 / 8, 1 / 20]


def build():
    raw = pd.read_csv(RAW).drop_duplicates(["symbol", "date"]).sort_values(["symbol", "date"])
    out = []
    for s, g in raw.groupby("symbol"):
        g = g.copy()
        prev_close = g["close"].shift()
        f = (g["prev"] / prev_close).where(prev_close > 0).fillna(1.0)
        f = f.where((f - 1).abs() > 0.02, 1.0)          # ignore tiny rounding differences
        # Audit: older NSE files often did NOT adjust PREVCLOSE for splits / bonuses (Castrol 2012 bonus 1:1, Cadila
        # 2015 split 5:1 showed as -50% / -80% 'crashes'). A day whose OPEN and CLOSE both sit within 6% of a standard
        # split/bonus ratio of the previous close is treated as a corporate action. Real crashes almost never open
        # AND close on such a ratio; any that do are mis-adjusted (documented in BACKTEST_VALIDATION.md).
        ro, rc = g["open"] / prev_close, g["close"] / prev_close
        hit = pd.Series(1.0, index=g.index)
        for k in SPLIT_RATIOS:
            m = ((ro / k - 1).abs() < 0.06) & ((rc / k - 1).abs() < 0.06) & (f == 1.0)
            hit = hit.where(~m | (hit != 1.0), k)
        f = f * hit
        # demergers / odd ratios / ETF unit splits: NSE price bands (mostly 20%) make an OPENING gap of more than 25%
        # almost always a corporate action -> adjust by the opening gap, keep that day's own move (open -> close).
        # Crashes that happen during the day (DHFL 21 Sep 2018 opened flat) are kept as real.
        big = ((ro - 1).abs() > 0.25) & (f == 1.0) & ro.notna() & (ro > 0)
        f = f.where(~big, ro)
        # cumulative factor for each row = product of factors of all LATER ex-dates
        cum = f[::-1].cumprod()[::-1].shift(-1).fillna(1.0)
        g["adj_close"] = g["close"] * cum
        out.append(g[["symbol", "date", "open", "high", "low", "close", "volume", "adj_close"]])
    pd.concat(out).to_csv(OUT, index=False, compression="gzip")
    print("built", OUT, sum(len(x) for x in out), "rows,", len(out), "symbols")


if __name__ == "__main__":
    syms = needed()
    print("symbols without Yahoo data:", len(syms), flush=True)
    try:
        done = set(json.load(open(DONE)))
    except Exception:
        done = set()
    days = pd.bdate_range("2012-06-01", "2026-11-13")
    t0 = time.time()
    for i, d in enumerate(days):
        ds = str(d.date())
        if ds in done:
            continue
        raw = data_nse._get(data_nse._bhav_path(d.date()), timeout=20, tries=2)
        if raw is not None:
            try:
                df = parse(raw, d.date(), syms)
                df.to_csv(RAW, mode="a", header=not pd.io.common.file_exists(RAW), index=False)
            except Exception as e:
                print("parse fail", ds, e, flush=True)
        done.add(ds)
        if i % 100 == 0:
            json.dump(sorted(done), open(DONE, "w"))
            print(f"{ds} {len(done)}/{len(days)} {time.time() - t0:.0f}s", flush=True)
        time.sleep(0.25)
    json.dump(sorted(done), open(DONE, "w"))
    build()
