"""Watchlists the owner forwards (pictures or text from research firms) - D101.

1. read every NSE stock on it (symbols or company names; OCR text for pictures)
2. for each: the system's own read on daily data - trend, 2-day RSI, the high-probability dip-buy rule (D98), the
   pattern library, distance from the 52-week high, liquidity -> a score out of 10 and one line of reasons
3. stocks with a dip-buy signal NOW are sent as trades in the Normal-trade format (and F&O when it fits)
4. all of them stay watched (data/private/watchlist.csv): the evening scan includes them, so a later dip-buy signal
   arrives as a normal tip. Watchlist stocks outside the 300 most-traded are labelled "outside the tested universe".
"""
import re

import numpy as np
import pandas as pd

from .config import PRIVATE, get_logger

log = get_logger()
WL_F = PRIVATE / "watchlist.csv"
COMMON = {"BUY", "SELL", "HOLD", "TARGET", "STOP", "LOSS", "NSE", "BSE", "STOCKS", "STOCK", "WATCH", "LIST", "WATCHLIST",
          "TOP", "PICKS", "PICK", "CMP", "PRICE", "VIEW", "WEEK", "MONTH", "TODAY", "FOR", "THE", "AND", "OF", "TO", "IN",
          "ON", "AT", "IS", "BY", "NEW", "HIGH", "LOW", "OPEN", "CLOSE", "LTP", "SL", "TGT", "RS", "INR", "UP", "DOWN"}


def extract_symbols(text, eq=None):
    """All NSE stocks named in a text (symbols first, then company names), in order of appearance."""
    from .tipcheck import _norm_name, equity_list
    eq = equity_list() if eq is None else eq
    syms = set(eq["SYMBOL"].astype(str))
    up = text.upper()
    found = []
    for w in re.findall(r"#?[A-Z][A-Z0-9&\-]{1,19}", up):
        w = w.lstrip("#")
        if w in syms and w not in COMMON and w not in found and len(w) >= 3:
            found.append(w)
    norm = " " + _norm_name(up) + " "
    names = sorted(((s, _norm_name(n)) for s, n in zip(eq["SYMBOL"], eq["NAME OF COMPANY"])), key=lambda x: -len(x[1]))
    for s, nn in names:
        if len(nn) >= 5 and f" {nn} " in norm and s not in found:
            found.append(s)
            norm = norm.replace(f" {nn} ", " ")
    return found


def looks_like_watchlist(text, eq=None):
    return len(extract_symbols(text, eq)) >= 3


def _daily(sym):
    from . import data_prices
    d = data_prices.load(sym)
    if d is None or len(d) < 210:
        try:
            import yfinance as yf
            from .data_prices import yahoo_ticker
            y = yf.download(yahoo_ticker(sym), period="2y", interval="1d", progress=False, auto_adjust=False)
            if len(y):
                y.columns = y.columns.get_level_values(0) if hasattr(y.columns, "levels") else y.columns
                d = y.rename(columns=str.lower).rename(columns={"adj close": "adj_close"})
        except Exception:
            return None
    return d


def assess(sym, top300=None):
    """-> dict(symbol, price, score, reasons, signal) - the system's own read of one stock."""
    from . import high_prob
    d = _daily(sym)
    if d is None or len(d) < 210:
        return {"symbol": sym, "score": None, "reasons": ["not enough price history"], "signal": None}
    a = high_prob.adjusted(d)
    c = a["close"]
    px = float(a["raw_close"].iloc[-1])
    s50, s200 = c.rolling(50).mean().iloc[-1], c.rolling(200).mean().iloc[-1]
    r2 = float(high_prob.rsi(c).iloc[-1])
    hi52 = float(c.tail(250).max())
    val = float((d["close"] * d["volume"]).tail(60).median()) / 1e7 if "volume" in d else None
    pts, why = 0.0, []
    if c.iloc[-1] > s50 > s200:
        pts += 3; why.append("strong uptrend")
    elif c.iloc[-1] > s200:
        pts += 1.5; why.append("above its 200-day average")
    else:
        why.append("below its 200-day average (downtrend)")
    ext = c.iloc[-1] / s200 - 1
    if c.iloc[-1] >= 1.10 * s200:
        pts += 1
    gap = (c.iloc[-1] / hi52 - 1) * 100
    if gap > -5:
        pts += 1; why.append(f"near its 52-week high ({gap:+.0f}%)")
    elif gap < -25:
        why.append(f"{-gap:.0f}% below its 52-week high")
    try:
        from .chart_reader import own_patterns
        fired, candles = own_patterns(d)
        if fired:
            pts += min(2, len(fired) * 0.5); why.append(f"{len(fired)} bullish pattern(s): {', '.join(fired[:2])}")
        if candles and any(x.startswith("bearish") for x in candles):
            pts -= 0.5
    except Exception:
        pass
    if r2 < 10 and c.iloc[-1] > s200:
        pts += 1; why.append(f"pulled back (2-day RSI {r2:.0f}) inside the uptrend - the kind of dip the system buys")
    elif r2 > 90:
        pts -= 0.5; why.append("stretched after a sharp rise (2-day RSI above 90) - better to wait for a dip")
    if val is not None:
        if val < 5:
            pts -= 1.5; why.append(f"thinly traded (~₹{val:.1f} cr a day)")
        elif val > 50:
            pts += 0.5
    sig = high_prob.signal(d)
    mkt_ok = None
    try:
        from . import data_prices
        mkt_ok = high_prob.market_ok(data_prices.load("NIFTY50"))[0]
    except Exception:
        pass
    if sig and mkt_ok:
        pts += 2; why.insert(0, "DIP-BUY SIGNAL NOW (the 72%-tested rule)")
    elif sig:
        why.insert(0, "dip-buy conditions on the stock, but the market filter is not open today")
    if top300 is not None and sym not in top300:
        why.append("outside the 300 most-traded stocks the rule was tested on")
    score = int(np.clip(round(1 + pts * 9 / 9.5), 1, 10))
    return {"symbol": sym, "price": px, "score": score, "reasons": why, "signal": sig if (sig and mkt_ok) else None,
            "rsi2": r2}


def save(symbols, source):
    old = pd.read_csv(WL_F) if WL_F.exists() else pd.DataFrame(columns=["symbol", "source", "added"])
    now = str(pd.Timestamp.now(tz="Asia/Kolkata").date())
    new = pd.DataFrame([{"symbol": s, "source": source, "added": now} for s in symbols])
    out = pd.concat([old, new], ignore_index=True).drop_duplicates("symbol", keep="last")
    out = out[pd.to_datetime(out["added"]) >= pd.Timestamp.now().normalize() - pd.Timedelta(days=45)]   # 45-day watch
    out.to_csv(WL_F, index=False)
    return len(out)


def watched():
    try:
        return list(pd.read_csv(WL_F)["symbol"].astype(str))
    except Exception:
        return []


def handle(text, source=""):
    """Reply for a forwarded watchlist; trades that exist now are sent as tips."""
    from . import high_prob
    syms = extract_symbols(text)
    if not syms:
        return None
    try:
        top = set(high_prob.universe())
    except Exception:
        top = None
    rows = [assess(s, top) for s in syms[:40]]
    log.info("Watchlist: %d stock(s) read, %d rated, %d with a trade now", len(syms),
             sum(1 for r in rows if r.get("score")), sum(1 for r in rows if r.get("signal")))
    rows.sort(key=lambda r: -(r["score"] or 0))
    n_watch = save(syms, source)
    L = [f"📋 WATCHLIST from {source or 'forwarded'} · {len(syms)} stocks read", ""]
    for r in rows:
        if r["score"] is None:
            L.append(f"⚪ #{r['symbol']} - {r['reasons'][0]}")
            continue
        icon = "🟢" if r["score"] >= 7 else "🟡" if r["score"] >= 5 else "🔴"
        L.append(f"{icon} #{r['symbol']} {r['price']:,.2f} · {r['score']}/10 · " + "; ".join(r["reasons"][:3]))
    trades = [r for r in rows if r.get("signal")]
    L.append("")
    if trades:
        L.append(f"⚡ {len(trades)} trade(s) right now - sent as tips: " + ", ".join(f"#{r['symbol']}" for r in trades))
        day = str(pd.Timestamp.now(tz="Asia/Kolkata").date())
        try:
            from .live_engine import already
            sigs = [dict(r["signal"], symbol=r["symbol"]) for r in trades if not already(r["symbol"], "NORMAL", day)]
            high_prob.send_evening(day, sigs=sigs)
        except Exception as e:
            log.warning("watchlist trades failed: %s", type(e).__name__)
    else:
        L.append("⏳ No trade right now. I keep watching all of them for 45 days and send a tip the evening one "
                 "gives a dip-buy signal.")
    L.append(f"👀 Watching {n_watch} stocks in total. Research, not advice.")
    return "\n".join(L)
