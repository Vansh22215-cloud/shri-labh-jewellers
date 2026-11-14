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


# ---- D102: line-by-line reading of watchlist PICTURES (NDTV Profit / CNBC-TV18 'stocks to watch' style) ----------
# names as the channels write them -> NSE symbol (short brand names a plain name match cannot find)
ALIASES = {"ZEE": "ZEEL", "ZEEENT": "ZEEL", "ZEEENTERTAINMENT": "ZEEL", "VODAIDEA": "IDEA", "VODAFONEIDEA": "IDEA",
           "VI": "IDEA", "HITACHIENERGY": "POWERINDIA", "TDPOWER": "TDPOWERSYS", "MANAPPURAMFIN": "MANAPPURAM",
           "MANAPPURAM": "MANAPPURAM", "OILINDIA": "OIL", "GODREJPROPS": "GODREJPROP", "GODREJPROP": "GODREJPROP",
           "NMDCSTEEL": "NSLNISP", "EIH": "EIHOTEL", "ETHOS": "ETHOSLTD", "EMS": "EMSLIMITED", "OLA": "OLAELEC",
           "OLAELECTRIC": "OLAELEC", "STARHEALTH": "STARHEALTH", "GODIGIT": "GODIGIT", "NETWEBTECH": "NETWEB",
           "E2E": "E2E", "E2ENETWORKS": "E2E", "AGIINFRA": "AGIIL", "MAHINDRAHOLIDAYS": "MHRIL", "NEWINDIA": "NIACL",
           "NEWINDIAASSURANCE": "NIACL", "DILIPBUILDCON": "DBL", "ORIENTCABLES": "ORIENTCABL", "ACE": "ACE",
           "KAYNES": "KAYNES", "KAYNESTECH": "KAYNES", "FINOBANK": "FINOPB", "SPAPPARELS": "SPAL", "RIL": "RELIANCE",
           "RELIANCEIND": "RELIANCE", "SBI": "SBIN", "L&T": "LT", "LANDT": "LT", "M&M": "M&M", "MANDM": "M&M",
           "HUL": "HINDUNILVR", "BAJAJFINANCE": "BAJFINANCE", "BAJAJFINSERV": "BAJAJFINSV", "AIRTEL": "BHARTIARTL",
           "BHARTIAIRTEL": "BHARTIARTL", "TATAMOTORS": "TATAMOTORS", "INFY": "INFY", "PAYTM": "PAYTM", "ZOMATO": "ETERNAL",
           "NYKAA": "NYKAA", "POLICYBAZAAR": "POLICYBZR", "IEX": "IEX", "MCX": "MCX", "BEL": "BEL", "HAL": "HAL",
           "BHEL": "BHEL", "IRFC": "IRFC", "RVNL": "RVNL", "LIC": "LICI", "SAIL": "SAIL", "ONGC": "ONGC", "IOC": "IOC",
           "BPCL": "BPCL", "HPCL": "HINDPETRO", "GAIL": "GAIL", "NTPC": "NTPC", "TCS": "TCS", "ITC": "ITC"}
# words on these pictures that are also NSE symbols or company-name starts - never stocks on their own
PICTURE_WORDS = {"NDTV", "PROFIT", "CNBC", "TV18", "CNBCTV18", "WATCHLIST", "STOCKS", "STOCKSTO", "WATCH", "RED", "GREEN",
                 "STAR", "TAKE", "CLEAN", "GLOBAL", "LIVE", "YOY", "QOQ", "PAT", "EBITDA", "MARGIN", "REVENUE", "CR",
                 "BLOCK", "DEAL", "DEALS", "PROVISION", "OFFER", "STRONG", "BUYBACK", "GUIDANCE", "ORDER", "ORDERS",
                 "FRIDAY", "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "SATURDAY", "SUNDAY", "DISCLAIMER", "Q2", "Q3",
                 "Q4", "Q1", "FY", "NET", "LOSS", "UP", "DOWN", "BOARD", "APPROVES", "SIGNS", "GOLD", "LAUNCHES", "CONSOLIDATED", "STANDALONE", "CONS", "PROMOTER", "BUYING", "MIXED"} | COMMON
BULL_HEAD = {"GREEN", "BULLISH", "POSITIVE", "GAINERS", "BUZZING", "UPBEAT", "BUY"}
BEAR_HEAD = {"RED", "BEARISH", "NEGATIVE", "LOSERS", "SELL"}
_TAILS = re.compile(r"(LIMITED|LTD|THE|COMPANY|CORPORATION|INDIA|\(INDIA\))")


def _condense(t):
    return re.sub(r"[^A-Z0-9&]", "", t.upper())


def _name_index(eq):
    """[(condensed company name without Limited/The/India, symbol)] - built once per equity list."""
    key = id(eq)
    if _name_index.cache.get("k") != key:
        idx = []
        for sym, nm in zip(eq["SYMBOL"].astype(str), eq["NAME OF COMPANY"].astype(str)):
            full = _condense(re.sub(r"(?i)\b(limited|ltd\.?|the)\b", " ", nm))
            idx.append((full, sym))
        _name_index.cache = {"k": key, "idx": idx, "syms": set(eq["SYMBOL"].astype(str))}
    return _name_index.cache


_name_index.cache = {}


def match_name(part, eq):
    """One name as written on a picture ('Hitachi Energy', 'TDPOWER', 'Mannapuram Finance') -> NSE symbol or None."""
    import difflib
    if not part or len(part) > 45:
        return None
    ix = _name_index(eq)
    tries = [part]
    if "l" in part:                      # OCR reads a capital I as a small l ('Vodafone ldea', 'AGlinfra')
        tries.append(re.sub(r"(?<![a-z])l|l(?=[A-Z])|(?<=[A-Z])l(?=[a-z])", "I", part))
    for t in tries:
        c = _condense(t)
        if len(c) < 2 or c in PICTURE_WORDS and c not in ALIASES:
            continue
        if c in ALIASES and ALIASES[c] in ix["syms"]:
            return ALIASES[c]
        if len(c) >= 3 and c in ix["syms"] and c not in PICTURE_WORDS:
            return c
        exact = [s for n, s in ix["idx"] if n == c]
        if exact and len(c) >= 3:
            return exact[0]
        if len(c) >= 6:
            pre = sorted(((n, s) for n, s in ix["idx"] if n.startswith(c) or (len(n) >= 6 and c.startswith(n)
                                                                               and len(c) - len(n) <= 4)),
                         key=lambda x: len(x[0]))
            if pre:
                return pre[0][1]
        if len(c) >= 8:                  # misspelt names ('Mannapuram Finance')
            names = [n for n, _ in ix["idx"]]
            m = difflib.get_close_matches(c, names, n=1, cutoff=0.88)
            if not m:
                m = difflib.get_close_matches(c, [n[:len(c)] for n in names], n=1, cutoff=0.9)
                if m:
                    return next(s for n, s in ix["idx"] if n[:len(c)] == m[0])
            if m:
                return next(s for n, s in ix["idx"] if n == m[0])
            sm = difflib.get_close_matches(c, list(ix["syms"]), n=1, cutoff=0.9)
            if sm:
                return sm[0]
    return None


def _line_stocks(text, eq):
    parts = [p.strip() for p in re.split(r",|&(?!\w)| and ", text) if p.strip()]
    hits = [s for s in (match_name(p, eq) for p in parts) if s]
    return hits if hits and len(hits) == len(parts) else []


def read_entries(boxes, eq=None):
    """OCR lines of a watchlist picture -> [{symbol, dir ('up'/'down'/None), note}] in reading order.
    Direction: a RED / GREEN (bullish / bearish) heading above the stock in the same column, else the green/red
    arrow printed next to the name. Note: the line written just under the name (the reason the channel gives)."""
    from .tipcheck import equity_list
    eq = equity_list() if eq is None else eq
    heads = []
    for b in boxes:
        c = _condense(b["text"])
        if c in BULL_HEAD or c in BEAR_HEAD:
            heads.append((b["x0"], b["y0"], "up" if c in BULL_HEAD else "down"))
    if heads:
        width = max(b["x1"] for b in boxes) or 1
        col = lambda b: 0 if (b["x0"] + 40) < width * 0.45 else 1
    else:
        width, col = 1, (lambda b: round(b["x0"] / 300))
    rows, used = [], set()
    for i, b in enumerate(boxes):
        hits = _line_stocks(b["text"], eq)
        if not hits:
            continue
        d = None
        if heads:
            above = [h for h in heads if h[1] < b["y0"] and (col({"x0": h[0]}) == col(b))]
            if above:
                d = max(above, key=lambda h: h[1])[2]
        else:
            d = b.get("arrow")
        note, last = [], b["y0"]
        for nb in boxes[i + 1:i + 8]:      # the lines just below it in the same column = the channel's reason
            if col(nb) != col(b) or not 0 < nb["y0"] - last < 90:
                continue
            if _line_stocks(nb["text"], eq) or len(note) == 2:
                break
            note.append(nb["text"]); last = nb["y0"]
        note = re.sub(r"\bQ (\d)\b", r"Q\1", " ".join(note))
        note = re.sub(r"\bYo Y\b", "YoY", re.sub(r"\bQ 0 Q\b", "QoQ", note))[:80]
        for s in hits:
            if s not in used:
                used.add(s)
                rows.append({"symbol": s, "dir": d, "note": note})
    return rows


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
    if d is not None and 20 <= len(d) < 210:          # recent listing / short history: a lighter check
        a = high_prob.adjusted(d)
        c = a["close"]
        n = min(50, len(c))
        avg = c.tail(n).mean()
        hi = c.max()
        pts = (2 if c.iloc[-1] > avg else 0) + (1 if c.iloc[-1] > c.tail(20).mean() else 0) + \
              (1 if c.iloc[-1] >= 0.95 * hi else 0)
        why = [("above" if c.iloc[-1] > avg else "below") + f" its {n}-day average (short history: "
               f"{len(c)} days - lighter check)"]
        return {"symbol": sym, "price": float(a["raw_close"].iloc[-1]), "score": int(min(6, 1 + pts * 1.3)),
                "reasons": why, "signal": None, "rsi2": float(high_prob.rsi(c).iloc[-1])}
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
    try:   # D103: a fresh demand zone (order block) just touched
        from .orderflow import order_block_touches
        t, _, _ = order_block_touches(a.tail(400))
        if t[-3:].any():
            pts += 0.5; why.append("at a demand zone (order block)")
    except Exception:
        pass
    if sig and mkt_ok:
        pts += 2; why.insert(0, "DIP-BUY SIGNAL NOW (the 72%-tested rule" + (", at an order block: 81%)" if sig.get("ob")
                                                                             else ")"))
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


def handle_entries(entries, source="", lists=1):
    """D102: one simple list from watchlist pictures (an album = several pictures) - bullish first, then bearish,
    each stock once with the channel's reason, how many lists named it, and the system's own score."""
    from . import high_prob
    merged = {}
    for e in entries:
        m = merged.setdefault(e["symbol"], {"symbol": e["symbol"], "up": 0, "down": 0, "notes": [], "n": 0})
        m["n"] += 1
        if e.get("dir") in ("up", "down"):
            m[e["dir"]] += 1
        if e.get("note") and e["note"] not in m["notes"]:
            m["notes"].append(e["note"])
    try:
        top = set(high_prob.universe())
    except Exception:
        top = None
    for m in merged.values():
        m["dir"] = "up" if m["up"] > m["down"] else "down" if m["down"] > m["up"] else ("mixed" if m["up"] else None)
        m.update({k: v for k, v in assess(m["symbol"], top).items() if k != "symbol"})
    rows = list(merged.values())
    log.info("Watchlist pictures: %d list(s), %d stock(s), %d rated, %d with a trade now", lists, len(rows),
             sum(1 for r in rows if r.get("score")), sum(1 for r in rows if r.get("signal")))
    n_watch = save([r["symbol"] for r in rows if r["dir"] != "down"], source)
    day = pd.Timestamp.now(tz="Asia/Kolkata")

    def chart(r):
        t = (r.get("reasons") or [""])[0]
        return ("strong uptrend" if t.startswith("strong uptrend") else "uptrend" if t.startswith("above") else
                "downtrend" if t.startswith("below") else "dip-buy signal" if t.startswith("DIP") else "no data") + \
            (" (new listing)" if "short history" in t else "")

    def line(k, r):
        sc = f"{r['score']}/10" if r.get("score") else "-"
        rep = f" ×{r['n']}" if r["n"] > 1 else ""
        why = r["notes"][0] if r["notes"] else ""
        return f"{k}. #{r['symbol']}{rep} · {sc} {chart(r)}\n    {why}"

    key = lambda r: (-r["n"], -(r.get("score") or 0))
    L = [f"📋 WATCHLIST · {day:%d %b} · {lists} picture(s) → {len(rows)} stocks", "",
         "How to read: ×2 = named in 2 lists · x/10 = my chart score (trend, momentum, liquidity) · "
         "then the channel's reason", ""]
    for title, want, icon in (("🟢 BULLISH - good news / in the green list", ("up",), ""),
                              ("🔴 BEARISH - bad news / in the red list", ("down",), ""),
                              ("⚪ MIXED / NO DIRECTION", ("mixed", None), "")):
        grp = sorted([r for r in rows if r["dir"] in want], key=key)
        if not grp:
            continue
        L.append(f"{title} ({len(grp)})")
        L += [line(i, r) for i, r in enumerate(grp, 1)]
        L.append("")
    best = sorted([r for r in rows if r["dir"] == "up" and (r.get("score") or 0) >= 7], key=key)[:5]
    L.append("🧠 WHAT IT MEANS")
    if best:
        L.append("• Strongest bullish names (good news + healthy chart): " + ", ".join(f"#{r['symbol']}" for r in best))
    L.append("• Good news is often priced in at the open - don't chase a big gap-up; my tips come only when a "
             "tested setup appears.")
    L.append("• Bearish names: avoid buying them for now (I don't short).")
    trades = [r for r in rows if r.get("signal") and r["dir"] != "down"]
    if trades:
        L.append(f"⚡ {len(trades)} trade(s) right now - sent as tips: " + ", ".join(f"#{r['symbol']}" for r in trades))
        try:
            from .live_engine import already
            sigs = [dict(r["signal"], symbol=r["symbol"]) for r in trades
                    if not already(r["symbol"], "NORMAL", str(day.date()))]
            high_prob.send_evening(str(day.date()), sigs=sigs)
        except Exception as e:
            log.warning("watchlist trades failed: %s", type(e).__name__)
    else:
        L.append("⏳ No trade right now. I watch the bullish ones for 45 days and send a tip when one gives a "
                 "tested dip-buy signal.")
    L.append(f"👀 Watching {n_watch} stocks in total. Research, not advice.")
    return "\n".join(L)


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
