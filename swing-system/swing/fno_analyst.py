"""F&O analyst for tips the owner forwards (D100): PROBABILITY out of 10 that the option reaches its FIRST target before
the stop-loss, with the reasons - and if the setup is good, the system TAKES it (tracks it with exit alerts) and
suggests an improved plan.

Steps (all from real data; Zerodha when logged in, Yahoo otherwise):
  1. read the tip: stock, strike, CE/PE, month, premium range, premium targets, stop (on SPOT or on premium), lot
  2. live spot, live option premium / open interest / spread (Kite), exact expiry (Kite instrument list)
  3. implied volatility from the premium -> the SPOT price at which each premium target / the stop is reached
     (Black-Scholes, a little time decay allowed for)
  4. probability = average of (a) the Time Machine: 10,000 replays from the stock's own 5-minute bars until expiry
     (max 5 days) and (b) the stock's own daily history: how often a move to that spot target came before the stop
  5. adjusted for: daily trend vs direction, option price vs the stock's real volatility, days to expiry, chasing,
     spread, and the channel's own track record (once it has 10+ finished calls)
"""
import math
import re

import numpy as np
import pandas as pd

from .config import get_logger, load_settings

log = get_logger()


def _spot_and_bars(sym):
    """(live spot, 5-minute bars, daily bars)."""
    from . import data_prices, kite
    daily = data_prices.load(sym)
    spot = None
    q = kite.quotes([sym]) if kite.logged_in() else {}
    if q.get(sym):
        spot = q[sym]["last"]
    bars = kite.historical(sym, "5minute", days=30) if kite.logged_in() else None
    if bars is None:
        try:
            import yfinance as yf
            from .data_prices import yahoo_ticker
            b = yf.download(yahoo_ticker(sym), period="30d", interval="5m", progress=False, auto_adjust=False)
            if len(b):
                b.columns = b.columns.get_level_values(0) if hasattr(b.columns, "levels") else b.columns
                b = b.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]].dropna()
                b.index = b.index.tz_convert("Asia/Kolkata").tz_localize(None)
                bars = b
        except Exception:
            bars = None
    if spot is None:
        spot = float(bars["close"].iloc[-1]) if bars is not None and len(bars) else \
            (float(daily["close"].iloc[-1]) if daily is not None and len(daily) else None)
    return spot, bars, daily


def _contract(sym, strike, kind, month, now):
    """(expiry, tradingsymbol, lot) from Kite's instrument list, else the standard monthly expiry."""
    try:
        from .live_engine import nfo
        ins = nfo()
        o = ins[(ins["name"] == sym) & (ins["instrument_type"] == kind) & (ins["strike"] == float(strike))]
        o = o[o["expiry"] >= now.normalize()]
        if month:
            om = o[o["expiry"].dt.month == int(month)]
            o = om if len(om) else o
        if len(o):
            r = o.sort_values("expiry").iloc[0]
            return pd.Timestamp(r["expiry"]), str(r["tradingsymbol"]), int(r["lot_size"])
    except Exception:
        pass
    from .options_check import monthly_expiry
    y = now.year + (1 if month and int(month) < now.month else 0)
    try:
        return pd.Timestamp(monthly_expiry(y, int(month or now.month))), None, None
    except Exception:
        return now.normalize() + pd.Timedelta(days=20), None, None


def _option_quote(ts):
    from . import kite
    if not ts or not kite.logged_in():
        return None
    try:
        q = kite._get("/quote", params=[("i", f"NFO:{ts}")]).json()["data"].get(f"NFO:{ts}", {})
        dep = q.get("depth", {})
        bid = (dep.get("buy") or [{}])[0].get("price") or 0
        ask = (dep.get("sell") or [{}])[0].get("price") or 0
        return {"ltp": float(q.get("last_price") or 0), "oi": q.get("oi"), "bid": bid, "ask": ask}
    except Exception:
        return None


def analyse(o, source=""):
    """-> dict with score (1-10), probability, reasons (pros/cons), plan, take (bool), improved (list)."""
    from .options_check import bs, implied_vol, spot_for_premium
    from . import timemachine, tipcheck
    now = pd.Timestamp.now(tz="Asia/Kolkata").tz_localize(None)
    sym, kind, K = o["symbol"], o["kind"], float(o["strike"])
    side = "buy" if kind == "CE" else "sell"                     # what the STOCK must do for the option to gain
    pros, cons, improved = [], [], []
    spot, bars, daily = _spot_and_bars(sym)
    if not spot:
        return {"score": None, "reasons": ([], ["could not get prices for this stock right now"]), "take": False}
    expiry, ts, lot_k = _contract(sym, K, kind, o.get("month"), now)
    lot = o.get("lot") or lot_k
    days = max(0.3, (expiry + pd.Timedelta(hours=15, minutes=30) - now).total_seconds() / 86400)
    t = days / 365
    q = _option_quote(ts)
    e_lo, e_hi = o.get("entry_low"), o.get("entry_high")
    entry = (e_lo + e_hi) / 2 if e_lo and e_hi else (q["ltp"] if q and q["ltp"] else None)
    ltp = q["ltp"] if q and q["ltp"] else entry
    if not entry or not ltp:
        return {"score": None, "reasons": ([], ["the tip has no premium and no live premium is available"]),
                "take": False}
    iv = implied_vol(ltp, spot, K, t, kind)
    hv = None
    if daily is not None and len(daily) > 30:
        hv = float(np.log(daily["close"]).diff().tail(20).std() * math.sqrt(252))
    if not iv:
        iv = (hv or 0.3) * 1.1
    t_after = max(1e-4, t - min(2, days / 2) / 365)              # some time decay before the targets come
    tg = [x for x in (o.get("targets") or []) if x > entry]
    if not tg:
        tg = [round(entry * 1.4, 1), round(entry * 1.8, 1)]
        cons.append("no premium target given - judged on +40% / +80% of the premium")
    spot_t1 = spot_for_premium(tg[0], K, t_after, iv, kind, spot)
    if o.get("stop") and o.get("stop_on_spot"):
        spot_sl = float(o["stop"])
    elif o.get("stop"):
        spot_sl = spot_for_premium(float(o["stop"]), K, t_after, iv, kind, spot)
    else:
        spot_sl = None
        cons.append("NO stop-loss given - with options you can lose the whole premium")
    if spot_t1 is None:
        return {"score": 2, "reasons": ([], [f"the first target {tg[0]:g} is out of reach for this option before "
                                              "expiry at today's volatility"]), "take": False}
    if spot_sl is None:
        spot_sl = spot - (spot_t1 - spot) if side == "buy" else spot + (spot - spot_t1)
    up_mv = abs(spot_t1 / spot - 1)
    dn_mv = abs(spot_sl / spot - 1)
    if (side == "buy" and spot_sl >= spot) or (side == "sell" and spot_sl <= spot):
        return {"score": 1, "reasons": ([], [f"the stop-loss {spot_sl:,.0f} is already beyond today's price "
                                              f"{spot:,.0f} - the call has failed"]), "take": False}
    # probabilities
    ps = []
    horizon_bars = int(min(days, 5) * 75)
    tm = None
    if bars is not None and len(bars) > 200:
        tm = timemachine.simulate(bars, side, spot, spot_sl, spot_t1, max(10, horizon_bars), lookback=1500)
        if tm:
            ps.append(tm["target"] / 100)
    br = tipcheck.base_rate(daily, up_mv, dn_mv, max(1, int(min(days, 10))), side) if daily is not None else None
    if br:
        win, loss, neither, n = br
        ps.append(win)
    if not ps:
        return {"score": None, "reasons": ([], ["not enough price history to judge"]), "take": False}
    p = float(np.mean(ps))
    pros.append(f"For target 1 ({tg[0]:g}) {sym} must move {up_mv * 100:.1f}% "
                f"{'up' if side == 'buy' else 'down'} to about {spot_t1:,.0f} before the stop {spot_sl:,.0f} "
                f"({dn_mv * 100:.1f}% the other way). History + 10,000 replays: about {p * 100:.0f} in 100 times.")
    # adjustments
    if daily is not None and len(daily) > 200:
        c = daily["close"]
        s50, s200 = c.rolling(50).mean().iloc[-1], c.rolling(200).mean().iloc[-1]
        with_trend = (c.iloc[-1] > s50 > s200) if side == "buy" else (c.iloc[-1] < s50 < s200)
        against = (c.iloc[-1] < s50 < s200) if side == "buy" else (c.iloc[-1] > s50 > s200)
        if with_trend:
            p += 0.04; pros.append("it goes WITH the stock's daily trend")
        elif against:
            p -= 0.06; cons.append("it goes AGAINST the stock's daily trend")
    if hv and iv / hv > 1.35:
        p -= 0.05; cons.append(f"the option is expensive: priced for {iv * 100:.0f}% yearly movement vs "
                               f"{hv * 100:.0f}% really seen lately")
    elif hv and iv / hv < 0.9:
        p += 0.02; pros.append("the option is cheap compared with the stock's real movement")
    if days < 5:
        p -= 0.06; cons.append(f"only {days:.0f} day(s) to expiry - time decay eats the premium fast")
        improved.append("use next month's expiry (less time decay)")
    if e_hi and ltp > e_hi * 1.05:
        p -= 0.05; cons.append(f"the premium is already {ltp:,.1f}, above the tip's range {e_lo:g}-{e_hi:g} - "
                               "you would be chasing")
    if q and q.get("ask") and q.get("bid") and ltp and (q["ask"] - q["bid"]) / ltp > 0.03:
        p -= 0.04; cons.append("wide bid-ask spread - you lose on entry and exit")
    rec = None
    try:
        from .market_views import source_record
        from .tipcheck import TIPS_F
        if source and TIPS_F.exists():
            rows = pd.read_csv(TIPS_F)
            g = rows[(rows["source"] == source) & rows["outcome"].isin(["target", "stop", "expired"])]
            if len(g) >= 10:
                ch = float((g["outcome"] == "target").mean())
                p = 0.7 * p + 0.3 * ch
                (pros if ch >= 0.55 else cons).append(f"this channel's past calls hit target {ch * 100:.0f}% of "
                                                       f"the time ({len(g)} calls)")
            rec = source_record(source)
    except Exception:
        pass
    p = float(np.clip(p, 0.02, 0.95))
    score = int(np.clip(round(p * 10), 1, 10))
    prem_sl = bs(spot_sl, K, t_after, iv, kind)
    loss_lot = (entry - prem_sl) * lot if lot else None
    gain_lot = (tg[0] - entry) * lot if lot else None
    rr = (tg[0] - entry) / max(1e-9, entry - prem_sl)
    if rr < 1:
        cons.append(f"target 1 pays only {rr:.1f}x what the stop costs")
    s = load_settings()
    cap = float(s.get("capital", 45000))
    limit = cap * (0.05 if score >= 9 else 0.03 if score >= 7 else 0.02)
    if loss_lot and loss_lot > limit:
        cons.append(f"one lot loses about ₹{loss_lot:,.0f} at the stop - more than your ₹{limit:,.0f} limit for this "
                    "quality")
    if dn_mv < 0.6 * up_mv:
        improved.append(f"the stop is tight for the target: a spot stop near {spot - np.sign(spot_t1 - spot) * up_mv * spot:,.0f} "
                        "(as far as target 1) is fairer")
    take = score >= 7 and rr >= 1 and (loss_lot is None or loss_lot <= limit)
    return {"score": score, "p": p, "pros": pros, "cons": cons, "improved": improved, "take": take,
            "spot": spot, "spot_t1": spot_t1, "spot_sl": spot_sl, "expiry": expiry, "contract": ts, "lot": lot,
            "entry": entry, "ltp": ltp, "targets": tg, "loss_lot": loss_lot, "gain_lot": gain_lot, "iv": iv,
            "record": rec, "days": days, "side": side}


def reply(o, a, source=""):
    """The structured reply the owner reads (plain text, Telegram)."""
    name = f"{o['symbol']} {pd.Timestamp(a['expiry']).strftime('%b').upper() if a.get('expiry') is not None else ''} " \
           f"{o['strike']:g} {o['kind']}"
    if a.get("score") is None:
        return f"🔍 {name}\n\n⚪ Can't judge yet: {'; '.join(a['reasons'][1])}"
    sc = a["score"]
    head = "🟢 STRONG" if sc >= 8 else "🟢 GOOD" if sc >= 7 else "🟡 AVERAGE" if sc >= 5 else "🔴 WEAK"
    L = [f"🔍 {name}", "", f"🎯 PROBABILITY - {sc}/10 · {head}", ""]
    if a.get("pros"):
        L += ["✅ Why it can work"] + [f"• {x}" for x in a["pros"]] + [""]
    if a.get("cons"):
        L += ["⚠️ Why it can fail"] + [f"• {x}" for x in a["cons"]] + [""]
    lot = a.get("lot")
    L += [f"📋 Plan: buy {a['entry']:,.1f} (live {a['ltp']:,.1f}) · targets {'/'.join(f'{x:g}' for x in a['targets'])} · "
          f"stop {a['spot_sl']:,.0f} SPOT" + (f" · lot {lot}" if lot else "")]
    if a.get("loss_lot") and a.get("gain_lot"):
        L.append(f"💰 Per lot: about ₹{a['gain_lot']:+,.0f} at target 1 / ₹{-a['loss_lot']:,.0f} at the stop")
    if a.get("improved"):
        L += ["", "🛠 Better version"] + [f"• {x}" for x in a["improved"]]
    L.append("")
    L.append("✅ TAKEN - I'm tracking it and will send exit alerts (targets / stop on 75-min closes)." if a["take"]
             else "⏭ Not taken by the system (below 7/10 or outside your risk limit) - your choice.")
    if a.get("record"):
        L.append(f"📒 {a['record']}")
    L.append("Research, not advice.")
    return "\n".join(L)


def take(o, a, source=""):
    """Track a taken tip like the system's own F&O tips (exit alerts via the live engine)."""
    from .live_engine import save_tip
    save_tip({"time": str(pd.Timestamp.now(tz="Asia/Kolkata").tz_localize(None))[:16], "type": "FNO",
              "symbol": o["symbol"], "side": a["side"], "entry": a["spot"], "stop": a["spot_sl"],
              "targets": f"{a['spot_t1']:.2f}", "rank": a["score"], "qty": 1, "contract": a.get("contract") or "",
              "lot": a.get("lot"), "premium": a["entry"], "opt_targets": "/".join(f"{x:.2f}" for x in a["targets"]),
              "spot_sl": a["spot_sl"], "status": "open", "hit": 0,
              "day": str(pd.Timestamp.now(tz="Asia/Kolkata").date()), "setup": "FWD:" + (source or "forwarded")[:30]})


NOTE_WORDS = {"bull": ("bullish", 1), "bear": ("bearish", -1), "buy": ("buying", 1), "sell": ("selling", -1),
              "breakout": ("breakout", 1), "breakdown": ("breakdown", -1), "support": ("support", 1),
              "resistance": ("resistance", -1), "positive": ("positive", 1), "negative": ("negative", -1),
              "rally": ("rally", 1), "crash": ("crash", -1), "profit booking": ("profit booking", -1)}


def note(text, source="", symbols=None):
    """A message that is not a tip: understand what it says, keep it (private), reply in two lines."""
    from .config import PRIVATE
    low = text.lower()
    found = [(w, v) for k, (w, v) in NOTE_WORDS.items() if k in low]
    tone = sum(v for _, v in found)
    mood = "bullish" if tone > 0 else "bearish" if tone < 0 else "neutral / information"
    levels = [x for x in re.findall(r"\b\d{3,6}(?:\.\d+)?\b", text)][:6]
    syms = symbols or []
    try:
        f = PRIVATE / "channel_notes.csv"
        old = pd.read_csv(f) if f.exists() else pd.DataFrame()
        row = {"time": str(pd.Timestamp.now(tz="Asia/Kolkata"))[:16], "source": source, "mood": mood,
               "symbols": " ".join(syms), "levels": " ".join(levels), "text": text.replace("\n", " ")[:400]}
        pd.concat([old, pd.DataFrame([row])], ignore_index=True).tail(5000).to_csv(f, index=False)
    except Exception:
        pass
    what = ", ".join(sorted({w for w, _ in found})) or "no clear direction"
    return (f"📝 Noted from {source or 'this channel'}: {mood} message ({what})" +
            (f" about {', '.join(syms)}" if syms else "") + (f", levels {', '.join(levels)}" if levels else "") +
            ".\nNot a trade tip, so nothing to check - I keep it with this channel's record.")
