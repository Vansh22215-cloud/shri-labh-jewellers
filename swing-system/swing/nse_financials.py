"""Company financials from the companies' own NSE filings (owner 20 Nov: "move company financials to NSE/BSE filings").
Replaces Yahoo's statements. Free, public NSE data, read-only:
  - annual results list  /api/corporates-financial-results?period=Annual  (every year since ~2005, real filing time)
  - each annual filing's XBRL file (the official machine-readable copy): income statement, balance sheet, cash flow
  - promoter holding     /api/corporate-share-holdings-master (latest shareholding pattern)
Consolidated figures when the company files them, else standalone (marked). A year is "known" from its REAL filing
date (point-in-time; no assumed delays). Fields a filing does not have stay None - never filled from another source.
Price-based ratios (P/E, P/B, market value) use the latest Kite close only (strict Kite; none if Kite has none).
Parsed filings are cached forever by NSE's filing number (data/fundamentals/nse_xbrl/), so each is read once."""
import json
import re
import time
import xml.etree.ElementTree as ET

import pandas as pd
import requests

from .config import FUND, get_logger

log = get_logger()
XCACHE = FUND / "nse_xbrl"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
      "Accept": "application/json, text/plain, */*", "Accept-Language": "en-US,en;q=0.9",
      "Referer": "https://www.nseindia.com/companies-listing/corporate-filings-financial-results"}
BASE = "https://www.nseindia.com"
MAX_YEARS = 12
# our field -> XBRL element names tried in order (Ind-AS taxonomy; banks/NBFCs use some different names)
DURATION = {"revenue": ("RevenueFromOperations", "Income", "TotalIncome", "InterestEarned"),
            "net_income": ("ProfitOrLossAttributableToOwnersOfParent", "ProfitLossAttributableToOwnersOfParent",
                           "ProfitLossForPeriod", "ProfitLossForThePeriod"),
            "pbt": ("ProfitBeforeTax", "ProfitLossBeforeTax"),
            "interest": ("FinanceCosts", "InterestExpended"),
            "ocf": ("CashFlowsFromUsedInOperatingActivities", "NetCashFlowsFromUsedInOperatingActivities"),
            "capex": ("PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities",
                      "PurchaseOfPropertyPlantAndEquipment"),
            "eps": ("BasicEarningsLossPerShareFromContinuingAndDiscontinuedOperations",
                    "BasicEarningsLossPerShareFromContinuingOperations")}
INSTANT = {"total_assets": ("Assets",), "current_assets": ("CurrentAssets",), "current_liabilities": ("CurrentLiabilities",),
           "equity": ("EquityAttributableToOwnersOfParent", "Equity"),
           "debt_noncurrent": ("BorrowingsNoncurrent", "NonCurrentBorrowings"),
           "debt_current": ("BorrowingsCurrent", "CurrentBorrowings"), "borrowings": ("Borrowings",),
           "paid_up": ("PaidUpValueOfEquityShareCapital", "EquityShareCapital"), "face_value": ("FaceValueOfEquityShareCapital",)}


def session():
    s = requests.Session()
    try:
        s.get(BASE + "/companies-listing/corporate-filings-financial-results", headers=UA, timeout=20)
    except Exception:
        pass
    return s


def _get_json(s, path, timeout=40):
    for a in range(3):
        try:
            r = s.get(BASE + path, headers=UA, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except Exception:
            if a == 2:
                raise
            time.sleep(2 * (a + 1))


def _d(x):
    try:
        return pd.Timestamp(x)
    except Exception:
        return None


def parse_xbrl(text, period_from, period_to):
    """-> {field: value} for the full-year period (duration items) and the year-end date (balance-sheet items),
    ignoring segment/dimension breakdowns."""
    root = ET.fromstring(text.encode() if isinstance(text, str) else text)
    loc = lambda t: t.rsplit("}", 1)[-1]
    # the filing's own "start/end of reporting period" facts are trusted over the context dates (older NSE XBRL
    # files label the full-year context with the quarter's dates)
    own = {}
    for e in root:
        if loc(e.tag) in ("DateOfStartOfReportingPeriod", "DateOfEndOfReportingPeriod") and e.get("contextRef"):
            own.setdefault(e.get("contextRef"), {})[loc(e.tag)] = _d((e.text or "").strip())
    dur, inst = set(), set()
    for c in root.iter():
        if loc(c.tag) != "context":
            continue
        if any(loc(e.tag) in ("segment", "scenario") for e in c.iter()):
            continue                                       # a breakdown (segment, member), not the company total
        vals = {loc(e.tag): (e.text or "").strip() for e in c.iter()}
        o = own.get(c.get("id"), {})
        start = o.get("DateOfStartOfReportingPeriod") or _d(vals.get("startDate"))
        end = o.get("DateOfEndOfReportingPeriod") or _d(vals.get("endDate"))
        if "instant" in vals and _d(vals["instant"]) == period_to:
            inst.add(c.get("id"))
        elif start == period_from and end == period_to:
            dur.add(c.get("id"))
    defined = {c.get("id") for c in root.iter() if loc(c.tag) == "context"}
    for ref, o in own.items():                     # some older NSE files use contexts they never define
        if ref not in defined and o.get("DateOfStartOfReportingPeriod") == period_from \
                and o.get("DateOfEndOfReportingPeriod") == period_to:
            dur.add(ref)
    if "OneI" not in defined and dur:
        inst.add("OneI")                           # NSE's own name for the year-end balance-sheet date
    facts = {}
    for e in root:
        ref = e.get("contextRef")
        if ref and (ref in dur or ref in inst):
            try:
                facts.setdefault((loc(e.tag), "D" if ref in dur else "I"), float(e.text))
            except Exception:
                pass
    out = {}
    for field, names in DURATION.items():
        out[field] = next((facts[(n, "D")] for n in names if (n, "D") in facts), None)
    for field, names in INSTANT.items():
        out[field] = next((facts[(n, "I")] for n in names if (n, "I") in facts), None)
    for field in ("paid_up", "face_value"):         # filed with the period, not the balance-sheet date
        if out[field] is None:
            out[field] = next((facts[(n, "D")] for n in INSTANT[field] if (n, "D") in facts), None)
    return out


def _row(x, fy_from, fy_to, filed, consolidated):
    """Our yearly row (same keys as before, so the quality screen and company research read it unchanged)."""
    parts = [x.get("debt_noncurrent"), x.get("debt_current")]
    debt = sum(p for p in parts if p is not None) if any(p is not None for p in parts) else x.get("borrowings")
    shares = x["paid_up"] / x["face_value"] if x.get("paid_up") and x.get("face_value") else None
    ebit = x["pbt"] + (x.get("interest") or 0) if x.get("pbt") is not None else None
    capex = -abs(x["capex"]) if x.get("capex") is not None else None      # cash going out (negative, as before)
    return {"published_assumed": str(filed.date()), "published": str(filed.date()), "period_from": str(fy_from.date()),
            "revenue": x.get("revenue"), "net_income": x.get("net_income"), "ebit": ebit,
            "total_assets": x.get("total_assets"), "current_liabilities": x.get("current_liabilities"),
            "equity": x.get("equity"), "debt": debt, "ocf": x.get("ocf"), "capex": capex, "interest": x.get("interest"),
            "gross_profit": None, "current_assets": x.get("current_assets"), "shares": shares, "eps": x.get("eps"),
            "consolidated": consolidated, "source": "NSE filing"}


def annual(symbol, s=None, max_years=MAX_YEARS):
    """{period end 'YYYY-MM-DD': row} from the company's annual XBRL filings, newest max_years."""
    s = s or session()
    lst = list(_get_json(s, f"/api/corporates-financial-results?index=equities&symbol={symbol}&period=Annual") or [])
    try:                    # from 2025 NSE takes results as "integrated filings": the year-end quarter's filing has the
        j = _get_json(s, f"/api/integrated-filing-results?index=equities&symbol={symbol}&page=1&size=200")    # full year + balance sheet
        for f in (j or {}).get("data", []):
            qe = _d(f.get("qe_Date"))
            if "Financials" in str(f.get("type")) and qe is not None and f.get("xbrl"):
                lst.append({"xbrl": f["xbrl"], "toDate": str(qe.date()),
                            "fromDate": str((qe - pd.DateOffset(years=1) + pd.Timedelta(days=1)).date()),
                            "consolidated": "Consolidated" if str(f.get("consolidated")).lower() == "consolidated" else "Standalone",
                            "broadCastDate": f.get("broadcast_Date"), "seqNumber": "if" + str(f.get("seq_Id"))})
    except Exception as e:
        log.info("NSE integrated filings %s: %s", symbol, type(e).__name__)
    best = {}
    for f in lst:
        to, fr = _d(f.get("toDate")), _d(f.get("fromDate"))
        if not str(f.get("xbrl", "")).endswith(".xml") or to is None or fr is None or (to - fr).days < 300:
            continue
        cons = str(f.get("consolidated", "")).lower() == "consolidated"
        filed = _d(str(f.get("broadCastDate") or f.get("filingDate") or "")[:11]) or (to + pd.Timedelta(days=60))
        k = str(to.date())
        old = best.get(k)
        # consolidated first; for the same kind the first-ever filing (point-in-time), later revisions noted
        if old is None or (cons and not old[1]) or (cons == old[1] and filed < old[2]):
            best[k] = (f, cons, filed, fr, to)
    out = {}
    for k in sorted(best)[-max_years:]:
        f, cons, filed, fr, to = best[k]
        XCACHE.mkdir(parents=True, exist_ok=True)
        cf = XCACHE / f"{f.get('seqNumber') or re.sub(r'[^0-9A-Za-z]', '_', f['xbrl'][-40:])}.json"
        try:
            x = json.loads(cf.read_text())
        except Exception:
            try:
                r = s.get(f["xbrl"], headers=UA, timeout=60)
                r.raise_for_status()
                x = parse_xbrl(r.text, fr, to)
                cf.write_text(json.dumps(x))
                time.sleep(0.4)
            except Exception as e:
                log.info("NSE XBRL %s %s: %s", symbol, k, type(e).__name__)
                continue
        if x.get("revenue") is not None or x.get("net_income") is not None:   # a full-year result (not a half-year)
            out[k] = _row(x, fr, to, filed, "consolidated" if cons else "standalone")
    return out


def promoter_pct(symbol, s=None):
    """Latest promoter + promoter-group holding (fraction, e.g. 0.7177) and its date, from NSE shareholding filings."""
    s = s or session()
    try:
        h = _get_json(s, f"/api/corporate-share-holdings-master?index=equities&symbol={symbol}") or []
        h = sorted(h, key=lambda r: _d(r.get("date")) or pd.Timestamp(0))
        r = h[-1]
        return float(r["pr_and_prgrp"]) / 100, str(_d(r["date"]).date())
    except Exception:
        return None, None


def industry(symbol):
    try:
        from .data_nse import nifty500_list
        L = nifty500_list()
        row = L[L["Symbol"] == symbol]
        return (str(row["Industry"].iloc[0]), str(row["Company Name"].iloc[0])) if len(row) else (None, None)
    except Exception:
        return None, None


def kite_close(symbol):
    try:
        from .data_prices import load
        d = load(symbol)
        return float(d["close"].dropna().iloc[-1]) if d is not None and len(d) else None
    except Exception:
        return None


def snapshot(symbol, s=None):
    """The fundamentals snapshot in the format the system already uses (v3 = NSE filings)."""
    from datetime import date
    s = s or session()
    snap = {"symbol": symbol, "downloaded": str(date.today()), "ok": False, "v": 3,
            "source": "NSE filings (annual XBRL + shareholding); prices: Kite"}
    years = annual(symbol, s)
    snap["annual"] = years
    snap["ok"] = bool(years)
    ind, name = industry(symbol)
    try:
        lst_name = None
        if not name:
            lst = _get_json(s, f"/api/corporates-financial-results?index=equities&symbol={symbol}&period=Annual") or []
            lst_name = lst[0].get("companyName") if lst else None
        name = name or lst_name
    except Exception:
        pass
    pp, pdate = promoter_pct(symbol, s)
    last = years[max(years)] if years else {}
    px = kite_close(symbol)
    mcap = px * last["shares"] if px and last.get("shares") else None
    ni, eq = last.get("net_income"), last.get("equity")
    snap.update({"name": name, "sector": ind, "industry": ind, "summary": "",
                 "insider_pct": pp, "promoter_pct": pp, "promoter_asof": pdate, "market_cap": mcap,
                 "pe": mcap / ni if (mcap and ni and ni > 0) else None,
                 "pb": mcap / eq if (mcap and eq and eq > 0) else None,
                 "float_shares": last["shares"] * (1 - pp) if (last.get("shares") and pp is not None) else None,
                 "dividend_yield": None, "info_ok": pp is not None,
                 "roe_info": None, "de_info": None, "margin_info": None, "rev_growth_info": None,
                 "eps_growth_info": None, "current_ratio_info": None})
    return snap
