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
    return {"close": raw, "stop": round(raw - STOP_ATR * atr * f, 2), "sma5": round(float(s5.iloc[-1]) * f, 2),
            "rsi2": round(float(r2.iloc[-1]), 2), "atr": atr * f}


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
    for s in universe():
        try:
            d = data_prices.load(s)
            if d is None or len(d) < 210:
                continue
            sg = signal(d)
            if sg:
                sg["symbol"] = s
                out.append(sg)
        except Exception:
            continue
    return sorted(out, key=lambda x: x["rsi2"]), "market dipped inside an uptrend - dip-buy day"


def rank(sg):
    """9 for every signal (the strategy's tested ~70% hit rate); 10 when the dip is extreme (RSI2 < 0.5)."""
    return 10 if sg["rsi2"] < 0.5 else 9


def send_evening(day, settings=None):
    """6:40 pm: send each signal as a Normal trade ('Buy tomorrow at open ...'). Returns how many were sent."""
    from .live_engine import already, save_tip, send, tv_link
    s = settings or load_settings()
    cap = float(s.get("capital", 45000))
    sigs, why = scan(day)
    log.info("High-probability scan: %d signal(s) - %s", len(sigs), why)
    n = 0
    for sg in sigs:
        sym = sg["symbol"]
        if already(sym, "NORMAL", str(day)):
            continue
        r = rank(sg)
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
               f"⭐ RANK - {r}/10 · Qty {qty} · tested: {STATS['win_pct']:.0f}% of past trades ended in profit, "
               f"avg {STATS['avg_win_pct']:+.1f}% win / {STATS['avg_loss_pct']:+.1f}% loss, ~4 days\n\n"
               f"{tv_link(sym, daily=True)}")
        send(msg)
        save_tip({"time": str(pd.Timestamp.now(tz='Asia/Kolkata').tz_localize(None))[:16], "type": "NORMAL",
                  "symbol": sym, "side": "buy", "entry": sg["close"], "stop": sg["stop"], "targets": "", "rank": r,
                  "qty": qty, "status": "open", "hit": 0, "day": str(day), "setup": "HP"})
        n += 1
    return n


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
                msgs.append(f"✅ #{r['symbol']} - closed above its 5-day average: SELL at tomorrow's open "
                            f"(now {raw:,.2f}, {chg:+.1f}% from the tip).")
            elif len(since) >= MAX_DAYS:
                t.loc[i, "status"] = "time"
                msgs.append(f"⌛ #{r['symbol']} - 10 trading days without the bounce: sell at tomorrow's open "
                            f"(now {raw:,.2f}, {chg:+.1f}%).")
        t.to_csv(TIPS_F, index=False)
    for m in msgs:
        send(m, label="exit alert")
    return msgs
