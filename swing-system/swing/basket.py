"""MONTHLY BASKET (round 4, M3 - vantage-ai/validation/IMPROVE3_RESULTS.md).

Once a month, after the last trading day's close: the 20 strongest of the 300 most-traded NSE stocks, ranked the way
NSE's momentum indices rank them (6- and 12-month gain, each divided by how jumpy the stock was over the year).
Same money in each stock, bought at the next open, held for the month. When NIFTY is below its 200-day average the
basket goes to cash for the month (the rule that cut the worst fall in the test).

13-year test with delisted stocks and costs: 2013-Oct 2023 about 24.6% a year (NIFTY 12.0%), Nov 2023 onward about
19.5% a year (NIFTY 7.4%), worst fall 9% recently (NIFTY 15%) but 34% in older years (NIFTY 29%).

Quantities only when the owner has set the money for the basket (/basket 20000 in Telegram, or basket_capital in
settings.yaml) - never guessed. Messages are recorded before they are sent and sent once per month.
"""
import json

import numpy as np
import pandas as pd

from .config import DATA, PRIVATE, get_logger, load_settings

log = get_logger()
STATE_F = PRIVATE / "basket.json"
TOP = 20


def _state():
    try:
        return json.loads(STATE_F.read_text())
    except Exception:
        return {}


def _save(st):
    STATE_F.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_F.with_suffix(".tmp")
    tmp.write_text(json.dumps(st, indent=1))
    tmp.replace(STATE_F)


def capital(s=None):
    """Money for the basket: /basket <amount> (stored privately) wins over settings.yaml basket_capital. 0 = not set."""
    s = s or load_settings()
    v = _state().get("capital")
    if v is None:
        v = s.get("basket_capital") or 0
    try:
        return max(0.0, float(v))
    except Exception:
        return 0.0


def set_capital(amount):
    st = _state()
    st["capital"] = float(amount)
    _save(st)


FUND = r"BEES$|ETF|^LIQUID|GOLD|SILVER|^SETF|NIFTY|SHARE$|^KOTAK(PSU|BK)|CASE$|^LIQ"


def universe():
    """The 300 most-traded NSE names, funds/ETFs removed exactly as in the test (not on NSE's equity list + a fund name)."""
    import re
    u = pd.read_csv(DATA / "universe_history.csv")
    last = u[u["asof"] == u["asof"].max()]
    try:
        from .tipcheck import equity_list
        eq = set(equity_list()["SYMBOL"].astype(str))
    except Exception:
        eq = set()
    fund = re.compile(FUND)
    return [str(x) for x in last.nsmallest(300, "rank")["symbol"] if str(x) in eq or not fund.search(str(x))]


def _close(sym):
    from . import data_prices
    d = data_prices.load(sym)
    if d is None or not len(d):
        return None
    return (d["adj_close"] if "adj_close" in d else d["close"]).astype(float), d["close"].astype(float)


def rank(day, syms=None):
    """-> (cash: bool, ranked list of (sym, score, last raw price)) using closes up to and including `day`."""
    from . import data_prices
    day = pd.Timestamp(day)
    rows = []
    for sym in syms or universe():
        x = _close(sym)
        if x is None:
            continue
        c, raw = x[0][x[0].index <= day], x[1][x[1].index <= day]
        if len(c) < 253 or (day - c.index[-1]).days > 6:
            continue                                   # too short or stale: skipped, never guessed
        vol = c.pct_change().tail(252).std() * np.sqrt(252)
        if not vol or not np.isfinite(vol):
            continue
        score = ((c.iloc[-1] / c.iloc[-127] - 1) / vol + (c.iloc[-1] / c.iloc[-253] - 1) / vol) / 2
        if np.isfinite(score):
            rows.append((sym, float(score), float(raw.iloc[-1])))
    rows.sort(key=lambda r: -r[1])
    n = data_prices.load("NIFTY50")["close"]
    n = n[n.index <= day]
    cash = bool(n.iloc[-1] < n.tail(200).mean())
    return cash, rows


def last_weekday_of_month(day):
    day = pd.Timestamp(day)
    end = day + pd.offsets.MonthEnd(0)
    while end.weekday() >= 5:
        end -= pd.Timedelta(days=1)
    return day.normalize() == end.normalize()


def due(day, st=None):
    """-> the month (YYYY-MM) whose basket should be sent today, or None. Normal: the last weekday of the month.
    Fallback: that day was a holiday -> the first trading day of the next month sends last month's basket."""
    st = _state() if st is None else st
    day = pd.Timestamp(day)
    m = f"{day:%Y-%m}"
    prev = f"{day.replace(day=1) - pd.Timedelta(days=1):%Y-%m}"
    if not st.get("month"):
        return prev if not last_weekday_of_month(day) else m   # first ever basket: start now, no waiting
    if last_weekday_of_month(day) and st.get("month") != m:
        return m
    if day.day <= 7 and st.get("month") not in (prev, m) and st.get("month"):
        return prev
    return None


def message(day, cash, picks, old, cap, prices):
    keep = [p for p in picks if p in old]
    buy = [p for p in picks if p not in old]
    sell = [p for p in old if p not in picks]
    head = f"#VANTAGE MONTHLY BASKET\n\n📅 {pd.Timestamp(day):%d %b %Y} · act at the next market open\n"
    if cash:
        head += ("\n💤 Market is weak (NIFTY below its 200-day average): hold NO basket stocks this month."
                 + (f"\n🔴 SELL: {', '.join(sell)}" if sell else "") +
                 "\nThis rule cut the worst fall in the 13-year test. Next list at the end of next month.")
        return head
    slot = cap / TOP if cap else 0

    def line(sym):
        if not slot:
            return f"#{sym}"
        q = int(slot // prices[sym]) if prices.get(sym) else 0
        return f"#{sym} qty {q}" if q >= 1 else f"#{sym} (one share is above ₹{slot:,.0f} - skip)"
    out = head
    if sell:
        out += f"\n🔴 SELL: {', '.join(sell)}"
    if buy:
        out += "\n🟢 BUY:\n" + "\n".join(line(x) for x in buy)
    if keep:
        out += f"\n⚪ KEEP: {', '.join(keep)}"
    out += (f"\n\nSame money in each of the {TOP} stocks"
            + (f" (₹{slot:,.0f} each of ₹{cap:,.0f})" if slot else " - send /basket 20000 (your amount) to get quantities")
            + ". No stop-loss: the basket is checked once a month."
            + "\nTested 2013-2026: about 19% a year recently vs NIFTY 7%; it can fall 10-30% in bad years.")
    return out


def run(day=None, force=False):
    """The monthly job (daemon 'basket', weekday evenings after the price update). -> summary dict."""
    from . import telegram, safety, health, data_prices
    s = load_settings()
    day = pd.Timestamp(day or pd.Timestamp.now(tz="Asia/Kolkata").tz_localize(None).normalize())
    if not s.get("monthly_basket", True):
        return {"ok": True, "why": "switched off"}
    st = _state()
    month = due(day, st) if not force else f"{day:%Y-%m}"
    if month is None:
        return {"ok": True, "why": "not due"}
    try:
        if health.traded_today(day + pd.Timedelta(hours=19)) is False:
            return {"ok": True, "why": "market closed today"}
    except Exception:
        pass
    syms = universe()
    try:
        data_prices.update(syms + ["NIFTY50"])
    except Exception as e:
        log.warning("Basket: price update failed: %s", type(e).__name__)
    cash, rows = rank(day, syms)
    if len(rows) < 100:
        return {"ok": False, "why": f"only {len(rows)} stocks with fresh prices - not sent"}
    picks = [] if cash else [r[0] for r in rows[:TOP]]
    if s.get("kill_switch") or safety.emergency_active():
        picks = []                                        # safety stop: sells only, no new buys
    prices = {r[0]: r[2] for r in rows}
    old = list(st.get("holdings") or [])
    msg = message(day, cash, picks, old, capital(s), prices)
    st.update(month=month, holdings=picks, cash=cash, sent_day=str(day.date()),
              history=(st.get("history") or []) + [{"month": month, "holdings": picks, "cash": cash}])
    _save(st)                                             # record first ...
    telegram.send_reliable(s, msg, label="vantage indicator")   # ... then send
    log.info("Basket %s: %s, %d stocks", month, "cash" if cash else "invested", len(picks))
    return {"ok": True, "month": month, "cash": cash, "stocks": len(picks)}


def show():
    st = _state()
    if not st.get("month"):
        return "No monthly basket yet - the first list comes after the last trading day of this month."
    h = st.get("holdings") or []
    cap = capital()
    return (f"📦 Monthly basket ({st['month']}): " + (", ".join(h) if h else "cash (market weak)")
            + (f"\nMoney set: ₹{cap:,.0f} (₹{cap / TOP:,.0f} per stock)" if cap else "\nMoney not set: /basket 20000"))
