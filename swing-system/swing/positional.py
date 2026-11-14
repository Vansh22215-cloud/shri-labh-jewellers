"""POSITIONAL trades (D104) - the Rolling Candle Profile BUY signal (exact port, swing/rolling_profile.py) on daily
bars, only for stocks within 10% of their 52-week high. Held until the indicator's own SELL signal (I alert), a
5 x ATR safety stop (watched live), or 60 trading days.

Test (validation/rolling_profile_positional.py): 13 years, point-in-time top-300, next-open entry, 0.35% costs:
6,340 trades, 45% in profit, average +5.4% a trade (wins +22.6%, losses -8.9%), ~43 days held; untouched last 3 years
43% / +3.2%. Buying a random top-300 stock for the same time made +2.7% (+2.1% last 3 years) - so the real edge is
about +1 to +2.5% a trade, from a few big winners. Fewer winners than the dip-buy (72%): ranked 6/10, risk 1%.
"""
import pandas as pd

from .config import get_logger, load_settings

log = get_logger()
STATS = {"trades": 6340, "win_pct": 45.3, "avg_pct": 5.37, "avg_win_pct": 22.6, "avg_loss_pct": -8.9,
         "holdout_win_pct": 43.2, "holdout_avg_pct": 3.16, "days": 43}
STOP_ATR, MAX_DAYS, NEAR_HIGH, RANK, RISK_PCT = 5.0, 60, 0.90, 6, 1.0


def _adjusted(sym):
    from . import data_prices
    from .high_prob import adjusted
    d = data_prices.load(sym)
    if d is None or len(d) < 300:
        return None
    a = adjusted(d)
    a["volume"] = d["volume"].reindex(a.index).fillna(0)
    return a


def signal(a):
    """a = adjusted daily bars (+ raw_close). -> dict for a BUY on the LAST bar, or None."""
    from .rolling_profile import signals
    s = signals(a.tail(400)[["open", "high", "low", "close", "volume"]], "price")
    if not bool(s["buy"].iloc[-1]):
        return None
    c = a["close"]
    if c.iloc[-1] < NEAR_HIGH * c.tail(250).max():
        return None
    tr = pd.concat([a["high"] - a["low"], (a["high"] - c.shift()).abs(), (a["low"] - c.shift()).abs()], axis=1).max(axis=1)
    raw = float(a["raw_close"].iloc[-1])
    f = raw / float(c.iloc[-1])
    atr = float(tr.rolling(14).mean().iloc[-1]) * f
    return {"close": raw, "stop": round(raw - STOP_ATR * atr, 2), "anchor": round(float(s["anchor"].iloc[-1]) * f, 2),
            "bands": int(s["green"].iloc[-1]), "from_high_pct": round((c.iloc[-1] / c.tail(250).max() - 1) * 100, 1)}


def sell_now(a):
    from .rolling_profile import signals
    return bool(signals(a.tail(400)[["open", "high", "low", "close", "volume"]], "price")["sell"].iloc[-1])


def scan():
    from .high_prob import universe
    try:
        from .watchlist import watched
        extra = watched()
    except Exception:
        extra = []
    try:   # stocks only - ETFs / funds (NIFTYBEES, GOLDBEES...) are not on the NSE equity list
        from .tipcheck import equity_list
        eq = set(equity_list()["SYMBOL"].astype(str))
    except Exception:
        eq = None
    out = []
    for s in list(dict.fromkeys(universe() + extra)):
        if eq is not None and s not in eq:
            continue
        try:
            a = _adjusted(s)
            sg = signal(a) if a is not None else None
            if sg:
                out.append(dict(sg, symbol=s))
        except Exception:
            continue
    return sorted(out, key=lambda x: (-x["bands"], -x["from_high_pct"]))


def send_evening(day, settings=None, sigs=None):
    """Evening: new positional BUYs as 'Positional trade' tips (at most `positional_max_new` a day and
    `positional_max_open` open at once - the capital is small)."""
    from .live_engine import already, load_tips, save_tip, send, tv_link
    s = settings or load_settings()
    if not s.get("positional_tips", True):
        return 0
    cap = float(s.get("capital", 45000))
    sigs = scan() if sigs is None else sigs
    t = load_tips()
    open_n = int(((t["status"] == "open") & (t.get("setup", "") == "RCP")).sum()) if len(t) and "setup" in t else 0
    mo, mn = int(s.get("positional_max_open", 0) or 0), int(s.get("positional_max_new", 0) or 0)   # 0 = no limit
    room = max(0, mo - open_n) if mo else len(sigs)
    log.info("Positional scan: %d signal(s), room for %d", len(sigs), room)
    n = 0
    for sg in sigs[:min(room, mn) if mn else room]:
        sym = sg["symbol"]
        if already(sym, "NORMAL", str(day)):
            continue
        per = max(1e-9, sg["close"] - sg["stop"])
        qty = int(min(cap * RISK_PCT / 100 / per, cap * 0.25 / sg["close"]))
        if qty < 1:
            continue
        send(f"• Positional trade (Rolling Candle Profile)\n\n"
             f"Buy #{sym} tomorrow at open ≈ {sg['close']:,.2f} 📊\n\n"
             f"SL at {sg['stop']:,.2f} ❗️ (wide safety stop - the real exit is the SELL signal)\n\n"
             f"Target: hold until the indicator's SELL signal - I'll alert you (max {MAX_DAYS} trading days)\n\n"
             f"{RISK_PCT:g}% Risk\n\n"
             f"⭐ RANK - {RANK}/10 · Qty {qty} · {sg['bands']} of 12 bands buying, {sg['from_high_pct']:+.0f}% from the "
             f"52-week high. Tested: {STATS['win_pct']:.0f}% of trades in profit - fewer winners but big ones "
             f"(avg win {STATS['avg_win_pct']:+.0f}% / loss {STATS['avg_loss_pct']:+.0f}%), avg {STATS['avg_pct']:+.1f}% "
             f"a trade, ~{STATS['days']} days. Expect several small losses before a big winner.\n\n"
             f"{tv_link(sym, daily=True)}")
        save_tip({"time": str(pd.Timestamp.now(tz='Asia/Kolkata').tz_localize(None))[:16], "type": "NORMAL",
                  "symbol": sym, "side": "buy", "entry": sg["close"], "stop": sg["stop"], "targets": "", "rank": RANK,
                  "qty": qty, "status": "open", "hit": 0, "day": str(day), "setup": "RCP"})
        n += 1
    return n


def evening_exits(day):
    """Evening: open positional tips - the indicator's SELL signal or 60 trading days -> sell at tomorrow's open."""
    from .live_engine import _LOCK, TIPS_F, load_tips, send
    msgs = []
    with _LOCK:
        t = load_tips()
        if not len(t) or "setup" not in t:
            return msgs
        for i, r in t[(t["status"] == "open") & (t["setup"] == "RCP")].iterrows():
            a = _adjusted(r["symbol"])
            if a is None:
                continue
            since = a[a.index > pd.Timestamp(str(r["day"]))]
            if not len(since):
                continue
            raw = float(a["raw_close"].iloc[-1])
            chg = (raw / float(r["entry"]) - 1) * 100
            if sell_now(a):
                t.loc[i, "status"] = "done"
                msgs.append(f"🔻 #{r['symbol']} (positional) - the Rolling Candle Profile gave its SELL signal: "
                            f"SELL at tomorrow's open (now {raw:,.2f}, {chg:+.1f}% from the tip).")
            elif len(since) >= MAX_DAYS:
                t.loc[i, "status"] = "time"
                msgs.append(f"⌛ #{r['symbol']} (positional) - {MAX_DAYS} trading days: sell at tomorrow's open "
                            f"(now {raw:,.2f}, {chg:+.1f}%).")
        t.to_csv(TIPS_F, index=False)
    for m in msgs:
        send(m, label="exit alert")
    return msgs
