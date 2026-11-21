"""COMPANY OF THE QUARTER (owner 20 Nov: "I want company of the day, but one company once a quarter").

One company a calendar quarter - research, not a trade tip. Sent at 6:30 pm on the first weekday of each quarter
(Jan, Apr, Jul, Oct); the very first one goes out as soon as enough companies have been read.
How it is chosen:
  - every NSE stock Kite lists that trades at least ₹1 crore a day on average and costs ₹20 or more (Kite daily
    candles) - tiny illiquid stocks are left out;
  - each company's own annual results from its NSE filings (company_filings.py, real filing dates, consolidated
    when filed), read again every ~80 days, ~150 companies a night outside market hours;
  - score 0-100:  Quality 25 (ROCE, ROE, net margin) · Growth 20 (sales and profit growth a year) ·
    Financial health 20 (debt/equity, interest cover, current ratio) · Cash 15 (operating cash vs profit, free
    cash flow) · Valuation 10 (P/E and P/B from the Kite price) · Piotroski-style health checks 10;
  - red flags remove a company: a loss in the latest year, negative equity, negative operating cash flow,
    debt/equity above 2, fewer than 3 years of results;
  - no company is repeated within 4 quarters.
Every pick is recorded (results/company_picks.csv) with its price, and the next quarter's message says how the
last pick did - so we learn whether the method works. Prices: Kite only."""
import json
import time

import numpy as np
import pandas as pd

from . import candles
from .config import COMPANY, RESULTS, get_logger, load_settings

log = get_logger()
PICKS = RESULTS / "company_picks.csv"
REFRESH_DAYS = 80
MAX_MINUTES = 10                 # the nightly filings read never blocks the other jobs for longer
MIN_TURNOVER_CR, MIN_PRICE = 1.0, 20.0


def quarter(t=None):
    t = pd.Timestamp(t or pd.Timestamp.now())
    return f"{t.year}-Q{(t.month - 1) // 3 + 1}"


def eligible():
    """Stocks with Kite daily candles that trade >= ₹1 crore a day (last 20 days) at >= ₹20. -> {sym: last close}."""
    out = {}
    for sym in candles.symbols("day"):
        if sym in candles.INDICES:
            continue
        d = candles.load(sym, "day")
        if d is None or len(d) < 20:
            continue
        t = d.tail(20)
        turnover = float((t["close"] * t["volume"]).mean()) / 1e7
        px = float(t["close"].iloc[-1])
        if turnover >= MIN_TURNOVER_CR and px >= MIN_PRICE and t.index[-1] >= pd.Timestamp.now().normalize() - pd.Timedelta(days=10):
            out[sym] = px
    return out


def _file(sym):
    return COMPANY / f"{sym}.json"


def refresh(syms, n=150):
    """Read the NSE filings of the n companies whose copy is oldest (or missing)."""
    from . import company_filings as cf
    age = lambda s: _file(s).stat().st_mtime if _file(s).exists() else 0
    todo = [s for s in sorted(syms, key=age) if time.time() - age(s) > REFRESH_DAYS * 86400][:n]
    if not todo:
        return 0
    sess = cf.session()
    ok, fails, t0 = 0, 0, time.time()
    for s in todo:
        if time.time() - t0 > MAX_MINUTES * 60 or fails >= 8:   # NSE slow or blocking: stop, try again tomorrow
            log.info("Company filings: stopped (%s)", "time limit" if fails < 8 else "NSE not answering")
            break
        try:
            years = cf.annual(s, sess)
            pp, pdate = cf.promoter_pct(s, sess)
            _file(s).write_text(json.dumps({"symbol": s, "read": str(pd.Timestamp.now().date()), "years": years,
                                            "promoter_pct": pp, "promoter_asof": pdate}))
            ok += bool(years)
            fails = 0
        except Exception as e:
            fails += 1
            log.info("Company filings %s: %s", s, type(e).__name__)
    log.info("Company of the quarter: filings read for %d of %d companies", ok, len(todo))
    return ok


def _cagr(a, b, n):
    return ((b / a) ** (1 / n) - 1) * 100 if (a and b and a > 0 and b > 0 and n > 0) else None


def _pts(v, good, ok, top):
    """0..top points: >= good gets all, >= ok half, else 0."""
    if v is None or v != v:
        return 0.0
    return top if v >= good else top / 2 if v >= ok else 0.0


def score(rec, price):
    ys = [rec["years"][k] for k in sorted(rec.get("years") or {}) if (rec["years"][k] or {}).get("revenue")]
    if len(ys) < 3:
        return None
    last, prev, first = ys[-1], ys[-2], ys[0]
    n = len(ys) - 1
    rev, ni, ebit, eq = last.get("revenue"), last.get("net_income"), last.get("ebit"), last.get("equity")
    ta, cl, ca = last.get("total_assets"), last.get("current_liabilities"), last.get("current_assets")
    cap_emp = (ta or 0) - (cl or 0)
    r = {"symbol": rec["symbol"], "years": len(ys), "fy": sorted(rec["years"])[-1][:4]}
    r["roce"] = ebit / cap_emp * 100 if (ebit is not None and cap_emp > 0) else None
    r["roe"] = ni / eq * 100 if (ni is not None and eq and eq > 0) else None
    r["margin"] = ni / rev * 100 if (ni is not None and rev) else None
    r["rev_growth"] = _cagr(first.get("revenue"), rev, n)
    r["profit_growth"] = _cagr(first.get("net_income"), ni, n)
    r["de"] = (last.get("debt") or 0) / eq if (eq and eq > 0) else None
    r["int_cover"] = ebit / last["interest"] if (ebit and last.get("interest")) else None
    r["current_ratio"] = ca / cl if (ca and cl) else None
    ocf, capex = last.get("ocf"), last.get("capex")
    r["ocf_to_profit"] = ocf / ni if (ocf is not None and ni and ni > 0) else None
    r["fcf_cr"] = (ocf + capex) / 1e7 if (ocf is not None and capex is not None) else None
    mcap = price * last["shares"] if last.get("shares") else None
    r["pe"] = mcap / ni if (mcap and ni and ni > 0) else None
    r["pb"] = mcap / eq if (mcap and eq and eq > 0) else None
    r["mcap_cr"] = mcap / 1e7 if mcap else None
    r["sales_cr"], r["profit_cr"] = (rev or 0) / 1e7, (ni or 0) / 1e7
    r["promoter_pct"] = rec.get("promoter_pct") * 100 if rec.get("promoter_pct") is not None else None
    flags = []
    if ni is not None and ni <= 0:
        flags.append("loss in the latest year")
    if eq is not None and eq <= 0:
        flags.append("negative equity")
    if ocf is not None and ocf < 0:
        flags.append("negative operating cash flow")
    if r["de"] is not None and r["de"] > 2:
        flags.append("debt/equity above 2")
    r["flags"] = flags
    # Piotroski-style checks (the ones company filings allow)
    roa = lambda y: y["net_income"] / y["total_assets"] if (y.get("net_income") is not None and y.get("total_assets")) else None
    lev = lambda y: (y.get("debt") or 0) / y["total_assets"] if y.get("total_assets") else None
    cur = lambda y: y["current_assets"] / y["current_liabilities"] if (y.get("current_assets") and y.get("current_liabilities")) else None
    turn = lambda y: y["revenue"] / y["total_assets"] if (y.get("revenue") and y.get("total_assets")) else None
    gt = lambda a, b: a is not None and b is not None and a > b
    checks = [ni is not None and ni > 0, ocf is not None and ocf > 0, gt(roa(last), roa(prev)),
              ocf is not None and ni is not None and ocf > ni, gt(lev(prev), lev(last)), gt(cur(last), cur(prev)),
              last.get("shares") is not None and prev.get("shares") is not None and last["shares"] <= prev["shares"] * 1.01,
              gt(turn(last), turn(prev))]
    r["fscore"] = int(sum(bool(c) for c in checks))
    parts = {"Quality": _pts(r["roce"], 20, 12, 10) + _pts(r["roe"], 18, 12, 10) + _pts(r["margin"], 12, 6, 5),
             "Growth": _pts(r["rev_growth"], 15, 8, 10) + _pts(r["profit_growth"], 15, 8, 10),
             "Financial health": (8.0 if r["de"] is not None and r["de"] < 0.3 else 4.0 if r["de"] is not None and r["de"] < 1 else 0.0)
                                 + _pts(r["int_cover"], 8, 3, 6) + _pts(r["current_ratio"], 1.5, 1.1, 6),
             "Cash": _pts(r["ocf_to_profit"], 1.0, 0.7, 10) + (5.0 if r["fcf_cr"] and r["fcf_cr"] > 0 else 0.0),
             "Valuation": (5.0 if r["pe"] and r["pe"] < 25 else 2.5 if r["pe"] and r["pe"] < 45 else 0.0)
                          + (5.0 if r["pb"] and r["pb"] < 4 else 2.5 if r["pb"] and r["pb"] < 8 else 0.0),
             "Health checks": r["fscore"] / 8 * 10}
    r["parts"] = {k: round(v, 1) for k, v in parts.items()}
    r["score"] = round(sum(parts.values()), 1)
    return r


def picks():
    try:
        return pd.read_csv(PICKS)
    except Exception:
        return pd.DataFrame(columns=["quarter", "date", "symbol", "score", "price"])


def choose(prices):
    P = picks()
    recent = set(P.tail(4)["symbol"]) if len(P) else set()
    best = None
    for s, px in prices.items():
        f = _file(s)
        if not f.exists() or s in recent:
            continue
        try:
            r = score(json.loads(f.read_text()), px)
        except Exception:
            continue
        if r and not r["flags"] and (best is None or r["score"] > best["score"]):
            best = r
    return best


def fmt(v, suf="", d=0):
    return "-" if v is None or v != v else f"{v:,.{d}f}{suf}"


def message(r, price, q):
    from .kite import instruments
    try:
        ins = instruments()
        name = str(ins.loc[ins["tradingsymbol"] == r["symbol"], "name"].iloc[0]).title()
    except Exception:
        name = r["symbol"]
    d = candles.load(r["symbol"], "day")
    hi52 = float(d["high"].tail(250).max()) if d is not None and len(d) else None
    lo52 = float(d["low"].tail(250).min()) if d is not None and len(d) else None
    L = [f"🏢 <b>COMPANY OF THE QUARTER</b> ({q})", f"<b>{name} ({r['symbol']})</b> - score {r['score']:.0f}/100", "",
         f"Price ₹{price:,.2f} · 52-week ₹{fmt(lo52, d=0)}-₹{fmt(hi52, d=0)} · value ₹{fmt(r['mcap_cr'])} cr",
         f"Sales ₹{fmt(r['sales_cr'])} cr, profit ₹{fmt(r['profit_cr'])} cr (FY{r['fy']}, {r['years']} years of NSE filings)",
         f"Quality: ROCE {fmt(r['roce'], '%')}, ROE {fmt(r['roe'], '%')}, margin {fmt(r['margin'], '%', 1)}",
         f"Growth a year: sales {fmt(r['rev_growth'], '%')}, profit {fmt(r['profit_growth'], '%')}",
         f"Health: debt/equity {fmt(r['de'], d=2)}, interest cover {fmt(r['int_cover'], 'x', 1)}, current ratio {fmt(r['current_ratio'], d=1)}",
         f"Cash: operating cash {fmt(r['ocf_to_profit'], 'x', 1)} of profit, free cash ₹{fmt(r['fcf_cr'])} cr",
         f"Valuation: P/E {fmt(r['pe'], d=1)}, P/B {fmt(r['pb'], d=1)} · promoters {fmt(r['promoter_pct'], '%', 1)} · health checks {r['fscore']}/8",
         "Scores: " + ", ".join(f"{k} {v:.0f}" for k, v in r["parts"].items())]
    P = picks()
    if len(P):
        last = P.iloc[-1]
        ld = candles.load(str(last["symbol"]), "day")
        if ld is not None and len(ld):
            ch = (float(ld["close"].iloc[-1]) / float(last["price"]) - 1) * 100
            L += ["", f"Last quarter's pick {last['symbol']} ({last['quarter']}): {ch:+.1f}% since then."]
    L += ["", "<i>Research, not a trade tip - a company worth studying. Data: NSE filings (results), Kite (prices).</i>"]
    return "\n".join(L)


def due(t=None):
    """A pick is due if none was sent this quarter and (it is the first weekday of the quarter or no pick ever)."""
    t = pd.Timestamp(t or pd.Timestamp.now())
    P = picks()
    if len(P) and quarter(t) in set(P["quarter"]):
        return False
    if not len(P):
        return True
    start = pd.Timestamp(f"{t.year}-{3 * ((t.month - 1) // 3) + 1:02d}-01")
    return t >= start and t.weekday() < 5 and t.hour * 60 + t.minute >= 18 * 60 + 30


def run(send=True, t=None):
    prices = eligible()
    if not prices:
        return "no Kite daily candles yet"
    refresh(list(prices))
    have = sum(1 for s in prices if _file(s).exists())
    if not due(t):
        return f"filings read for {have}/{len(prices)}; not due"
    if have < 0.8 * len(prices):
        return f"filings read for {have}/{len(prices)} - the pick waits until 80% are read"
    r = choose(prices)
    if r is None:
        return "no company passed"
    msg = message(r, prices[r["symbol"]], quarter(t))
    if send:
        from . import telegram
        if telegram.send(load_settings(), msg, html=True, label="company of the quarter") != "Telegram message sent":
            return "Telegram failed"
    P = pd.concat([picks(), pd.DataFrame([{"quarter": quarter(t), "date": str(pd.Timestamp(t or pd.Timestamp.now()).date()),
                                           "symbol": r["symbol"], "score": r["score"], "price": prices[r["symbol"]]}])])
    PICKS.parent.mkdir(parents=True, exist_ok=True)
    P.to_csv(PICKS, index=False)
    return f"sent {r['symbol']}"
