"""NSE company filings for the stocks the owner follows (adapted from 'trader-news', 'trader-analyst', 'trader-pelosi'):

  * company announcements (results, orders won, acquisitions, dividends, rating changes, management exits, takeover
    and insider disclosures, regulator actions ...) - only the categories that can move a price
  * the results calendar (board meetings for financial results)
  * insider / promoter trades (SEBI PIT disclosures; NSE's feed, with the takeover announcements as a fallback) -
    India's version of the US 'Congress trades' tracker. Every record is also kept in the lifelong archive, so
    "buy after promoter buying" can be tested once enough history has been collected (it can't be back-tested
    today: the free feed has no long history)
  * a quarterly results summary: sales, profit and margin vs the last quarter and the same quarter last year

Followed stocks = the owner's trades + open/pending system tips + today's scan signals + forwarded stock tips.
Free public NSE data; polite (cached, one call per list).
"""
import html
import json
import re
from datetime import datetime, timedelta

import pandas as pd
import requests

from .config import DATA, get_logger

log = get_logger()
E = html.escape
CACHE = DATA / "nse_filings"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
      "Accept": "application/json, text/plain, */*", "Accept-Language": "en-US,en;q=0.9",
      "Referer": "https://www.nseindia.com/companies-listing/corporate-filings-announcements"}
IMPORTANT = {   # announcement category -> (icon, plain words)
    "Outcome of Board Meeting": ("📊", "board meeting outcome"), "Integrated Filing- Financial": ("📊", "financial results"),
    "Financial Results": ("📊", "financial results"), "Bagging/Receiving of orders/contracts": ("📦", "won an order / contract"),
    "Acquisition": ("🤝", "acquisition"), "Dividend": ("💰", "dividend"), "Credit Rating": ("🏷", "credit rating"),
    "Resignation of Director/KMP/SMP": ("🚪", "director / key manager resigned"), "Resignation": ("🚪", "resignation"),
    "Change in Management": ("🔁", "management change"), "Change in Auditors": ("⚠️", "auditor changed"),
    "Disclosure under SEBI Takeover Regulations": ("🏦", "large shareholder / promoter stake change"),
    "Action(s) taken or orders passed": ("⚖️", "regulator / court action"),
    "Action(s) initiated or orders passed": ("⚖️", "regulator / court action"),
    "Pendency of Litigation(s)/dispute(s) or the outcome impacting the Company": ("⚖️", "litigation"),
    "Corporate Insolvency Resolution Process": ("🛑", "insolvency process"), "Spurt in Volume": ("📢", "volume spurt query"),
    "Allotment of Securities": ("🧾", "new shares allotted"), "Buyback": ("🔙", "buyback"), "Bonus": ("🎁", "bonus issue"),
    "Record Date": ("📅", "record date"), "Capacity addition": ("🏭", "capacity addition"),
    "Monthly Business Updates": ("📈", "monthly business update"), "Agreements": ("✍️", "agreement"),
}


def _session():
    s = requests.Session()
    try:
        s.get("https://www.nseindia.com/companies-listing/corporate-filings-insider-trading", headers=UA, timeout=20)
    except Exception:
        pass
    return s


def _get_json(s, url, timeout=60):
    r = s.get(url, headers=UA, timeout=timeout)
    r.raise_for_status()
    return r.json()


def announcements(days=2, s=None):
    """Important announcements of the last `days` days (all NSE companies), newest first, cached 15 minutes."""
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / "announcements.json"
    if f.exists() and (datetime.now().timestamp() - f.stat().st_mtime) < 900:
        try:
            return json.loads(f.read_text())
        except Exception:
            pass
    to, fr = datetime.now(), datetime.now() - timedelta(days=days)
    try:
        d = _get_json(s or _session(), "https://www.nseindia.com/api/corporate-announcements?index=equities"
                                       f"&from_date={fr:%d-%m-%Y}&to_date={to:%d-%m-%Y}")
    except Exception as e:
        log.warning("NSE announcements failed: %s", type(e).__name__)
        return []
    out = []
    for a in d if isinstance(d, list) else []:
        cat = str(a.get("desc", ""))
        if cat not in IMPORTANT:
            continue
        out.append({"symbol": a.get("symbol"), "time": a.get("sort_date") or a.get("an_dt"), "category": cat,
                    "text": re.sub(r"\s+", " ", str(a.get("attchmntText") or ""))[:300],
                    "pdf": a.get("attchmntFile")})
    out.sort(key=lambda x: str(x["time"]), reverse=True)
    f.write_text(json.dumps(out))
    return out


def results_calendar(s=None):
    """Upcoming board meetings for financial results: [{'symbol','date','purpose'}]."""
    f = CACHE / "calendar.json"
    CACHE.mkdir(parents=True, exist_ok=True)
    if f.exists() and (datetime.now().timestamp() - f.stat().st_mtime) < 6 * 3600:
        return json.loads(f.read_text())
    try:
        d = _get_json(s or _session(), "https://www.nseindia.com/api/event-calendar?index=equities")
        out = [{"symbol": x.get("symbol"), "date": x.get("date"), "purpose": x.get("purpose")} for x in d
               if "result" in str(x.get("purpose", "")).lower()]
        f.write_text(json.dumps(out))
        return out
    except Exception as e:
        log.warning("NSE results calendar failed: %s", type(e).__name__)
        return []


def insider(days=7, s=None):
    """Insider / promoter trades (SEBI PIT) of the last `days` days: [{'symbol','who','role','action','shares',
    'value_cr','date','mode'}]. Falls back to takeover-regulation announcements when NSE's feed is empty."""
    to, fr = datetime.now(), datetime.now() - timedelta(days=days)
    rows = []
    try:
        d = _get_json(s or _session(), "https://www.nseindia.com/api/corporates-pit?index=equities"
                                       f"&from_date={fr:%d-%m-%Y}&to_date={to:%d-%m-%Y}")
        for x in (d.get("data", []) if isinstance(d, dict) else []):
            try:
                val = float(str(x.get("secVal") or 0).replace(",", "")) / 1e7
            except ValueError:
                val = None
            rows.append({"symbol": x.get("symbol"), "who": x.get("acqName"), "role": x.get("personCategory"),
                         "action": x.get("tdpTransactionType") or x.get("acqMode"), "shares": x.get("secAcq"),
                         "value_cr": val, "date": x.get("date") or x.get("acqfromDt"), "mode": x.get("acqMode")})
    except Exception as e:
        log.warning("NSE insider feed failed: %s", type(e).__name__)
    if not rows:   # fallback: takeover disclosures (large shareholder / promoter stake changes)
        for a in announcements(days=days, s=s):
            if a["category"] == "Disclosure under SEBI Takeover Regulations":
                rows.append({"symbol": a["symbol"], "who": None, "role": "large shareholder / promoter",
                             "action": "stake change (see filing)", "shares": None, "value_cr": None,
                             "date": a["time"], "mode": a["text"][:120]})
    try:   # keep every record for future research ("buy after promoter buying")
        from . import archive
        if rows:
            archive.write_day("insider", datetime.now().date(),
                              pd.DataFrame(rows).astype(str).assign(seen=str(datetime.now().date())))
    except Exception:
        pass
    return rows


def followed():
    """Stocks the owner follows (trades, tips, signals, forwarded stock tips)."""
    from .tip_status import symbols_needed
    from . import journal
    syms = set(symbols_needed())
    try:
        syms |= set(journal.load_my_trades()["symbol"])
    except Exception:
        pass
    return sorted(s for s in syms if s and s.isupper())


def results_summary(sym):
    """'Sales +12% vs last year, profit +18%, margin 21% -> 23%' from the quarterly statements (Yahoo)."""
    try:
        import yfinance as yf
        q = yf.Ticker(f"{sym}.NS").quarterly_income_stmt
        if q is None or q.empty or q.shape[1] < 2:
            return None
        q = q.T.sort_index()
        rev = q.get("Total Revenue")
        ni = q.get("Net Income")
        if rev is None or ni is None:
            return None
        last = q.index[-1]
        parts = [f"quarter to {pd.Timestamp(last):%b %Y}: sales ₹{rev.iloc[-1] / 1e7:,.0f} cr, profit ₹{ni.iloc[-1] / 1e7:,.0f} cr"]
        if len(q) >= 2 and rev.iloc[-2]:
            parts.append(f"vs last quarter sales {(rev.iloc[-1] / rev.iloc[-2] - 1) * 100:+.0f}%, profit "
                         f"{(ni.iloc[-1] / ni.iloc[-2] - 1) * 100:+.0f}%" if ni.iloc[-2] else "")
        if len(q) >= 5 and rev.iloc[-5]:
            parts.append(f"vs a year ago sales {(rev.iloc[-1] / rev.iloc[-5] - 1) * 100:+.0f}%, profit "
                         f"{(ni.iloc[-1] / ni.iloc[-5] - 1) * 100:+.0f}%" if ni.iloc[-5] else "")
            m_now, m_then = ni.iloc[-1] / rev.iloc[-1] * 100, ni.iloc[-5] / rev.iloc[-5] * 100
            parts.append(f"profit margin {m_then:.0f}% -> {m_now:.0f}%")
        return "; ".join(p for p in parts if p) + " (Yahoo statements; may lag the filing by a few days)."
    except Exception as e:
        log.warning("results summary %s failed: %s", sym, type(e).__name__)
        return None


def _ann_line(a):
    icon, words = IMPORTANT.get(a["category"], ("📢", a["category"].lower()))
    t = pd.Timestamp(a["time"]).strftime("%d %b %I:%M %p") if a.get("time") else ""
    txt = re.sub(r"^.*?has informed the Exchange (about|regarding) ", "", a["text"]).strip()
    return f"{icon} <b>{E(a['symbol'])}</b> - {E(words)} <i>({E(t)})</i>" + (f"\n   {E(txt[:180])}" if txt else "")


def morning_brief(today=None, syms=None):
    """Owner's 9:00 am brief for followed stocks: filings since yesterday, results due, insider trades. None if quiet."""
    today = pd.Timestamp(today or pd.Timestamp.now(tz="Asia/Kolkata").date())
    syms = set(syms if syms is not None else followed())
    if not syms:
        return None
    s = _session()
    ann = [a for a in announcements(days=2, s=s) if a["symbol"] in syms]
    cal = [c for c in results_calendar(s=s) if c["symbol"] in syms]
    soon = [c for c in cal if 0 <= (pd.Timestamp(c["date"]) - today).days <= 7]
    ins = [i for i in insider(days=7, s=s) if i["symbol"] in syms]
    if not (ann or soon or ins):
        return None
    L = [f"🌅 <b>MORNING BRIEF</b> · {today:%a %d %b} · for your {len(syms)} followed stocks"]
    if soon:
        L += ["", "📅 <b>Results coming</b> (big moves likely - a stop can gap)"] + [
            f"• <b>{E(c['symbol'])}</b> - {E(pd.Timestamp(c['date']).strftime('%a %d %b'))}" +
            (" <b>TODAY</b>" if pd.Timestamp(c["date"]) == today else "") for c in soon]
    if ann:
        L += ["", "📢 <b>Company filings</b>"] + [_ann_line(a) for a in ann[:12]]
        res = sorted({a["symbol"] for a in ann if a["category"] in ("Outcome of Board Meeting", "Integrated Filing- Financial",
                                                                    "Financial Results")})
        for sy in res[:4]:
            rs = results_summary(sy)
            if rs:
                L.append(f"📊 <b>{E(sy)} results</b>: {E(rs)}")
    if ins:
        L += ["", "🏦 <b>Insider / promoter trades</b> (last 7 days)"]
        for i in ins[:8]:
            val = f" ₹{i['value_cr']:,.1f} cr" if i.get("value_cr") else ""
            who = f"{i['who']} ({i['role']})" if i.get("who") else i.get("role") or "insider"
            L.append(f"• <b>{E(i['symbol'])}</b>: {E(who)} - {E(str(i.get('action') or ''))}{E(val)}")
        L.append("<i>Promoters buying is often read as confidence, selling can be for many reasons - it's a clue, "
                 "not a signal (not tested yet).</i>")
    L.append("\n<i>Research, not advice.</i>")
    return "\n".join(L)


def new_filings(seen, syms=None):
    """Important filings for followed stocks not yet seen (for during-market alerts). Returns (lines, new seen)."""
    syms = set(syms if syms is not None else followed())
    ann = [a for a in announcements(days=1) if a["symbol"] in syms]
    fresh = [a for a in ann if f"{a['symbol']}|{a['time']}|{a['category']}" not in seen]
    for a in fresh:
        seen.add(f"{a['symbol']}|{a['time']}|{a['category']}")
    return [_ann_line(a) for a in fresh], seen
