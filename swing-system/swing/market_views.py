"""Forwarded market VIEWS and SETUPS that are not an NSE stock: indices (Nifty, Bank Nifty, Sensex ...),
forex pairs (EURUSD, USDINR ...), gold/silver/crude, and crypto.

Two kinds of message are understood:
  * SETUP - has levels to trade: "XAUUSD BUY 2650 SL 2640 TP 2670 / 2690"
  * VIEW  - an opinion with a "wrong if" level: "#Nifty trend continuation on 60 min, weakness only below 24290"
            (bullish, wrong if it sustains below 24290). With no target given, the check uses a 1:1 move
            (as far up as the distance to the "wrong if" level), the fairest yes/no test of a view.

For each one: live price, how far the key level is, the trend on daily and hourly bars, and a base rate from
~2 years of hourly bars (how often did a move of this size in this direction come before the opposite move).
Every one is saved (private file) and tracked on hourly bars until it is right, wrong, or runs out of time;
the owner gets a Telegram message the moment that happens, and each channel's record is kept, so we learn
which sources are worth listening to. Research, not advice.
"""
import re
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from .config import DISCLAIMER, get_logger

log = get_logger()

# name in messages -> (yahoo ticker, display name, kind)
INSTRUMENTS = [
    (r"BANK ?NIFTY|NIFTY ?BANK|#BANKNIFTY", "^NSEBANK", "Bank Nifty", "index"),
    (r"FIN ?NIFTY|NIFTY ?FIN(?:ANCIAL)?(?: SERVICES)?", "NIFTY_FIN_SERVICE.NS", "Fin Nifty", "index"),
    (r"MIDCP ?NIFTY|NIFTY ?MIDCAP ?(?:SELECT|50)?", "^NSEMDCP50", "Nifty Midcap", "index"),
    (r"SENSEX", "^BSESN", "Sensex", "index"),
    (r"NIFTY ?(?:50)?(?! ?(?:IT|AUTO|PHARMA|METAL|FMCG|REALTY|ENERGY|MEDIA|PSU|NEXT))", "^NSEI", "Nifty 50", "index"),
    (r"XAU ?/?USD|GOLD ?SPOT|GOLD", "GC=F", "Gold (USD)", "commodity"),
    (r"XAG ?/?USD|SILVER", "SI=F", "Silver (USD)", "commodity"),
    (r"US ?OIL|WTI|CRUDE(?: ?OIL)?", "CL=F", "Crude oil (WTI)", "commodity"),
    (r"BTC ?/?USDT?|BITCOIN", "BTC-USD", "Bitcoin", "crypto"),
    (r"ETH ?/?USDT?|ETHEREUM", "ETH-USD", "Ethereum", "crypto"),
]
CCY = "EUR|GBP|USD|JPY|AUD|NZD|CAD|CHF|INR"
FX = re.compile(rf"\b({CCY}) ?/? ?({CCY})\b")
NUM = r"(\d[\d,]*(?:\.\d+)?)"
FX_NOTE = ("Note: in India only rupee pairs (USDINR, EURINR, GBPINR, JPYINR) on NSE/BSE are legal for residents; "
           "RBI warns against overseas forex/CFD apps. Tracking a setup here is research only.")


def _n(s):
    return float(s.replace(",", ""))


def find_instrument(text):
    t = " " + text.upper() + " "
    m = FX.search(t)
    if m and m.group(1) != m.group(2):
        pair = m.group(1) + m.group(2)
        return {"ticker": f"{pair}=X", "name": f"{m.group(1)}/{m.group(2)}", "kind": "forex"}
    for pat, tick, name, kind in INSTRUMENTS:
        if re.search(rf"(?<![A-Z])(?:{pat})(?![A-Z])", t):
            return {"ticker": tick, "name": name, "kind": kind}
    return None


def _timeframe(t):
    """Chart timeframe named in the message -> (label, hours the view is given to play out)."""
    m = re.search(r"\b(\d{1,3}) ?(MIN|MINS|MINUTE|MINUTES|M|H|HR|HRS|HOUR|HOURS)\b(?: ?TF| ?TIME ?FRAME| ?CHART)?", t)
    if m:
        k, u = int(m.group(1)), m.group(2)
        minutes = k * (60 if u.startswith("H") else 1)
        if minutes <= 15:
            return f"{minutes} min", 8
        if minutes <= 60:
            return f"{minutes} min", 24 * 3
        return f"{minutes // 60} hour", 24 * 7
    if re.search(r"\bWEEKLY\b|\bWEEK(?:LY)? (?:CHART|TF)\b", t):
        return "weekly", 24 * 60
    if re.search(r"\bDAILY\b|\b1D\b|\bPOSITIONAL\b|\bSWING\b", t):
        return "daily", 24 * 14
    if re.search(r"\bINTRADAY|SCALP", t):
        return "intraday", 8
    return "not stated", 24 * 5


def tf_minutes(label):
    m = re.match(r"(\d+) (min|hour)", str(label))
    if m:
        return int(m.group(1)) * (60 if m.group(2) == "hour" else 1)
    return {"daily": 1440, "weekly": 10080, "intraday": 15}.get(label)


def set_timeframe(v, minutes):
    """Timeframe read from the chart picture (e.g. 15 for a 15-minute chart)."""
    v["tf_min"] = minutes
    if minutes <= 15:
        v["timeframe"], v["hours"] = f"{minutes} min", 8
    elif minutes <= 60:
        v["timeframe"], v["hours"] = f"{minutes} min", 24 * 3
    elif minutes < 1440:
        v["timeframe"], v["hours"] = f"{minutes // 60} hour", 24 * 7
    elif minutes < 10080:
        v["timeframe"], v["hours"] = "daily", 24 * 14
    else:
        v["timeframe"], v["hours"] = "weekly", 24 * 60


def parse(text):
    inst = find_instrument(text)
    if not inst:
        return None
    t = text.upper().replace("₹", " ").replace("$", " ")
    t = re.sub(r"[^\w\s.,/:+\-#%]", " ", t)
    v = dict(inst, raw=text.strip()[:500], side=None, entry=None, stop=None, targets=[], wrong_if=None,
             type="view")
    if re.search(r"\b(BUY|LONG|BULLISH|UPSIDE|UPTREND|BREAKOUT|SUPPORT|BUY ON DIPS)\b", t):
        v["side"] = "buy"
    if re.search(r"\b(SELL|SHORT|BEARISH|DOWNSIDE|DOWNTREND|BREAKDOWN|SELL ON RISE)\b", t) and \
            not re.search(r"\b(BUY|LONG|BULLISH)\b", t):
        v["side"] = "sell"
    m = re.search(r"\b(?:SL|S/L|STOP ?LOSS|STOPLOSS|STOP)\b\s*[:\-=]?\s*(?:AT|BELOW|ABOVE)?\s*" + NUM, t)
    if m:
        v["stop"] = _n(m.group(1))
    for m in re.finditer(r"\b(?:TP|TGT|TARGETS?|T)(?:\s*\d(?![\d,.]))?\s*[:\-=]?\s*" + NUM, t):
        x = _n(m.group(1))
        if x not in v["targets"] and x != v["stop"]:
            v["targets"].append(x)
    m = re.search(r"\b(?:BUY|SELL|LONG|SHORT|ENTRY|ENTER)\b(?:\s+(?:NOW|LIMIT|STOP|AT|ZONE|AROUND|NEAR|CMP|@|:))*\s*" + NUM, t)
    if m and _n(m.group(1)) not in v["targets"] and _n(m.group(1)) != v["stop"]:
        v["entry"] = _n(m.group(1))
    # "weakness only (sustaining) below X" / "invalid below X" -> bullish, wrong if below X (and the mirror)
    m = re.search(r"\b(?:WEAK\w*|BEARISH|SELL(?:ING)?|INVALID(?:ATION)?|NEGATIVE|BREAKDOWN)\b[\w\s]{0,30}?"
                  r"\bBELOW\b\s*" + NUM, t)
    if m:
        v["wrong_if"], v["side"] = ("below", _n(m.group(1))), v["side"] or "buy"
    m = re.search(r"\b(?:STRENGTH|STRONG|BULLISH|BUY(?:ING)?|INVALID(?:ATION)?|POSITIVE|BREAKOUT)\b[\w\s]{0,30}?"
                  r"\bABOVE\b\s*" + NUM, t)
    if m and not v["wrong_if"]:
        v["wrong_if"], v["side"] = ("above", _n(m.group(1))), v["side"] or "sell"
    if v["stop"] and (v["entry"] or v["targets"]):
        v["type"] = "setup"
    v["timeframe"], v["hours"] = _timeframe(t)
    v["tf_min"] = tf_minutes(v["timeframe"])
    if re.search(r"\bTREND CONTINUATION\b", t) and v["side"] is None:
        v["side"] = "trend"        # decided from the actual trend once prices are loaded
    return v


# ----------------------------------------------------------------------------- prices
def hourly(ticker, period="730d", interval="60m"):
    import yfinance as yf
    df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=False)
    if df is None or not len(df):
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.rename(columns=str.lower)[["open", "high", "low", "close"]].dropna()
    df.index = pd.to_datetime(df.index, utc=True)
    return df


def daily(ticker):
    import yfinance as yf
    df = yf.download(ticker, period="2y", interval="1d", progress=False, auto_adjust=False)
    if df is None or not len(df):
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df.rename(columns=str.lower)[["open", "high", "low", "close"]].dropna()


def base_rate(h, up, down, bars, side):
    """Share of past hourly bars from which a move of `up` (in our direction) came before `down` against us,
    within `bars` bars. Same-bar ties count as a loss (conservative). Fractions, e.g. 0.004 = 0.4%."""
    c, hi, lo = h["close"].to_numpy(), h["high"].to_numpy(), h["low"].to_numpy()
    n = len(c)
    if n < bars + 50:
        return None, 0
    wins = losses = 0
    for i in range(0, n - bars, 3):                       # every 3rd bar: plenty of samples, fast
        if side == "buy":
            tgt, stp = c[i] * (1 + up), c[i] * (1 - down)
            w = np.argmax(hi[i + 1:i + 1 + bars] >= tgt) if (hi[i + 1:i + 1 + bars] >= tgt).any() else None
            l_ = np.argmax(lo[i + 1:i + 1 + bars] <= stp) if (lo[i + 1:i + 1 + bars] <= stp).any() else None
        else:
            tgt, stp = c[i] * (1 - up), c[i] * (1 + down)
            w = np.argmax(lo[i + 1:i + 1 + bars] <= tgt) if (lo[i + 1:i + 1 + bars] <= tgt).any() else None
            l_ = np.argmax(hi[i + 1:i + 1 + bars] >= stp) if (hi[i + 1:i + 1 + bars] >= stp).any() else None
        if w is not None and (l_ is None or w < l_):
            wins += 1
        elif l_ is not None:
            losses += 1
    tot = wins + losses
    return (round(wins / tot * 100, 1) if tot else None), tot


def _fmt(x):
    if x is None:
        return "n/a"
    return f"{x:,.5f}".rstrip("0").rstrip(".") if abs(x) < 10 else f"{x:,.2f}" if abs(x) < 10000 else f"{x:,.0f}"


def _hours_to_bars(hours, kind, bar_min=60):
    per_day = (24 * 60 if kind in ("forex", "crypto", "commodity") else 375) / bar_min   # NSE: 6h15m a day
    return max(4, int(round(hours / 24 * per_day)))


def bars_for(v):
    """Price bars matching the chart: 15-minute bars (last 60 days) for charts of 15 min or less, else hourly (2 yrs)."""
    if v.get("tf_min") and v["tf_min"] <= 15:
        return 15, "60d", "15m", "15-minute prices of the last 60 days"
    return 60, "730d", "60m", "hourly prices of the last 2 years"


def prices(v):
    bar_min, period, interval, _ = bars_for(v)
    return hourly(v["ticker"], period=period, interval=interval)


# ----------------------------------------------------------------------------- checking a message
def evaluate(v, h=None, d=None):
    """Fill in live price, plan levels, trend and odds. Returns (verdict, reasons, plan)."""
    h = prices(v) if h is None else h
    d = daily(v["ticker"]) if d is None else d
    bar_min, _, _, data_note = bars_for(v)
    if v.get("offset"):
        d = d + v["offset"] if d is not None else d
    if h is None or not len(h):
        return "UNKNOWN", ["Could not get prices for this right now (free data source). It is saved and will be "
                           "checked again."], {}
    px = float(h["close"].iloc[-1])
    reasons, plan = [], {"price": px}
    ema = h["close"].ewm(span=50).mean()
    h_trend = "up" if px > ema.iloc[-1] and ema.iloc[-1] > ema.iloc[-10] else \
        "down" if px < ema.iloc[-1] and ema.iloc[-1] < ema.iloc[-10] else "sideways"
    d_trend = None
    if d is not None and len(d) > 200:
        m50, m200 = d["close"].rolling(50).mean().iloc[-1], d["close"].rolling(200).mean().iloc[-1]
        d_trend = "up" if px > m50 > m200 else "down" if px < m50 < m200 else "mixed"
    side = v["side"]
    if side == "trend":
        side = "buy" if h_trend == "up" else "sell" if h_trend == "down" else None
    if side is None and v["wrong_if"]:
        side = "buy" if v["wrong_if"][0] == "below" else "sell"
    if side is None:
        return "UNKNOWN", [f"I found {v['name']} but not a direction (buy/sell, bullish/bearish) or a 'wrong if' "
                           f"level. Try e.g. '{v['name']} buy {_fmt(px)} SL {_fmt(px * 0.99)} TP {_fmt(px * 1.02)}'."], plan
    v["side"] = side
    entry = v["entry"] or px
    stop = v["stop"] or (v["wrong_if"][1] if v["wrong_if"] else None)
    if stop is None:
        return "UNKNOWN", [f"{v['name']} {'bullish' if side == 'buy' else 'bearish'} view noted, but there is no "
                           "stop or 'wrong if' level, so it cannot be checked fairly. Price now " + _fmt(px) + "."], plan
    risk = (entry - stop) if side == "buy" else (stop - entry)
    if risk <= 0:
        return "AVOID", [f"The stop/'wrong if' level {_fmt(stop)} is on the wrong side of the entry {_fmt(entry)}."], plan
    target = v["targets"][0] if v["targets"] else (entry + risk if side == "buy" else entry - risk)
    reward = (target - entry) if side == "buy" else (entry - target)
    rr = reward / risk if risk else 0
    plan.update(entry=entry, stop=stop, target=target, rr=round(rr, 2), side=side)
    gone = (px <= stop) if side == "buy" else (px >= stop)
    done = (px >= target) if side == "buy" else (px <= target)
    if gone:
        return "AVOID", [f"Price {_fmt(px)} is already past the stop/'wrong if' level {_fmt(stop)}: the call has "
                         "already failed."], plan
    if done:
        return "AVOID", [f"Price {_fmt(px)} is already at/through the target {_fmt(target)}: nothing left to gain."], plan
    word = "bullish" if side == "buy" else "bearish"
    dist = abs(px - stop) / px * 100
    days = max(1, v["hours"] // 24)
    tf = f"{v['timeframe']} chart" if v["timeframe"] != "not stated" else "no timeframe given"
    if v["type"] == "view":
        plan["said"] = (f"{v['name']} looks {word} ({tf}). The call is wrong if it "
                        f"{'falls below' if side == 'buy' else 'rises above'} {_fmt(stop)}.")
        reasons.append(("info", f"No target was given, so I judge it fairly as: does it move {_fmt(abs(target - entry))} "
                                f"{'up' if side == 'buy' else 'down'} (to {_fmt(target)}) before it breaks {_fmt(stop)}, "
                                f"within about {days} day(s)?"))
    else:
        plan["said"] = (f"{'Buy' if side == 'buy' else 'Sell'} {v['name']} at {_fmt(entry)}, stop {_fmt(stop)}, "
                        f"target {' / '.join(_fmt(x) for x in v['targets']) or _fmt(target)} ({tf}).")
    plan["now"] = (f"{_fmt(px)} - {dist:.1f}% away from the 'wrong' level {_fmt(stop)}"
                   + (", so there is room before it fails." if dist > 0.8 else ", very close - one small move can end it."))
    if v["type"] == "setup" and v["entry"] and abs(px - entry) / entry > 0.003:
        plan["now"] += f" Not at the entry {_fmt(entry)} yet - wait for it, don't chase."
    agree = (side == "buy" and h_trend == "up") or (side == "sell" and h_trend == "down")
    against = (side == "buy" and h_trend == "down") or (side == "sell" and h_trend == "up")
    if agree:
        reasons.append(("pro", f"It goes WITH the short-term trend ({'15-minute' if bar_min == 15 else 'hourly'} chart moving {h_trend}) - trends tend to "
                               "continue more often than they reverse."))
    elif against:
        reasons.append(("con", f"It goes AGAINST the short-term trend ({'15-minute' if bar_min == 15 else 'hourly'} chart moving {h_trend}) - fighting the "
                               "trend fails more often."))
    else:
        reasons.append(("info", f"The {'15-minute' if bar_min == 15 else 'hourly'} chart is moving sideways - no trend to help or hurt."))
    if d_trend == ("up" if side == "buy" else "down"):
        reasons.append(("pro", f"The bigger daily trend is {d_trend} too, so both timeframes agree."))
    elif d_trend == ("down" if side == "buy" else "up"):
        reasons.append(("con", f"The bigger daily trend is {d_trend} - the opposite direction."))
    elif d_trend == "mixed":
        reasons.append(("info", "The bigger daily trend is mixed (no clear direction)."))
    if dist < 0.4:
        reasons.append(("con", f"The 'wrong' level is only {dist:.1f}% away - normal noise can hit it."))
    bars = _hours_to_bars(v["hours"], v["kind"], bar_min)
    pct, n = base_rate(h, reward / entry, risk / entry, bars, side)
    need = round(100 / (1 + rr), 1) if rr > 0 else None
    plan.update(hist_pct=pct, need_pct=need, bars=bars, samples=n)
    if pct is not None and need is not None:
        if pct >= need + 3:
            reasons.append(("pro", f"In real {data_note}, a move like this went the right way first {pct:.0f} times in "
                                   f"100 ({n} cases) - more than the {need:.0f} needed."))
        else:
            reasons.append(("con", f"In real {data_note}, a move like this went the right way first only {pct:.0f} times "
                                   f"in 100 ({n} cases) - it needs {need:.0f} to pay off."))
    edge = pct is not None and need is not None and pct >= need + 3
    if pct is not None and pct < need - 3:
        verdict = "RISKY"
    elif edge and agree:
        verdict = "GOOD"
    else:
        verdict = "RISKY" if against else "NEUTRAL"
    if v["kind"] == "forex":
        reasons.append(("info", FX_NOTE))
    return verdict, reasons, plan


def source_record(source, rows=None):
    """'Dark Horse: 3 of 5 finished calls were right (60%) - ...' from the private journal of forwarded tips."""
    from .tipcheck import TIPS_F
    if rows is None:
        if not TIPS_F.exists():
            return None
        rows = pd.read_csv(TIPS_F)
    if "source" not in rows or not source:
        return None
    g = rows[(rows["source"] == source) & rows["outcome"].isin(["target", "stop", "expired"])]
    if len(g) == 0:
        return f"{source}: no finished calls yet - this is one of the first I'm tracking, so I can't say yet if they are any good."
    w = int((g["outcome"] == "target").sum())
    pct = w / len(g) * 100
    judge = ("too few calls to judge yet" if len(g) < 10 else
             "clearly better than chance" if pct >= 60 else "about a coin flip" if pct >= 45 else "worse than a coin flip")
    return f"{source}: {w} of {len(g)} finished calls were right ({pct:.0f}%) - {judge}."


def check(text, source="", image=None):
    """Returns a reply, or None if the message is not about an index/forex/commodity/crypto.
    image: what chart_reader.read_image found on a forwarded chart picture (levels, pattern names)."""
    from . import reply_card as rc
    v = parse(text)
    if not v:
        return None
    picture, h = None, None
    if image:
        from .chart_reader import apply_image
        picture = [f"Instrument: {v['name']}" + (" (matched from the price scale - no name was readable)"
                                                 if image.get("guessed") else "")]
        if image.get("timeframe_min"):
            set_timeframe(v, image["timeframe_min"])
            picture.append(f"Timeframe: {v['timeframe']} chart")
        pos = image.get("position")
        if pos and not v.get("stop"):
            v.update(side=pos["side"], entry=pos["entry"], stop=pos["stop"], targets=[pos["target"]], type="setup")
            picture.append(f"Position tool drawn: {'LONG (buy)' if pos['side'] == 'buy' else 'SHORT (sell)'} - entry "
                           f"{_fmt(pos['entry'])}, stop {_fmt(pos['stop'])}, target {_fmt(pos['target'])} (read from the box edges)")
        try:
            h = prices(v)
        except Exception:
            h = None
        price = float(h["close"].iloc[-1]) if h is not None and len(h) else None
        cp = image.get("chart_price")
        if cp and price:
            gap = cp / price - 1
            if abs(gap) > 0.03:     # safety rule: the data must be the same instrument as the chart
                from . import reply_card as rc
                return rc.build("UNKNOWN", f"{v['name']} · {v['type']}", source=source, picture=picture + [
                    f"Price on the chart: {_fmt(cp)}"], missing=(
                    f"the chart shows {_fmt(cp)} but my free data for {v['name']} is at {_fmt(price)} "
                    f"({gap * 100:+.1f}%), so this may be a different instrument or contract. Please type the exact name "
                    "with the picture (e.g. XAUUSD, NIFTY, BANKNIFTY, EURUSD)"))
            if abs(gap) > 0.0005:
                v["offset"] = cp - price
                h = h.copy()
                h[["open", "high", "low", "close"]] += v["offset"]
                picture.append(f"Price on the chart {_fmt(cp)}; my free data ({v['ticker']}) is {_fmt(price)} - "
                               f"{abs(gap) * 100:.2f}% apart (e.g. futures vs spot), so I shifted the data to match the chart.")
                price = cp
            else:
                picture.append(f"Price on the chart {_fmt(cp)} matches my data.")
        picture += apply_image(v, image, price)
    verdict, reasons, plan = evaluate(v, h=h)
    tag = "con" if verdict == "AVOID" else "missing" if verdict == "UNKNOWN" else "info"
    reasons = [r if isinstance(r, tuple) else (tag, r) for r in reasons]
    own = None
    if verdict not in ("UNKNOWN",):
        try:
            from .chart_reader import own_patterns_for
            own = own_patterns_for(v["ticker"])
        except Exception:
            pass
    from .tipcheck import save
    now = datetime.now(timezone.utc)
    tracking = bool(plan.get("stop")) and verdict not in ("AVOID", "UNKNOWN")
    save({"symbol": v["name"], "side": plan.get("side") or v.get("side"), "horizon": v["timeframe"], "raw": v["raw"]},
         verdict, {"entry": plan.get("entry"), "stop": plan.get("stop"), "target": plan.get("target"),
                   "ltp": plan.get("price"), "hist_target_first_pct": plan.get("hist_pct"),
                   "breakeven_win_pct": plan.get("need_pct")},
         source, outcome=("open" if v["type"] == "view" or not v["entry"] else "waiting entry") if tracking else "n/a",
         extra={"kind": v["kind"] + " " + v["type"], "ticker": v["ticker"], "checked_utc": now.isoformat(),
                "hours": v["hours"], "offset": v.get("offset", 0.0)})
    k = lambda kind: [t for kk, t in reasons if kk == kind]
    pros, cons = k("pro"), k("con")
    pp, pc = rc.pattern_points(own, plan.get("side") or "buy")
    pros += pp
    cons += pc
    side = plan.get("side")
    tm = None
    if plan.get("stop") and plan.get("target") and verdict not in ("UNKNOWN",):
        try:
            from . import timemachine
            hb = h if h is not None else prices(v)
            if v.get("offset") and h is None:
                hb = hb.copy(); hb[["open", "high", "low", "close"]] += v["offset"]
            bar_min, _, _, note = bars_for(v)
            tm = timemachine.line(timemachine.simulate(hb, side, plan["entry"], plan["stop"], plan["target"],
                                                       plan.get("bars") or 24, lookback=1000),
                                  "bars", f"real {note.replace(' of the last', ', last')}")
        except Exception as e:
            log.warning("time machine failed: %s", type(e).__name__)
    return rc.build(verdict, f"{v['name']} · {v['type']} ({'buy' if side == 'buy' else 'sell' if side == 'sell' else '?'})",
                    said=plan.get("said"), now=plan.get("now"), pros=pros, cons=cons, info=k("info"),
                    p=plan.get("hist_pct"), need=plan.get("need_pct"),
                    plan={"side": side, "entry": plan.get("entry"), "stop": plan.get("stop"), "target": plan.get("target"),
                          "rr": plan.get("rr")} if plan.get("stop") else None,
                    record=source_record(source), tracking=tracking, source=source, raw=v["raw"],
                    missing=(k("missing") or [None])[0], picture=picture, tm=tm)


# ----------------------------------------------------------------------------- tracking + alerts
def _walk(bars, side, entry, stop, target, waiting):
    """Walk hourly bars in time order -> (new status, when). Stop first if both in one bar (conservative)."""
    for ts, b in bars.iterrows():
        if waiting:
            if (side == "buy" and b["low"] <= entry) or (side == "sell" and b["high"] >= entry):
                waiting = False
            else:
                continue
        hit_s = b["low"] <= stop if side == "buy" else b["high"] >= stop
        hit_t = b["high"] >= target if side == "buy" else b["low"] <= target
        if hit_s:
            return "stop", ts
        if hit_t:
            return "target", ts
    return ("waiting entry" if waiting else "open"), None


def recheck_unknown(df, now, fetch=hourly, days=7):
    """Messages the old checker could not read (index/forex views) in the last `days` days: read them again now,
    judged at the price of the hour they were forwarded, and start tracking them. Rows are changed in place."""
    from .config import on_github
    for i, r in df.iterrows():
        if r.get("verdict") != "UNKNOWN" or (isinstance(r.get("ticker"), str) and r.get("ticker")):
            continue
        t0 = pd.Timestamp(r["checked"])
        t0 = t0.tz_localize("UTC" if on_github() else "Asia/Kolkata").tz_convert("UTC") if t0.tzinfo is None else t0
        if (pd.Timestamp(now) - t0).days > days:
            continue
        v = parse(str(r.get("raw", "")))
        if not v:
            continue
        try:
            h = fetch(v["ticker"], period="730d")
        except Exception:
            continue
        if h is None or not len(h[h.index <= t0]):
            continue
        verdict, _, plan = evaluate(v, h=h[h.index <= t0], d=None)
        if not plan.get("stop") or verdict in ("AVOID", "UNKNOWN"):
            continue
        for k, val in {"symbol": v["name"], "side": plan["side"], "horizon": v["timeframe"], "verdict": verdict,
                       "entry": plan["entry"], "stop": plan["stop"], "target": plan["target"], "ltp": plan["price"],
                       "hist_pct": plan.get("hist_pct"), "need_pct": plan.get("need_pct"),
                       "outcome": "open" if v["type"] == "view" or not v["entry"] else "waiting entry",
                       "kind": v["kind"] + " " + v["type"], "ticker": v["ticker"], "checked_utc": t0.isoformat(),
                       "hours": v["hours"]}.items():
            if k not in df:
                df[k] = None
            df[k] = df[k].astype(object)
            df.at[i, k] = val
        log.info("Re-read an earlier forwarded message as a %s %s and started tracking it", v["name"], v["type"])
    return df


def track(send=True, now=None, fetch=hourly):
    """Update every open non-stock call; message the owner about each one that finished. Returns messages."""
    from .tipcheck import TIPS_F
    if not TIPS_F.exists():
        return []
    df = pd.read_csv(TIPS_F)
    now = now or datetime.now(timezone.utc)
    df = recheck_unknown(df, now, fetch)
    if "ticker" not in df:
        return []
    msgs, cache = [], {}
    for i, r in df.iterrows():
        if r.get("outcome") not in ("open", "waiting entry") or pd.isna(r.get("ticker")) or pd.isna(r.get("stop")):
            continue
        t0 = pd.Timestamp(r["checked_utc"])
        t0 = t0.tz_localize("UTC") if t0.tzinfo is None else t0
        tk = r["ticker"]
        if tk not in cache:
            try:
                cache[tk] = fetch(tk, period="60d")
            except Exception as e:
                log.warning("view tracking: prices for %s failed: %s", tk, type(e).__name__)
                cache[tk] = None
        h = cache[tk]
        if h is None:
            continue
        bars = h[h.index > t0]
        off = float(r.get("offset") or 0) if "offset" in r and not pd.isna(r.get("offset")) else 0.0
        if off:
            bars = bars.copy()
            bars[["open", "high", "low", "close"]] += off
        status, when = _walk(bars, r["side"], float(r["entry"]), float(r["stop"]), float(r["target"]),
                             r["outcome"] == "waiting entry")
        hours = float(r.get("hours") or 120)
        if status in ("open", "waiting entry") and (now - t0).total_seconds() / 3600 > hours:
            status = "expired" if status == "open" else "never filled"
        if status == r["outcome"]:
            continue
        df.at[i, "outcome"] = status
        if status != "open":
            if "resolved" not in df:
                df["resolved"] = None
            df["resolved"] = df["resolved"].astype(object)
            df.at[i, "resolved"] = str(pd.Timestamp.now(tz="Asia/Kolkata").date())
        if status == "open":
            msgs.append(f"▶️ ENTRY REACHED - {r['symbol']} ({r['side']}) from {r['source'] or 'forwarded'}\n"
                        f"The price came to the entry {_fmt(float(r['entry']))}. If you took it, your exit-if-wrong level "
                        f"is {_fmt(float(r['stop']))}. I keep tracking it.")
            continue
        last = float(bars["close"].iloc[-1]) if len(bars) else None
        head = {"target": "✅ RIGHT", "stop": "❌ WRONG", "expired": "⌛ NO RESULT", "never filled": "⌛ NO TRADE"}[status]
        what = {"target": f"it reached the target {_fmt(float(r['target']))}",
                "stop": f"it broke the exit-if-wrong level {_fmt(float(r['stop']))}",
                "expired": "neither the target nor the exit level was hit in the time allowed",
                "never filled": f"the price never came to the entry {_fmt(float(r['entry']))}"}[status]
        when_txt = f" ({pd.Timestamp(when).tz_convert('Asia/Kolkata'):%d %b, %I:%M %p})" if when is not None else ""
        lesson = {"target": "The call worked. One win proves little - the score below is what matters.",
                  "stop": "The call failed. This is why the exit level matters: a small, planned loss.",
                  "expired": "Counts as not right. Calls that go nowhere tie up money.",
                  "never filled": "No trade, no loss - waiting for the entry protected you."}[status]
        msgs.append(f"{head} - {r['symbol']} ({r['side']}) from {r['source'] or 'forwarded'}\n"
                    f"What they said ({str(r['checked'])[:10]}): {r['side']} near {_fmt(float(r['entry']))}, "
                    f"wrong if {'below' if r['side'] == 'buy' else 'above'} {_fmt(float(r['stop']))}\n"
                    f"What happened: {what}{when_txt}" + (f"; price now {_fmt(last)}" if last else "") + ".\n"
                    f"What it means: {lesson}")
    df.to_csv(TIPS_F, index=False)
    if send and msgs:
        from . import telegram
        from .config import load_settings
        rec_lines = sorted({source_record(s, df) for s in df["source"].dropna().unique()
                            if any(str(s) in m for m in msgs)} - {None})
        telegram.send(load_settings(), "\n\n".join(msgs + ["📒 Scoreboard\n" + "\n".join(rec_lines)] * bool(rec_lines)
                                                     + [DISCLAIMER]),
                      label="forwarded call update")
    return msgs
