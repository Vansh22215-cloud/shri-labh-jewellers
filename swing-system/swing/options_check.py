"""Checks OPTION tips (F&O), e.g. "BOSCHLTD NOV 49000 PE AT 1000-1020, SL 800, TGT 1200/1350, lot 25".

Free data has no NSE option prices, so we work from the tip's own premium:
  1. Live spot price of the underlying (Yahoo).
  2. Implied volatility that makes Black-Scholes match the tip's entry premium (sanity-checked against
     the stock's own recent volatility).
  3. Translate the option stop-loss and targets into STOCK PRICE levels (holding that volatility,
     a couple of days later - time decay works against option buyers every day).
  4. Base rate from the stock's last 5 years: how often did the stock reach the target level before the
     stop level within the holding window? Compare with the win rate needed after charges.
  5. Position risk: one lot's loss at the stop vs YOUR capital (the 1%-risk rule), and gap risk.
SEBI's study (FY22-FY24): about 9 in 10 individual F&O traders lost money.
"""
import math
import re
from datetime import date, timedelta

import numpy as np
import pandas as pd

from . import tipcheck
from .config import DISCLAIMER

MONTHS = {m: i for i, m in enumerate(["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"], 1)}
R = 0.065


def _ncdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def bs(spot, strike, t, vol, kind):
    if t <= 0 or vol <= 0:
        return max(0.0, (spot - strike) if kind == "CE" else (strike - spot))
    d1 = (math.log(spot / strike) + (R + vol * vol / 2) * t) / (vol * math.sqrt(t))
    d2 = d1 - vol * math.sqrt(t)
    if kind == "CE":
        return spot * _ncdf(d1) - strike * math.exp(-R * t) * _ncdf(d2)
    return strike * math.exp(-R * t) * _ncdf(-d2) - spot * _ncdf(-d1)


def implied_vol(price, spot, strike, t, kind):
    lo, hi = 0.01, 3.0
    if bs(spot, strike, t, hi, kind) < price:
        return None
    for _ in range(80):
        mid = (lo + hi) / 2
        if bs(spot, strike, t, mid, kind) > price:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def spot_for_premium(target_prem, strike, t, vol, kind, spot0):
    """Stock price at which the option would be worth target_prem (bisection)."""
    lo, hi = spot0 * 0.5, spot0 * 1.5
    f = lambda s: bs(s, strike, t, vol, kind) - target_prem
    if f(lo) * f(hi) > 0:
        return None
    for _ in range(80):
        mid = (lo + hi) / 2
        if f(lo) * f(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def monthly_expiry(year, month):
    """NSE monthly stock-option expiry: last Tuesday of the month (since Sept 2025; holidays ignored)."""
    d = date(year, month + 1, 1) - timedelta(days=1) if month < 12 else date(year, 12, 31)
    while d.weekday() != 1:
        d -= timedelta(days=1)
    return d


def parse_option(text, eq=None):
    t = text.upper().replace("₹", " ")
    m = re.search(r"\b(\d{2,6}(?:\.\d+)?)\s*(CE|PE|CALL|PUT)\b", t)
    if not m:
        return None
    strike = float(m.group(1))
    kind = {"CALL": "CE", "PUT": "PE"}.get(m.group(2), m.group(2))
    mon = re.search(r"\b(" + "|".join(MONTHS) + r")[A-Z]*\b", t)
    base = tipcheck.parse(text, eq)
    nums = lambda s: [float(x.replace(",", "")) for x in re.findall(r"\d[\d,]*(?:\.\d+)?", s)]
    after = t[m.end():]
    em = re.search(r"\b(?:AT|ABOVE|NEAR|AROUND|BUY|@|CMP|RANGE)\b[^0-9]{0,10}(\d[\d,]*(?:\.\d+)?)(?:\s*(?:-|TO|–)\s*(\d[\d,]*(?:\.\d+)?))?", after)
    e_lo = e_hi = None
    if em:
        a = float(em.group(1).replace(",", ""))
        b = float(em.group(2).replace(",", "")) if em.group(2) else a
        e_lo, e_hi = min(a, b), max(a, b)
    sl = re.search(r"\b(?:SL|STOP ?LOSS|STOPLOSS|STOP)\b[^0-9]{0,6}(\d[\d,]*(?:\.\d+)?)", t)
    tg = re.search(r"\b(?:TGT|TARGETS?|TG)\b[^0-9]{0,6}((?:\d[\d,]*(?:\.\d+)?\s*[-/,&\s]\s*)*\d[\d,]*(?:\.\d+)?)", t)
    lot = re.search(r"\bLOT(?:\s*SIZE)?\b[^0-9]{0,6}(\d+)", t)
    return {"symbol": base["symbol"], "kind": kind, "strike": strike,
            "month": MONTHS[mon.group(1)[:3]] if mon else None,
            "entry_low": e_lo, "entry_high": e_hi, "stop": float(sl.group(1).replace(",", "")) if sl else None,
            "targets": nums(tg.group(1)) if tg else [], "lot": int(lot.group(1)) if lot else None,
            "raw": text.strip()[:500]}


def option_costs(buy_prem_value, sell_prem_value):
    """Zerodha options: Rs 20/order, STT 0.1% on sell premium, NSE 0.03553%, SEBI, stamp 0.003% buy, GST 18%."""
    brok = 40.0
    exch = (buy_prem_value + sell_prem_value) * 0.0003553
    sebi = (buy_prem_value + sell_prem_value) * 10 / 1e7
    return brok + sell_prem_value * 0.001 + exch + sebi + buy_prem_value * 0.00003 + 0.18 * (brok + exch + sebi)


def evaluate_option(o, capital=45000.0, today=None):
    today = today or date.today()
    reasons, flags, d = [], [], {}
    sym = o.get("symbol")
    if not sym:
        return "UNKNOWN", ["I could not find the underlying stock in this option tip."], d
    if not o.get("entry_low"):
        return "UNKNOWN", ["I could not find the option's buy price (premium) in this tip."], d
    df = tipcheck.history(sym)
    spot = tipcheck.live_price(sym) or float(df["close"].iloc[-1])
    prem = (o["entry_low"] + o["entry_high"]) / 2
    month = o.get("month") or today.month
    year = today.year + (1 if month < today.month else 0)
    exp = monthly_expiry(year, month)
    if exp < today:
        exp = monthly_expiry(year + (month == 12), month % 12 + 1)
    try:   # use the ACTUAL expiry from the latest NSE F&O bhavcopy when it is the same month (holidays etc.)
        from .intel_fno import expiry_for
        real = expiry_for(sym)
        if real is not None and real.month == exp.month and real >= today:
            exp = real
    except Exception:
        pass
    days_left = max(1, (exp - today).days)
    t = days_left / 365
    k, kind = o["strike"], o["kind"]
    lot = o.get("lot")
    d.update({"spot": round(spot, 2), "expiry": str(exp), "days_left": days_left, "premium": prem, "lot": lot})
    hv = float(np.log(df["close"]).diff().tail(60).std() * math.sqrt(252))
    iv = implied_vol(prem, spot, k, t, kind)
    intrinsic = max(0.0, (spot - k) if kind == "CE" else (k - spot))
    moneyness = (k / spot - 1) * 100 if kind == "PE" else (spot / k - 1) * 100
    d["hv_pct"] = round(hv * 100, 1)
    if iv is None or iv < 0.05:
        reasons.append(f"The tip's premium {prem:g} doesn't fit today's price {spot:.0f} for a {k:g} {kind} "
                       f"(time value {prem - intrinsic:.0f}) - the tip is stale or the price is wrong.")
        flags.append("AVOID")
        iv = hv
    d["iv_pct"] = round(iv * 100, 1)
    if iv > hv * 1.6:
        reasons.append(f"Premium looks expensive: implied volatility {iv*100:.0f}% vs the stock's recent {hv*100:.0f}%.")
        flags.append("CAUTION")
    side_word = "FALL" if kind == "PE" else "RISE"
    reasons.append(f"This is a bet that {sym} will {side_word}: {kind} {k:g} with the stock at {spot:.0f} "
                   f"({'out of the money' if (kind == 'PE' and k < spot) or (kind == 'CE' and k > spot) else 'in the money'}), "
                   f"{days_left} days to expiry ({exp}).")
    # translate stop & targets into stock levels, two trading days later (time decay)
    t2 = max(1 / 365, t - 2 / 365)
    stop = o.get("stop")
    tgts = [x for x in o.get("targets", []) if x > prem]
    if stop is None:
        reasons.append("No stop-loss given - with options you can lose the whole premium.")
        flags.append("AVOID")
        stop = prem * 0.7
    s_stop = spot_for_premium(stop, k, t2, iv, kind, spot)
    s_t1 = spot_for_premium(tgts[0], k, t2, iv, kind, spot) if tgts else None
    if s_stop and s_t1:
        mv_t = (s_t1 / spot - 1) * 100
        mv_s = (s_stop / spot - 1) * 100
        d.update({"stock_at_target1": round(s_t1), "stock_at_stop": round(s_stop)})
        reasons.append(f"Target 1 ({tgts[0]:g}) needs the stock near {s_t1:.0f} ({mv_t:+.1f}%); the stop ({stop:g}) "
                       f"is hit near {s_stop:.0f} ({mv_s:+.1f}%) - or by time decay alone if the stock does nothing.")
        up, dn = (abs(mv_t) / 100, abs(mv_s) / 100)
        horizon = min(5, max(1, int(days_left * 5 / 7)))
        br = tipcheck.base_rate(df, up, dn, horizon, side="buy" if kind == "CE" else "sell")
        if br:
            win, loss, neither, n = br
            p = win / (win + loss) if (win + loss) else 0
            reward, risk = (tgts[0] - prem), (prem - stop)
            q = lot or max(1, int(500000 / spot))   # lot unknown: NSE lots are worth about Rs 5 lakh
            c = option_costs(prem * q, tgts[0] * q) / q
            need = (risk + c) / (reward + risk)
            d.update({"hist_pct": round(p * 100, 1), "need_pct": round(need * 100, 1),
                      "expected_r": round((p * (reward - c) - (1 - p) * (risk + c)) / risk, 2)})
            reasons.insert(0, f"For the target, {sym} must move {mv_t:+.1f}% before it moves {mv_s:+.1f}%, within "
                              f"{horizon} trading days. In its last 5 years that happened only {p*100:.0f} times in 100 - "
                              f"it needs {need*100:.0f} to make money after charges." if p < need else
                              f"For the target, {sym} must move {mv_t:+.1f}% before it moves {mv_s:+.1f}%, within "
                              f"{horizon} trading days. In its last 5 years that happened {p*100:.0f} times in 100 "
                              f"(needs {need*100:.0f}).")
            if p < need - 0.05:
                flags.append("AVOID")
            elif p < need + 0.05:
                flags.append("CAUTION")
    # position risk vs YOUR capital
    if lot:
        cost = prem * lot
        loss_at_sl = (prem - stop) * lot
        d.update({"capital_needed": round(cost), "loss_at_stop": round(loss_at_sl)})
        reasons.append(f"One lot ({lot}) costs about Rs {cost:,.0f} = {cost / capital * 100:.0f}% of your capital; "
                       f"loss at the stop about Rs {loss_at_sl:,.0f} = {loss_at_sl / capital * 100:.1f}% "
                       f"(your rule is 1% = Rs {capital * 0.01:,.0f}). A gap can lose far more, up to Rs {cost:,.0f}.")
        if loss_at_sl > capital * 0.02:
            flags.append("AVOID")
    reasons.append("SEBI found about 9 in 10 individual F&O traders lost money (FY22-FY24).")
    verdict = "AVOID" if "AVOID" in flags else ("RISKY" if flags else "RISKY")   # option buying is never 'GOOD' by default
    return verdict, reasons, d


def format_option_reply(o, verdict, reasons, d, source=""):
    """Same clear card as every other forwarded tip."""
    from . import reply_card as rc
    said = next((r for r in reasons if r.startswith("This is a bet")), None)
    info = [r for r in reasons if r.startswith(("Target 1", "One lot"))]
    cons = [r for r in reasons if r not in info and r != said]
    now = (f"Stock {d['spot']}, option premium {d.get('premium')}. Option price implies {d.get('iv_pct')}% yearly "
           f"movement vs {d.get('hv_pct')}% actually seen lately" + (" (expensive)." if (d.get("iv_pct") or 0) >
                                                                        1.2 * (d.get("hv_pct") or 1e9) else ".")) \
        if d.get("spot") else None
    return rc.build(verdict, f"{o.get('symbol')} {o.get('strike'):g} {o.get('kind')} · option tip (expiry ~{d.get('expiry', '?')})",
                    said=said, now=now, pros=[], cons=cons, info=info, p=d.get("hist_pct"), need=d.get("need_pct"),
                    source=source, raw=o.get("raw"),
                    missing=reasons[0] if verdict == "UNKNOWN" and reasons else None)
