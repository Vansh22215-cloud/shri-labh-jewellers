"""HIGH-PROBABILITY DIP BUY (D98) - the owner's main tips: chosen because it wins ~7 of 10 trades on NSE data.

Rule (Connors-style mean reversion, filters chosen on 2013-2023 only, then confirmed on the untouched 2023-11..2026-11):
  BUY at the next open when, at today's close,
    * the stock is in the 300 most-traded NSE stocks (point-in-time list) and closes >= 10% above its 200-day average
    * its 2-day RSI is below 2 (a sharp 2-3 day dip)
    * Nifty is above its 200-day average (market uptrend) AND Nifty's 2-day RSI is below 20 (the market dipped too)
  SELL at the next open after the first close above the 5-day average; safety stop 4 x ATR(14); time limit 10 days.
Test (13 years, top-300 universe, 0.35% charges+slippage per trade): 1,660 trades, 71.9% in profit, average +1.74%
per trade, average win +3.9%, average loss -3.9%, ~4 days held. Untouched last 3 years: 70.1% in profit, +2.06%.
Worst calendar year: 38.5% winners (a crash year) - a high win rate is not a guarantee.
"""
import numpy as np
import pandas as pd

from .config import DATA, get_logger, load_settings

log = get_logger()
STOP_ATR, MAX_DAYS = 4.0, 10
STATS = {"trades": 1660, "win_pct": 71.9, "avg_pct": 1.74, "holdout_win_pct": 70.1, "holdout_avg_pct": 2.06,
         "avg_win_pct": 3.92, "avg_loss_pct": -3.85, "avg_days": 3.6}


# D103: the signal while price is at a fresh bullish ORDER BLOCK (demand zone, touched in the last 3 days)
# 13 years: 347 trades, 80.7% in profit, +3.03% avg (development 80.2%, untouched holdout 82.1%, +3.37%); all 27
# nearby settings 76-86%. The same signal NOT at an order block: 70.3%, +1.49%.
OB_STATS = {"trades": 347, "win_pct": 80.7, "avg_pct": 3.03, "holdout_win_pct": 82.1}


def rsi(c, n=2):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def adjusted(d):
    f = (d["adj_close"] / d["close"]).fillna(1.0) if "adj_close" in d else 1.0
    return pd.DataFrame({"open": d["open"] * f, "high": d["high"] * f, "low": d["low"] * f,
                         "close": d["adj_close"] if "adj_close" in d else d["close"], "raw_close": d["close"]}).dropna()


def market_ok(nifty):
    c = nifty["close"]
    up = bool(c.iloc[-1] > c.rolling(200).mean().iloc[-1])
    r = float(rsi(c).iloc[-1])
    return up and r < 20, up, r


def universe():
    u = pd.read_csv(DATA / "universe_history.csv")
    last = u[u["asof"] == u["asof"].max()]
    return [str(s) for s in last.nsmallest(300, "rank")["symbol"]]


def signal(d):
    """d = one stock's daily bars (raw, with adj_close). -> dict with entry reference, stop, exit level or None."""
    a = adjusted(d)
    if len(a) < 210:
        return None
    c = a["close"]
    s200, s5 = c.rolling(200).mean(), c.rolling(5).mean()
    r2 = rsi(c)
    if not (c.iloc[-1] >= 1.10 * s200.iloc[-1] and r2.iloc[-1] < 2):
        return None
    tr = pd.concat([a["high"] - a["low"], (a["high"] - c.shift()).abs(), (a["low"] - c.shift()).abs()], axis=1).max(axis=1)
    atr = float(tr.rolling(14).mean().iloc[-1])
    raw = float(a["raw_close"].iloc[-1])
    f = raw / float(c.iloc[-1])                          # back to today's (unadjusted) rupee prices
    ob = None
    try:
        from .orderflow import order_block_touches
        t, zl, zh = order_block_touches(a.tail(400))
        k = [i for i in range(len(t) - 3, len(t)) if t[i]]
        if k:
            ob = (round(float(zl[k[-1]]) * f, 2), round(float(zh[k[-1]]) * f, 2))
    except Exception:
        pass
    tier, conf = None, []
    try:   # D105: confirmations from the owner's TradingView indicators decide whether / how strongly to send
        from .confirmations import assess
        tier, conf = assess(a.tail(400), at_order_block=bool(ob))
    except Exception:
        tier, conf = "B", []
    return {"close": raw, "stop": round(raw - STOP_ATR * atr * f, 2), "sma5": round(float(s5.iloc[-1]) * f, 2),
            "rsi2": round(float(r2.iloc[-1]), 2), "atr": atr * f, "ob": ob, "tier": tier, "conf": conf}


def scan(day=None):
    """Evening scan of the 300 most-traded stocks. -> list of signals (best = deepest dip first)."""
    from . import data_prices
    nifty = data_prices.load("NIFTY50")
    if nifty is None or len(nifty) < 210:
        return [], "no Nifty data"
    ok, up, r = market_ok(nifty)
    if not ok:
        return [], (f"market filter: Nifty {'above' if up else 'BELOW'} its 200-day average, 2-day RSI {r:.0f} "
                    "(needs < 20)")
    out = []
    try:   # D101: stocks from forwarded watchlists are scanned too
        from .watchlist import watched
        extra = [x for x in watched() if x not in set(universe())]
    except Exception:
        extra = []
    for s in universe() + extra:
        try:
            d = data_prices.load(s)
            if d is None or len(d) < 210:
                continue
            sg = signal(d)
            if sg and sg.get("tier"):              # D105: weak dips (no fear spike / squeeze on) are not sent
                sg["symbol"] = s
                out.append(sg)
        except Exception:
            continue
    return sorted(out, key=lambda x: (-rank(x), x["rsi2"])), "market dipped inside an uptrend - dip-buy day"


def rank(sg):
    """D105 tiers: A (fear spike + support zone, 79% tested) 10, B (fear spike, 72%) 9, C (zone only, 74%, small
    sample) 8. Signals without a tier are not sent. Older signals without a tier: order block 10, else 9."""
    from .confirmations import TIERS
    if "tier" in sg:
        return TIERS[sg["tier"]]["rank"] if sg["tier"] in TIERS else 0
    return 10 if sg.get("ob") else 9


def send_evening(day, settings=None, sigs=None):
    """6:40 pm: send each signal as a Normal trade ('Buy tomorrow at open ...'). Returns how many were sent."""
    from .live_engine import already, save_tip, send, tv_link
    s = settings or load_settings()
    cap = float(s.get("capital", 45000))
    if sigs is None:
        sigs, why = scan(day)
        log.info("High-probability scan: %d signal(s) - %s", len(sigs), why)
    n = 0
    for sg in sigs:
        sym = sg["symbol"]
        if already(sym, "NORMAL", str(day)):
            continue
        r = rank(sg)
        if r < 1:                                   # D105: untiered (weak) dip - not sent
            continue
        rp = 2.0
        per = max(1e-9, sg["close"] - sg["stop"])
        qty = int(min(cap * rp / 100 / per, cap * 0.25 / sg["close"]))
        if qty < 1:
            continue
        msg = (f"• Normal trade (high-probability dip buy)\n\n"
               f"Buy #{sym} tomorrow at open ≈ {sg['close']:,.2f} 📊\n\n"
               f"SL at {sg['stop']:,.2f} ❗️\n\n"
               f"Target: sell when it closes above its 5-day average (now ≈ {sg['sma5']:,.2f}) - I'll alert you\n\n"
               f"{rp:g}% Risk\n\n"
               + (f"🧱 At a demand zone (order block {sg['ob'][0]:,.2f}-{sg['ob'][1]:,.2f}): big buyers stepped in "
                  f"here before.\n\n" if sg.get("ob") else "")
               + (f"✅ Confirmed by: {', '.join(sg['conf'])}\n\n" if sg.get("conf") else "") +
               f"⭐ RANK - {r}/10 · Qty {qty} · tested: {_tier_line(sg)}, ~4 days\n\n"
               f"{tv_link(sym, daily=True)}")
        send(msg)
        try:
            n += send_option(sg, r, day, s)
        except Exception as e:
            log.warning("high-probability option %s failed: %s", sym, type(e).__name__)
        save_tip({"time": str(pd.Timestamp.now(tz='Asia/Kolkata').tz_localize(None))[:16], "type": "NORMAL",
                  "symbol": sym, "side": "buy", "entry": sg["close"], "stop": sg["stop"], "targets": "", "rank": r,
                  "qty": qty, "status": "open", "hit": 0, "day": str(day), "setup": "HP"})
        n += 1
    return n


def _tier_line(sg):
    from .confirmations import TIERS
    t = TIERS.get(sg.get("tier"))
    if t:
        return f"{t['win']}% of such trades ended in profit, avg {t['avg']:+.1f}% (last 3 years {t['holdout']}%)"
    return (f"{STATS['win_pct']:.0f}% of past trades ended in profit, avg {STATS['avg_win_pct']:+.1f}% win / "
            f"{STATS['avg_loss_pct']:+.1f}% loss")


OPT_STATS = {"trades": 811, "win_pct": 69.7, "avg_pct": 16.9, "holdout_win_pct": 70.3, "holdout_avg_pct": 18.8}


def send_option(sg, r, day, s):
    """F&O version of a signal on an F&O stock: buy a ~2%-in-the-money CALL, monthly expiry >= 15 days away.
    Modelled on 13 years (Black-Scholes on the stock's real path, 1.5% option costs): 70% of trades in profit,
    +17% of the premium on average (holdout 70%, +19%). Only if the loss at the stop fits the rank's risk."""
    from .live_engine import already, fno_underlyings, fmt_fno, option_trade, save_tip, send
    sym = sg["symbol"]
    if sym not in fno_underlyings() or already(sym, "FNO", str(day)):
        return 0
    e = sg["close"]
    c = {"symbol": sym, "side": "buy", "setup": "HP", "entry": e, "stop": sg["stop"],
         "targets": [round(e * 1.02, 2), round(e * 1.04, 2), round(e * 1.06, 2)],
         "why": "high-probability dip buy (sell when the stock closes above its 5-day average)",
         "sl_basis": "daily close"}
    opt = option_trade(c, r, e, pd.Timestamp.now(tz="Asia/Kolkata").tz_localize(None),
                       float(s.get("capital", 45000)), hold_days=4, min_days=15, itm=0.02)
    if not opt:
        return 0
    send(fmt_fno(c, opt, r) + f"\n\n🧪 Tested (modelled): {OPT_STATS['win_pct']:.0f}% of trades in profit, "
                              f"avg {OPT_STATS['avg_pct']:+.0f}% of premium. Buy at tomorrow's open.")
    save_tip({"time": str(pd.Timestamp.now(tz="Asia/Kolkata").tz_localize(None))[:16], "type": "FNO", "symbol": sym,
              "side": "buy", "entry": e, "stop": sg["stop"], "targets": "/".join(f"{x:.2f}" for x in c["targets"]),
              "rank": r, "qty": 1, "contract": opt["contract"], "lot": opt["lot"], "premium": round(opt["premium"], 2),
              "opt_targets": "/".join(f"{x:.2f}" for x in opt["targets"]), "spot_sl": opt["spot_sl"],
              "status": "open", "hit": 0, "day": str(day), "setup": "HP"})
    return 1


def evening_exits(day):
    """6:40 pm: for each open high-probability tip - closed above the 5-day average -> sell at tomorrow's open;
    10 trading days -> time exit. (Safety stop is watched live by the engine.)"""
    from . import data_prices
    from .live_engine import _LOCK, load_tips, send, TIPS_F
    msgs = []
    with _LOCK:
        t = load_tips()
        if not len(t) or "setup" not in t:
            return msgs
        for i, r in t[(t["status"] == "open") & (t["setup"] == "HP")].iterrows():
            what = f"#{r['symbol']}" if r["type"] != "FNO" else f"{r['symbol']} {r.get('contract', '')} (option)"
            d = data_prices.load(r["symbol"])
            if d is None or not len(d):
                continue
            a = adjusted(d)
            since = a[a.index > pd.Timestamp(str(r["day"]))]
            if not len(since):
                continue
            c, s5 = a["close"], a["close"].rolling(5).mean()
            raw = float(a["raw_close"].iloc[-1])
            chg = (raw / float(r["entry"]) - 1) * 100
            if c.iloc[-1] > s5.iloc[-1]:
                t.loc[i, "status"] = "done"
                msgs.append(f"✅ {what} - the stock closed above its 5-day average: SELL at tomorrow's open "
                            f"(now {raw:,.2f}, {chg:+.1f}% from the tip).")
            elif len(since) >= MAX_DAYS:
                t.loc[i, "status"] = "time"
                msgs.append(f"⌛ {what} - 10 trading days without the bounce: sell at tomorrow's open "
                            f"(now {raw:,.2f}, {chg:+.1f}%).")
        t.to_csv(TIPS_F, index=False)
    for m in msgs:
        send(m, label="exit alert")
    return msgs
