"""Tip checker: judge a stock tip (e.g. forwarded from a Telegram channel) in seconds.

What it does (research, not advice):
  1. PARSE the message: stock, buy/sell, entry price or zone, stop-loss, targets, intraday or swing.
  2. LIVE price check: has the price already run past the entry, or fallen through the stop?
  3. BASE RATE from THIS stock's own last 5 years of daily prices: from any day's close, how often did
     the price reach the target distance BEFORE the stop distance within the holding window?
     (If both happen on the same day we assume the stop came first - conservative.)
  4. COSTS: the win rate needed to break even after Zerodha charges + slippage.
  5. RED FLAGS: no stop-loss, illiquid/small stock (typical pump-and-dump), surveillance series,
     results due, weak trend, stop too tight/wide, weak market.
  6. Every checked tip is saved to journal/forwarded_tips.csv and its real outcome is tracked,
     so we learn which tip sources are any good.
"""
import io
import math
import re
import time
from datetime import date

import numpy as np
import pandas as pd
import requests

from . import costs, data_prices, fundamentals
from .config import DATA, PRIVATE, DISCLAIMER, EVENTS, JOURNAL, get_logger

log = get_logger()
TIPS_F = PRIVATE / "forwarded_tips.csv"   # personal (channel names, messages): not in the public repo
STOPWORDS = {"BUY", "SELL", "SL", "TGT", "CMP", "NSE", "BSE", "TARGET", "TARGETS", "STOP", "LOSS", "ABOVE",
             "BELOW", "NEAR", "AT", "ON", "FOR", "THE", "AND", "OR", "INTRADAY", "SWING", "BTST", "STBT", "CALL",
             "ENTRY", "EXIT", "RANGE", "ZONE", "HOLD", "LONG", "SHORT", "TERM", "DAYS", "WEEK", "WEEKS", "ADD",
             "TO", "IN", "OF", "UP", "NEW", "BOOK", "PROFIT", "RS", "INR", "LTP", "PRICE", "TRADE", "STOCK",
             "TODAY", "TOMORROW", "NIFTY", "BANKNIFTY", "FUT", "CE", "PE", "OPTION", "OPTIONS", "AROUND", "ONLY",
             "IS", "A", "AN", "WITH", "STRONG", "BREAKOUT", "CHART", "VIEW", "POSITIONAL", "SAFE", "SURE", "SHOT",
             "JACKPOT", "MULTIBAGGER", "T1", "T2", "T3", "TG", "SLOSS", "STOPLOSS", "BUYING", "GOOD", "BEST"}


# ----------------------------------------------------------------------------- symbols
def equity_list():
    f = EVENTS / "equity_list.csv"
    if not f.exists() or (time.time() - f.stat().st_mtime) > 7 * 86400:
        try:
            r = requests.get("https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv",
                             headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
            r.raise_for_status()
            new = pd.read_csv(io.BytesIO(r.content))
            new.columns = [c.strip() for c in new.columns]
            if "SYMBOL" not in new.columns or len(new) < 1000:     # an error page or broken file: keep the old list
                raise ValueError(f"unexpected NSE file ({len(new)} rows)")
            new.to_csv(f, index=False)
        except Exception as e:
            log.warning("NSE equity list download failed: %s", e)
            if f.exists():
                f.touch()                                             # retry tomorrow, not on every message
    df = pd.read_csv(f)
    df.columns = [c.strip() for c in df.columns]
    return df


def _norm_name(n):
    n = re.sub(r"[^A-Z0-9 ]", " ", str(n).upper())
    n = re.sub(r"\b(LIMITED|LTD|INDIA|THE|COMPANY|CORPORATION|CORP|INDUSTRIES|IND)\b", " ", n)
    return re.sub(r"\s+", " ", n).strip()


NUM = r"(\d[\d,]*(?:\.\d+)?)"


def _num(s):
    return float(s.replace(",", ""))


def parse(text, eq=None):
    """Extract a structured tip from free text. Missing fields are None."""
    eq = equity_list() if eq is None else eq
    syms = set(eq["SYMBOL"].astype(str))
    t = text.upper().replace("₹", " ").replace("RS.", " ").replace("@", " AT ")
    t = re.sub(r"[🔥🎯🚀✅📈📉💰⭐️👉➡️]", " ", t)
    tip = {"raw": text.strip()[:500], "symbol": None, "side": "buy", "entry_low": None, "entry_high": None,
           "stop": None, "targets": [], "horizon": "swing"}
    if re.search(r"\b(SELL|SHORT|STBT)\b", t) and not re.search(r"\bBUY\b", t):
        tip["side"] = "sell"
    if re.search(r"\b(INTRADAY|INTRA ?DAY|SCALP)\b", t):
        tip["horizon"] = "intraday"
    elif re.search(r"\b(BTST|STBT)\b", t):
        tip["horizon"] = "btst"
    elif re.search(r"\b(POSITIONAL|LONG ?TERM|INVEST)\b", t):
        tip["horizon"] = "positional"
    # symbol: hashtag, then word after BUY/SELL, then any known symbol, then company name
    words = [w for w in re.findall(r"#?[A-Z0-9][A-Z0-9&\-]{1,19}", t) if re.search(r"[A-Z]", w)]
    cands = [w.lstrip("#") for w in words if w.lstrip("#") in syms and w.lstrip("#") not in STOPWORDS]
    tagged = [w.lstrip("#") for w in words if w.startswith("#") and w.lstrip("#") in syms]
    after = re.findall(r"\b(?:BUY|SELL|SHORT)\s+#?([A-Z0-9][A-Z0-9&\-]{1,19})", t)
    after = [a for a in after if a in syms]
    for how, group in (("tag", tagged), ("after", after), ("word", cands)):
        if group:
            tip["symbol"], tip["symbol_how"] = group[0], how
            break
    if tip["symbol"] is None:
        norm_t = " " + _norm_name(t) + " "
        best = None
        for s, n in zip(eq["SYMBOL"], eq["NAME OF COMPANY"]):
            nn = _norm_name(n)
            if len(nn) >= 4 and f" {nn} " in norm_t and (best is None or len(nn) > len(best[1])):
                best = (s, nn)
        if best:
            tip["symbol"], tip["symbol_how"] = best[0], "name"
    # stop-loss
    m = re.search(r"\b(?:SL|S\.L\.?|STOP ?LOSS|STOPLOSS|STOP)\b\s*[:\-=]?\s*(?:AT|BELOW|ABOVE)?\s*" + NUM, t)
    if m:
        tip["stop"] = _num(m.group(1))
    # targets: numbers after TGT/TARGET/T1.. (several, separated by / , - and)
    for m in re.finditer(r"\b(?:TGT|TARGETS?|TG|T\d)\b\s*[:\-=]?\s*((?:\d[\d,]*(?:\.\d+)?\s*(?:/|,|-|AND|&|\+|\s)\s*)*\d[\d,]*(?:\.\d+)?)", t):
        for x in re.findall(NUM, m.group(1)):
            v = _num(x)
            if v not in tip["targets"]:
                tip["targets"].append(v)
    # entry: number(s) after BUY/ENTRY/ABOVE/NEAR/AT/CMP/AROUND/RANGE/ZONE
    # the gap between keyword and number may not cross another keyword (TGT/SL) and may not hit the symbol's digits
    sym_t = t.replace(tip["symbol"], " SYMBOL ") if tip["symbol"] else t
    m = re.search(r"\b(?:BUY|SELL|SHORT|ENTRY|ABOVE|BELOW|NEAR|AT|CMP|AROUND|RANGE|ZONE)\b"
                  r"(?:(?!TGT|TARGET|\bSL\b|STOP|\bT\d)[^0-9]){0,25}?"
                  + NUM + r"(?:\s*(?:-|TO|–)\s*" + NUM + r")?", sym_t)
    if m:
        a = _num(m.group(1))
        b = _num(m.group(2)) if m.group(2) else a
        tip["entry_low"], tip["entry_high"] = min(a, b), max(a, b)
    # drop "numbers" that are clearly not prices (e.g. a target list swallowed the stop)
    if tip["stop"] in tip["targets"]:
        tip["targets"].remove(tip["stop"])
    return tip


# ----------------------------------------------------------------------------- evaluation
def live_price(symbol):
    try:
        import yfinance as yf
        fi = yf.Ticker(data_prices.yahoo_ticker(symbol)).fast_info
        p = float(fi["last_price"])
        if p > 0 and math.isfinite(p):
            return p
    except Exception as e:
        log.debug("live price failed %s: %s", symbol, e)
    return None


def history(symbol):
    df = data_prices.load(symbol)
    if df is None or (pd.Timestamp.today() - df.index[-1]).days > 5:
        data_prices.download_full([symbol], start=str((pd.Timestamp.today() - pd.DateOffset(years=6)).date()))
        df = data_prices.load(symbol)
    return df


def base_rate(df, up_pct, down_pct, horizon_days, side="buy", years=5):
    """Share of past days on which price moved +up_pct before -down_pct (buy) within horizon_days.
    Same-day touches of both count as a LOSS (conservative). Returns (win, loss, neither, n)."""
    df = df[df.index >= df.index[-1] - pd.DateOffset(years=years)]
    c, h, l = df["close"].values, df["high"].values, df["low"].values
    n = len(c) - horizon_days - 1
    if n < 100:
        return None
    win = loss = 0
    for i in range(n):
        base = c[i]
        up, dn = base * (1 + up_pct), base * (1 - down_pct)
        for k in range(i + 1, i + 1 + horizon_days):
            if side == "buy":
                hit_dn, hit_up = l[k] <= dn, h[k] >= up
            else:
                hit_dn, hit_up = h[k] >= base * (1 + down_pct), l[k] <= base * (1 - up_pct)
            if hit_dn:
                loss += 1
                break
            if hit_up:
                win += 1
                break
    return win / n, loss / n, 1 - (win + loss) / n, n


def evaluate(tip, capital=45000.0):
    """Return (verdict, list of reasons, details dict)."""
    reasons, flags, details = [], [], {}
    sym = tip.get("symbol")
    if not sym:
        return "UNKNOWN", [("missing", "I could not find an NSE stock symbol in this message. Try e.g. 'BUY TATASTEEL 150 SL 145 TGT 160', or for an index/forex/gold/crypto: 'Nifty weakness only below 24290', 'XAUUSD BUY 2650 SL 2640 TP 2670'.")], {}
    eq = equity_list()
    row = eq[eq["SYMBOL"] == sym]
    series = str(row[" SERIES"].iloc[0] if " SERIES" in row else row["SERIES"].iloc[0]).strip() if len(row) else "?"
    df = history(sym)
    if df is None or len(df) < 150:
        return "AVOID", [("con", f"{sym} has too little reliable price history (new or rarely traded stock) - it can't be checked, and that alone is a risk.")], {}
    a = data_prices.adjusted(df)
    last_close = float(df["close"].iloc[-1])
    ltp = live_price(sym) or last_close
    details["ltp"] = round(ltp, 2)
    side = tip.get("side", "buy")
    sgn = 1 if side == "buy" else -1
    entry = tip.get("entry_high") or tip.get("entry_low") or ltp
    if tip.get("entry_low") and tip.get("entry_high"):
        entry = (tip["entry_low"] + tip["entry_high"]) / 2
    # sanity: entry must be near the real price (catches wrong symbol or old tips)
    if abs(entry / ltp - 1) > 0.10:
        reasons.append(("block", f"The tip's entry ({entry:g}) is {abs(entry / ltp - 1) * 100:.0f}% away from today's price ({ltp:.2f}) - it is an old tip, the wrong stock, or a typo. Acting on it now is not the trade they meant."))
        flags.append("AVOID")
    tr = np.maximum(df["high"] - df["low"], np.maximum((df["high"] - df["close"].shift()).abs(),
                                                       (df["low"] - df["close"].shift()).abs()))
    atr = float(tr.rolling(14).mean().iloc[-1])
    details["atr"] = round(atr, 2)
    # liquidity & surveillance (pump-and-dump protection)
    tv = float((df["close"] * df["volume"]).tail(60).median())
    details["median_daily_value_cr"] = round(tv / 1e7, 1)
    if tv < 5e7:
        reasons.append(("block", f"Very illiquid: only ~Rs {tv/1e7:.1f} crore traded a day. Tips on small, thinly traded stocks "
                       "are the classic Telegram pump-and-dump (SEBI has acted against such channels)."))
        flags.append("AVOID")
    elif tv < 5e8:
        reasons.append(("block", f"Small/less liquid stock (~Rs {tv/1e7:.0f} crore a day): bigger gaps and slippage."))
        flags.append("CAUTION")
    else:
        reasons.append(("pro", f"Well traded (about Rs {tv/1e7:,.0f} crore a day), so you can get in and out easily."))
    if series not in ("EQ", "?"):
        reasons.append(("con", f"Trades in the '{series}' series (trade-to-trade / surveillance) - higher risk."))
        flags.append("AVOID")
    # stop-loss
    stop = tip.get("stop")
    if stop is None:
        stop = entry - sgn * 2 * atr
        reasons.append(("block", f"No stop-loss given. A tip without a stop is a red flag. If you take it, use about {stop:.2f} (2x daily range)."))
        flags.append("CAUTION")
    risk = (entry - stop) * sgn
    if risk <= 0:
        return "AVOID", [("con", f"The stop-loss {stop:g} is on the wrong side of the entry {entry:g} - the tip doesn't make sense as written.")], details
    if (ltp - stop) * sgn <= 0:
        reasons.append(("con", f"Price {ltp:.2f} is already beyond the stop-loss {stop:g}: the tip has already failed."))
        flags.append("AVOID")
    stop_atr = risk / atr
    details["stop_atr"] = round(stop_atr, 2)
    horizon = {"intraday": 1, "btst": 2, "swing": 10, "positional": 40}[tip.get("horizon", "swing")]
    if tip.get("horizon") == "intraday" and stop_atr < 0.3:
        reasons.append(("con", "Stop is extremely tight even for intraday - likely to be hit by normal noise."))
        flags.append("CAUTION")
    elif tip.get("horizon") != "intraday" and stop_atr < 0.7:
        reasons.append(("con", f"Stop is very tight ({stop_atr:.1f}x the normal daily move) - normal noise will likely hit it."))
        flags.append("CAUTION")
    if stop_atr > 5:
        reasons.append(("con", f"Stop is very wide ({risk / entry * 100:.1f}% away) - a big loss if it fails."))
        flags.append("CAUTION")
    targets = [x for x in tip.get("targets", []) if (x - entry) * sgn > 0]
    if not targets:
        targets = [entry + sgn * 1.5 * risk]
        reasons.append(("info", "No target was given, so I used 1.5 times the risk as a fair reference target."))
    t1 = targets[0]
    reward = (t1 - entry) * sgn
    rr = reward / risk
    details.update({"entry": round(entry, 2), "stop": round(stop, 2), "target": round(t1, 2), "rr": round(rr, 2)})
    # already ran away?
    run = (ltp - entry) * sgn / entry * 100
    if run > 1.5 and abs(entry / ltp - 1) <= 0.10:
        reasons.append(("con", f"Price {ltp:.2f} has already moved {run:.1f}% past the entry - chasing it worsens the odds."))
        flags.append("CAUTION")
    # costs: per-share rupees for a round trip
    if tip.get("horizon") == "intraday":
        from .intraday import mis_costs
        cost_ps = mis_costs(entry * 100, entry * 100) / 100 + 2 * 0.0005 * entry
    else:
        cost_ps = (costs.buy_cost(entry * 100) + costs.sell_cost(entry * 100)) / 100 + 2 * costs.SLIPPAGE_PCT * entry
    need = (risk + cost_ps) / (reward + risk)        # win rate needed to break even after costs
    details["breakeven_win_pct"] = round(need * 100, 1)
    br = base_rate(df, reward / entry, risk / entry, horizon, side)
    if br:
        win, loss, neither, n = br
        decided = win + loss
        p = win / decided if decided > 0 else 0
        details.update({"hist_target_first_pct": round(p * 100, 1), "hist_samples": n,
                        "hist_unresolved_pct": round(neither * 100, 1)})
        ev_r = (p * (reward - cost_ps) - (1 - p) * (risk + cost_ps)) / risk
        details["expected_r"] = round(ev_r, 2)
        if p >= need + 0.05:
            reasons.insert(0, ("pro", f"In {sym}'s own last 5 years, a move like this reached the target before the stop "
                                      f"{p*100:.0f} times in 100 - more than the {need*100:.0f} needed after charges."))
        else:
            reasons.insert(0, ("con", f"In {sym}'s own last 5 years, a move like this reached the target first only "
                                      f"{p*100:.0f} times in 100 (within {horizon} trading day{'s' if horizon > 1 else ''}) - "
                                      f"it needs {need*100:.0f} to make money after charges."))
        if p < need - 0.05:
            flags.append("AVOID")
            reasons[0] = ("block", reasons[0][1])
        elif p < need + 0.05:
            flags.append("CAUTION")
    # trend & market
    s50, s200 = a["close"].rolling(50).mean().iloc[-1], a["close"].rolling(200).mean().iloc[-1]
    cl = a["close"].iloc[-1]
    if side == "buy" and cl < s200:
        reasons.append(("con", "Stock is below its 200-day average (long-term downtrend) - buying against the trend."))
        flags.append("CAUTION")
    if side == "buy" and cl > s50 > s200:
        reasons.append(("pro", "The stock is in an uptrend (above its rising 50- and 200-day averages) - buyers are in control."))
    nifty = data_prices.load("NIFTY50")
    if nifty is not None and side == "buy":
        nc = nifty["close"]
        if nc.iloc[-1] >= nc.rolling(200).mean().iloc[-1]:
            reasons.append(("pro", "The overall market (Nifty) is healthy - above its 200-day average."))
        if nc.iloc[-1] < nc.rolling(200).mean().iloc[-1]:
            reasons.append(("con", "Overall market (Nifty) is below its 200-day average - most stocks struggle then."))
            flags.append("CAUTION")
    # results
    try:
        rd = fundamentals.next_results_date(sym)
        if rd is not None and (rd - pd.Timestamp.today().normalize()).days <= 7:
            reasons.append(("con", f"Results due {rd.date()}: big gap risk."))
            flags.append("CAUTION")
    except Exception:
        pass
    try:   # news headlines about the stock (ROADMAP I4)
        from .intel_news import fetch as _nf, line as _nl
        _nf()
        nl = _nl(sym, row["NAME OF COMPANY"].iloc[0] if len(row) else "")
        if nl:
            reasons.append(("con" if "RED FLAG" in nl else "info", nl))
            if "RED FLAG" in nl:
                flags.append("CAUTION")
    except Exception:
        pass
    qty = int(max(0, min(capital * 0.01 / risk, capital * 0.25 / entry)))
    details["qty_1pct_risk"] = qty
    verdict = "AVOID" if "AVOID" in flags else ("RISKY" if flags.count("CAUTION") >= 1 else "GOOD")
    if verdict == "GOOD" and (not br or rr < 1.2):
        verdict = "RISKY"
    return verdict, reasons, details


def format_reply(tip, verdict, reasons, d, source="", picture=None, own=None, record=None, tm=None):
    from . import reply_card as rc
    side = tip.get("side", "buy")
    kinds = lambda k: [t for kk, t in reasons if kk == k]
    blocks = sorted(kinds("block"), key=lambda t: t.startswith("In "))   # the history odds go after the hard facts
    pros, cons, info = kinds("pro"), blocks + kinds("con"), kinds("info")
    pp, pc = rc.pattern_points(own, side)
    pros += pp
    cons += pc
    sym = tip.get("symbol") or "?"
    hz = {"intraday": "intraday", "btst": "buy today, sell tomorrow", "swing": "swing (days to 2 weeks)",
          "positional": "positional (weeks)"}.get(tip.get("horizon"), tip.get("horizon"))
    said = None
    if tip.get("symbol"):
        said = (f"{'Buy' if side == 'buy' else 'Sell'} {sym}"
                + (f" at {rc.fmt(tip['entry_low'])}" + (f"-{rc.fmt(tip['entry_high'])}" if tip.get("entry_high") and
                   tip["entry_high"] != tip["entry_low"] else "") if tip.get("entry_low") else " at the current price")
                + (f", stop-loss {rc.fmt(tip['stop'])}" if tip.get("stop") else ", no stop-loss given")
                + (", target " + " / ".join(rc.fmt(x) for x in tip["targets"]) if tip.get("targets") else "")
                + f" - {hz}.")
    now = None
    if d.get("ltp") and d.get("entry"):
        gap = (d["ltp"] / d["entry"] - 1) * 100
        now = (f"{rc.fmt(d['ltp'])} - " + ("right at the entry." if abs(gap) < 0.5 else
               f"{abs(gap):.1f}% {'above' if gap > 0 else 'below'} the entry."))
    risk_ps = abs(d["entry"] - d["stop"]) if d.get("entry") and d.get("stop") else None
    plan = {"side": side, "entry": d.get("entry"), "stop": d.get("stop"), "target": d.get("target"), "rr": d.get("rr"),
            "qty": d.get("qty_1pct_risk"), "risk_rs": (d.get("qty_1pct_risk") or 0) * (risk_ps or 0)} if d.get("stop") else None
    return rc.build(verdict, f"{sym} · stock tip" if tip.get("symbol") else "Forwarded message", said=said, now=now,
                    pros=pros, cons=cons, info=info, p=d.get("hist_target_first_pct"),
                    need=d.get("breakeven_win_pct"), plan=plan, record=record, tracking=bool(tip.get("symbol")) and
                    verdict != "UNKNOWN", source=source, raw=tip.get("raw"),
                    missing=(kinds("missing") or [None])[0], picture=picture, tm=tm)


LAST_TICKET = None   # the ticket made for the last forwarded stock tip (the bot sends it with its buttons)


def check_text(text, source="", capital=45000.0, image=None):
    from . import options_check
    o = options_check.parse_option(text)
    if o and o.get("symbol"):
        verdict, reasons, d = options_check.evaluate_option(o, capital)
        save({"symbol": o["symbol"], "side": f"{o['strike']:g} {o['kind']}", "horizon": "option",
              "raw": o["raw"]}, verdict, {"entry": d.get("premium"), "stop": o.get("stop"),
                                           "target": (o.get("targets") or [None])[0], "ltp": d.get("spot"),
                                           "hist_target_first_pct": d.get("hist_pct"),
                                           "breakeven_win_pct": d.get("need_pct"), "expected_r": d.get("expected_r")},
             source, outcome="n/a (option - outcome not tracked yet)")
        return options_check.format_option_reply(o, verdict, reasons, d, source=source)
    tip = parse(text)
    from . import market_views
    inst = market_views.find_instrument(text)
    # an index / forex / gold / crypto name beats a stock symbol that is only an ordinary word in the text
    # (e.g. "Gold Spot / U.S. Dollar" contains DOLLAR, which is also an NSE stock) - unless the stock was
    # clearly named (#SYMBOL or right after BUY/SELL)
    if inst and tip.get("symbol_how") in ("word", "name", None):
        tip["symbol"] = None
    if not tip.get("symbol"):   # not an NSE stock: an index / forex / gold / crypto view or setup?
        try:
            r = market_views.check(text, source, image=image)
            if r:
                return r
        except Exception as e:
            log.warning("market view check failed: %s", type(e).__name__)
    verdict, reasons, d = evaluate(tip, capital)
    if image and image.get("chart_price") and d.get("ltp") and abs(image["chart_price"] / d["ltp"] - 1) > 0.05:
        # safety rule: never analyse an instrument whose price does not match the chart
        from . import reply_card as rc
        return rc.build("UNKNOWN", f"{tip['symbol']} · stock tip", source=source,
                        missing=(f"the chart shows a price of {rc.fmt(image['chart_price'])}, but {tip['symbol']} is at "
                                 f"{rc.fmt(d['ltp'])}, so I may have picked the wrong instrument. Please type the name "
                                 "(e.g. 'XAUUSD' or the NSE symbol) with the picture"),
                        picture=[f"Price on the chart: {rc.fmt(image['chart_price'])}"])
    picture, own, record = None, None, None
    if tip.get("symbol"):
        from .chart_reader import apply_image, own_patterns_for
        from .market_views import source_record
        if image:
            picture = apply_image(dict(tip, side=tip.get("side"), wrong_if=True), image, d.get("ltp"))
        own = own_patterns_for(tip["symbol"], nse_stock=True)
        record = source_record(source)
    save(tip, verdict, d, source)
    global LAST_TICKET
    LAST_TICKET = None
    if tip.get("symbol") and verdict in ("GOOD", "RISKY", "NEUTRAL") and tip.get("side", "buy") == "buy" \
            and all(d.get(k) for k in ("entry", "stop", "target")):
        try:
            from . import risk
            LAST_TICKET = risk.new_ticket(tip["symbol"], "buy", d["entry"], d["stop"], d["target"],
                                          f"forwarded from {source or 'a channel'}")
        except Exception as e:
            log.warning("ticket failed: %s", type(e).__name__)
    tm = None
    if tip.get("symbol") and all(d.get(k) for k in ("entry", "stop", "target")):
        try:
            from . import timemachine
            hz = {"intraday": 1, "btst": 2, "swing": 10, "positional": 40}.get(tip.get("horizon"), 10)
            tm = timemachine.line(timemachine.simulate(history(tip["symbol"]), tip.get("side", "buy"), d["entry"],
                                                       d["stop"], d["target"], hz),
                                  "trading days", f"{tip['symbol']}'s own last year of daily bars, {hz}-day window")
        except Exception as e:
            log.warning("time machine failed: %s", type(e).__name__)
    return format_reply(tip, verdict, reasons, d, source=source, picture=picture, own=own, record=record, tm=tm)


def save(tip, verdict, d, source, outcome=None, extra=None):
    row = {"checked": str(pd.Timestamp.now().round("s")), "source": source, "symbol": tip.get("symbol"),
           "side": tip.get("side"), "horizon": tip.get("horizon"), "verdict": verdict,
           "entry": d.get("entry"), "stop": d.get("stop"), "target": d.get("target"), "ltp": d.get("ltp"),
           "hist_pct": d.get("hist_target_first_pct"), "need_pct": d.get("breakeven_win_pct"),
           "expected_r": d.get("expected_r"),
           "outcome": outcome or ("open" if tip.get("symbol") else "n/a"),
           "raw": tip.get("raw", "").replace("\n", " ")[:300], **(extra or {})}
    df = pd.read_csv(TIPS_F) if TIPS_F.exists() else pd.DataFrame()
    pd.concat([df, pd.DataFrame([row])], ignore_index=True).to_csv(TIPS_F, index=False)


def update_outcomes():
    """Did each forwarded tip hit its target or its stop first? (daily bars, stop-first if both)."""
    if not TIPS_F.exists():
        return pd.DataFrame()
    df = pd.read_csv(TIPS_F)
    for i, r in df.iterrows():
        if r.get("outcome") != "open" or pd.isna(r.get("entry")):
            continue
        h = data_prices.load(r["symbol"])
        if h is None:
            continue
        since = h[h.index > pd.Timestamp(r["checked"]).normalize()]
        horizon = {"intraday": 1, "btst": 2, "swing": 10, "positional": 40}.get(r["horizon"], 10)
        sgn = 1 if r["side"] == "buy" else -1
        for k, (d, bar) in enumerate(since.iterrows()):
            hit_stop = (bar["low"] <= r["stop"]) if sgn == 1 else (bar["high"] >= r["stop"])
            hit_tgt = (bar["high"] >= r["target"]) if sgn == 1 else (bar["low"] <= r["target"])
            if hit_stop:
                df.at[i, "outcome"] = "stop"; break
            if hit_tgt:
                df.at[i, "outcome"] = "target"; break
            if k + 1 >= horizon:
                df.at[i, "outcome"] = "expired"; break
    df.to_csv(TIPS_F, index=False)
    return df


def update_and_notify(send=True):
    """Re-check open forwarded STOCK tips and message the owner about each one that finished."""
    if not TIPS_F.exists():
        return []
    before = pd.read_csv(TIPS_F)["outcome"].tolist()
    df = update_outcomes()
    msgs = []
    changed = False
    for (i, r), old in zip(df.iterrows(), before):
        if old == "open" and r["outcome"] != "open":
            if "resolved" not in df:
                df["resolved"] = None
            df["resolved"] = df["resolved"].astype(object)
            df.at[i, "resolved"] = str(pd.Timestamp.now(tz="Asia/Kolkata").date())
            changed = True
            head = {"target": "✅ RIGHT", "stop": "❌ WRONG", "expired": "⌛ NO RESULT"}.get(r["outcome"], r["outcome"])
            what = {"target": f"it reached the target {r['target']}", "stop": f"it hit the stop-loss {r['stop']}",
                    "expired": "neither target nor stop was hit in the time allowed"}.get(r["outcome"], r["outcome"])
            ours = {"GOOD": "worth considering", "RISKY": "risky", "AVOID": "skip it", "NEUTRAL": "coin flip"}.get(
                r["verdict"], str(r["verdict"]).lower())
            msgs.append(f"{head} - {r['symbol']} ({r['side']}) tip from {r['source'] or 'forwarded'} ({str(r['checked'])[:10]})\n"
                        f"What happened: {what}.\nMy verdict then was: {ours}.")
    if changed:
        df.to_csv(TIPS_F, index=False)
    if send and msgs:
        from . import telegram
        from .config import load_settings
        from .market_views import source_record
        recs = sorted({source_record(s, df) for s in df["source"].dropna().unique() if any(str(s) in m for m in msgs)} - {None})
        telegram.send(load_settings(), "\n\n".join(msgs + ["📒 Scoreboard\n" + "\n".join(recs)] * bool(recs) + [DISCLAIMER]),
                      label="stock tip update")
    return msgs


def source_scorecard():
    """How have forwarded tips done, by source and by our verdict?"""
    if not TIPS_F.exists():
        return {}
    df = update_outcomes()
    done = df[df["outcome"].isin(["target", "stop", "expired"])]
    if len(done) == 0:
        return {}
    by = lambda col: {k: {"tips": int(len(g)), "target_hit_pct": round((g["outcome"] == "target").mean() * 100, 1),
                          "stop_hit_pct": round((g["outcome"] == "stop").mean() * 100, 1)}
                      for k, g in done.groupby(col)}
    return {"by_source": by("source"), "by_verdict": by("verdict")}
