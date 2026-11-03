"""Fundamentals and results dates (free source: Yahoo Finance via yfinance).

POINT-IN-TIME RULE: a financial number is treated as known only from its
"assumed publish date" = period end + 60 days for annual figures and + 45 days for
quarterly ones (SEBI LODR deadlines). Before that date the number is not used.
Every snapshot is saved with the date WE downloaded it, so over time the local
cache becomes a true point-in-time record.

Known limits (stated in every validation report):
  * Yahoo only has ~4-5 years of annual statements, restated (not as-first-published).
  * Promoter PLEDGE data is not available from any free source we may automate
    (Screener.in's terms forbid copying; NSE's API blocks scripts). Yahoo's
    "insider holding" is used as an approximation of promoter holding.
  * The quality filter is therefore NOT part of the validated backtest; it is a
    live safety screen only (it can remove a tip, never add one).
"""
import json
import time
from datetime import date

import numpy as np
import pandas as pd
import yfinance as yf

from .config import FUND, EVENTS, get_logger
from .data_prices import yahoo_ticker

log = get_logger()
EARN = EVENTS / "earnings"
EARN.mkdir(parents=True, exist_ok=True)


def _row(df, *names):
    for n in names:
        if df is not None and n in df.index:
            return df.loc[n]
    return None


def _safe(x):
    try:
        x = float(x)
        return None if not np.isfinite(x) else x
    except Exception:
        return None


def fetch_fundamentals(symbol, max_age_days=30):
    """Download (or read cached) fundamentals snapshot for one stock."""
    f = FUND / f"{symbol}.json"
    if f.exists() and (time.time() - f.stat().st_mtime) < max_age_days * 86400:
        old = json.loads(f.read_text())
        if old.get("v") == 2 or not old.get("ok"):
            return old
    snap = {"symbol": symbol, "downloaded": str(date.today()), "ok": False}
    try:
        t = yf.Ticker(yahoo_ticker(symbol))
        inc, bs, cf = t.income_stmt, t.balance_sheet, t.cashflow
        info = {}
        try:
            info = t.info or {}
        except Exception:
            pass
        rev, ni = _row(inc, "Total Revenue", "Operating Revenue"), _row(inc, "Net Income", "Net Income Common Stockholders")
        ebit = _row(inc, "EBIT", "Operating Income")
        assets, cl = _row(bs, "Total Assets"), _row(bs, "Current Liabilities")
        equity = _row(bs, "Stockholders Equity", "Common Stock Equity")
        debt = _row(bs, "Total Debt")
        ocf = _row(cf, "Operating Cash Flow")
        capex = _row(cf, "Capital Expenditure")
        intexp = _row(inc, "Interest Expense", "Interest Expense Non Operating")
        gp = _row(inc, "Gross Profit")
        ca = _row(bs, "Current Assets")
        shares = _row(bs, "Ordinary Shares Number", "Share Issued")
        years = {}
        if rev is not None:
            for per in rev.index:
                pe = pd.Timestamp(per)
                g = lambda s: _safe(s.get(per)) if s is not None else None
                years[str(pe.date())] = {
                    "published_assumed": str((pe + pd.Timedelta(days=60)).date()),
                    "revenue": g(rev), "net_income": g(ni), "ebit": g(ebit), "total_assets": g(assets),
                    "current_liabilities": g(cl), "equity": g(equity), "debt": g(debt), "ocf": g(ocf),
                    "capex": g(capex), "interest": g(intexp), "gross_profit": g(gp), "current_assets": g(ca),
                    "shares": g(shares)}
        snap.update({"ok": bool(years), "annual": years,
                     "pe": _safe(info.get("trailingPE")), "pb": _safe(info.get("priceToBook")),
                     "insider_pct": _safe(info.get("heldPercentInsiders")),
                     "sector": info.get("sector"), "industry": info.get("industry"),
                     "name": info.get("longName") or info.get("shortName"),
                     "market_cap": _safe(info.get("marketCap")), "dividend_yield": _safe(info.get("dividendYield")),
                     "summary": (info.get("longBusinessSummary") or "")[:600], "v": 2})
    except Exception as e:
        snap["error"] = str(e)
        log.warning("Fundamentals failed for %s: %s", symbol, e)
    f.write_text(json.dumps(snap, indent=1))
    time.sleep(0.5)
    return snap


def quality_summary(snap, asof=None):
    """Compute growth, margins, ROCE/ROE, debt, cash flow using only figures 'published' by asof."""
    asof = pd.Timestamp(asof or date.today())
    yrs = {k: v for k, v in (snap.get("annual") or {}).items()
           if pd.Timestamp(v["published_assumed"]) <= asof and v.get("revenue")}
    keys = sorted(yrs)
    out = {"years_available": len(keys), "flags": [], "positives": []}
    if not keys:
        out["flags"].append("no financial statements available")
        return out
    last = yrs[keys[-1]]
    first = yrs[keys[0]]
    n = len(keys) - 1

    def cagr(a, b):
        if a and b and a > 0 and b > 0 and n > 0:
            return ((b / a) ** (1 / n) - 1) * 100
        return None
    out["revenue_cagr_pct"] = cagr(first.get("revenue"), last.get("revenue"))
    out["profit_cagr_pct"] = cagr(first.get("net_income"), last.get("net_income"))
    rev, ni, ebit = last.get("revenue"), last.get("net_income"), last.get("ebit")
    out["net_margin_pct"] = ni / rev * 100 if (ni is not None and rev) else None
    cap_emp = (last.get("total_assets") or 0) - (last.get("current_liabilities") or 0)
    out["roce_pct"] = ebit / cap_emp * 100 if (ebit is not None and cap_emp > 0) else None
    eq = last.get("equity")
    out["roe_pct"] = ni / eq * 100 if (ni is not None and eq and eq > 0) else None
    out["debt_to_equity"] = (last.get("debt") or 0) / eq if (eq and eq > 0) else None
    out["ocf_to_profit"] = last.get("ocf") / ni if (last.get("ocf") is not None and ni and ni > 0) else None
    out["pe"] = snap.get("pe")
    out["insider_pct"] = snap.get("insider_pct")

    # Red flags (these REMOVE a tip). Thresholds fixed in DECISIONS.md.
    if ni is not None and ni <= 0:
        out["flags"].append("loss-making in latest year")
    if out["debt_to_equity"] is not None and out["debt_to_equity"] > 2.0:
        out["flags"].append(f"high debt (debt/equity {out['debt_to_equity']:.1f})")
    if eq is not None and eq <= 0:
        out["flags"].append("negative shareholder equity")
    if last.get("ocf") is not None and last["ocf"] < 0:
        out["flags"].append("negative operating cash flow")
    if out["pe"] is not None and out["pe"] > 120:
        out["flags"].append(f"very expensive (P/E {out['pe']:.0f})")
    # Positives (shown as reasons only)
    if out["roce_pct"] and out["roce_pct"] >= 15:
        out["positives"].append(f"ROCE {out['roce_pct']:.0f}%")
    if out["revenue_cagr_pct"] and out["revenue_cagr_pct"] >= 10:
        out["positives"].append(f"revenue growing {out['revenue_cagr_pct']:.0f}%/yr")
    if out["profit_cagr_pct"] and out["profit_cagr_pct"] >= 10:
        out["positives"].append(f"profit growing {out['profit_cagr_pct']:.0f}%/yr")
    if out["debt_to_equity"] is not None and out["debt_to_equity"] < 0.3:
        out["positives"].append("low debt")
    return out


def earnings_dates(symbol, max_age_days=14):
    """Past and next results dates for a stock (Yahoo). Cached; [] on failure."""
    f = EARN / f"{symbol}.csv"
    if f.exists() and (time.time() - f.stat().st_mtime) < max_age_days * 86400:
        d = pd.read_csv(f, parse_dates=["date"])
        return list(d["date"])
    try:
        ed = yf.Ticker(yahoo_ticker(symbol)).get_earnings_dates(limit=60)
        dates = sorted({pd.Timestamp(x).tz_localize(None).normalize() if pd.Timestamp(x).tzinfo
                        else pd.Timestamp(x).normalize() for x in (ed.index if ed is not None else [])})
        # Yahoo stamps US time; Indian results often come after market -> keep calendar date.
        pd.DataFrame({"date": dates}).to_csv(f, index=False)
        time.sleep(0.7)
        return dates
    except Exception as e:
        log.debug("earnings dates failed %s: %s", symbol, e)
        if f.exists():
            return list(pd.read_csv(f, parse_dates=["date"])["date"])
        return []


def results_soon_mask(symbols, dates, days_ahead=7):
    """bool DataFrame: a results date falls within the next `days_ahead` calendar days.
    Uses only CACHED data (call earnings_dates first)."""
    m = pd.DataFrame(False, index=dates, columns=symbols)
    for s in symbols:
        f = EARN / f"{s}.csv"
        if not f.exists():
            continue
        ed = pd.read_csv(f, parse_dates=["date"])["date"]
        for e in ed:
            lo = e - pd.Timedelta(days=days_ahead)
            m.loc[(m.index >= lo) & (m.index <= e), s] = True
    return m


def next_results_date(symbol, today=None):
    today = pd.Timestamp(today or date.today()).normalize()
    fut = [d for d in earnings_dates(symbol) if d >= today]
    return min(fut) if fut else None


def results_day_mask(symbols, dates):
    """bool DataFrame: True on the first trading day ON or AFTER each historical results date (the market's
    reaction day; Indian results often come after market hours). Uses cached earnings dates only."""
    m = pd.DataFrame(False, index=dates, columns=symbols)
    idx = pd.DatetimeIndex(dates)
    for s in symbols:
        f = EARN / f"{s}.csv"
        if not f.exists():
            continue
        for e in pd.read_csv(f, parse_dates=["date"])["date"]:
            # Yahoo stamps US time, so the Indian calendar date is the date shown: react on that day or the next
            pos = idx.searchsorted(e.normalize())
            if pos < len(idx):
                m.iat[pos, m.columns.get_loc(s)] = True
                if pos + 1 < len(idx):
                    m.iat[pos + 1, m.columns.get_loc(s)] = True
    return m


EPS = EVENTS / "eps"
EPS.mkdir(parents=True, exist_ok=True)


def eps_history(symbol, max_age_days=30):
    """Quarterly REPORTED EPS with the date it was announced (point-in-time; Yahoo earnings calendar). For CANSLIM."""
    f = EPS / f"{symbol}.csv"
    if f.exists() and (time.time() - f.stat().st_mtime) < max_age_days * 86400:
        return pd.read_csv(f, parse_dates=["date"])
    try:
        ed = yf.Ticker(yahoo_ticker(symbol)).get_earnings_dates(limit=60)
        df = pd.DataFrame({"date": [pd.Timestamp(x).tz_localize(None).normalize() if pd.Timestamp(x).tzinfo
                                    else pd.Timestamp(x).normalize() for x in ed.index],
                           "eps": pd.to_numeric(ed["Reported EPS"], errors="coerce").values}).dropna()
        df = df.sort_values("date")
        df.to_csv(f, index=False)
        time.sleep(0.7)
        return df
    except Exception as e:
        log.debug("eps history failed %s: %s", symbol, e)
        return pd.read_csv(f, parse_dates=["date"]) if f.exists() else pd.DataFrame(columns=["date", "eps"])


def eps_growth_panel(symbols, dates):
    """Point-in-time quarterly EPS growth vs the same quarter a year earlier (latest report known on each date)."""
    idx = pd.DatetimeIndex(dates)
    out = pd.DataFrame(index=idx, columns=symbols, dtype=float)
    for s in symbols:
        f = EPS / f"{s}.csv"
        if not f.exists():
            continue
        e = pd.read_csv(f, parse_dates=["date"]).sort_values("date")
        if len(e) < 5:
            continue
        # same quarter a year earlier = the report 320-410 days before (Yahoo history has gaps, so no shift(4))
        prev = []
        for d0 in e["date"]:
            m = e[(e["date"] <= d0 - pd.Timedelta(days=320)) & (e["date"] >= d0 - pd.Timedelta(days=410))]
            prev.append(m["eps"].iloc[-1] if len(m) else float("nan"))
        e["prev_year"] = prev
        e["growth"] = (e["eps"] - e["prev_year"]) / e["prev_year"].abs()
        e.loc[e["prev_year"] <= 0, "growth"] = float("nan")
        g = e.set_index(e["date"] + pd.Timedelta(days=1))["growth"]      # known from the day after the report
        g = g[~g.index.duplicated(keep="last")]
        out[s] = g.reindex(g.index.union(idx)).ffill().reindex(idx).values
    return out
