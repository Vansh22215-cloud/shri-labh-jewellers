"""BREAKOUT trades (D118, owner 17 Nov: "find other smarter and best ways of finding trades").

Two published breakout methods that passed the pre-registered test in validation/new_strategies_research.py
(13 years, point-in-time top-300 incl. delisted stocks, next-open entry, gap-adjusted stops, 0.35% costs):
  BRK52  52-week-high breakout on volume (O'Neil / Darvas): close above the highest high of the prior 250 days,
         volume >= 1.5x its 50-day average, above the 200-day average.
  VCP    volatility-contraction breakout: last 20 days' range <= 12% of price, within 5% of the 52-week high,
         close > 50d > 200d average, close above the prior 20-day high on >= 1.5x volume.
Exit: the first close below the 50-day average -> sell at the next open (alert); 3 ATR safety stop (watched live);
60 trading days at most.
Combined (one trade per stock at a time): 5,434 trades, 38% in profit, avg win +19.5% / loss -7.5%, +2.85% a trade
after costs; untouched last 3 years +2.03% (1,262 trades); 5 losing years of 14. FEW winners, BIG winners.
"""
import pandas as pd

from .config import get_logger, load_settings

log = get_logger()
STATS = {"trades": 5434, "win_pct": 38.2, "avg_pct": 2.85, "avg_win_pct": 19.5, "avg_loss_pct": -7.5,
         "holdout_avg_pct": 2.03, "days": 32}
STOP_ATR, MAX_DAYS, RANK, RISK_PCT, SETUP = 3.0, 60, 6, 1.0, "BRK"


def signal(a):
    """a = adjusted daily bars with volume and raw_close. -> dict for a breakout on the LAST bar, or None."""
    if a is None or len(a) < 260:
        return None
    c, h, l, v = a["close"], a["high"], a["low"], a["volume"]
    s50, s200, v50 = c.rolling(50).mean(), c.rolling(200).mean(), v.rolling(50).mean().shift(1)
    i = -1
    vol_ok = v.iloc[i] >= 1.5 * v50.iloc[i]
    brk52 = c.iloc[i] > h.shift(1).rolling(250).max().iloc[i] and vol_ok and c.iloc[i] > s200.iloc[i]
    rng20 = (h.rolling(20).max().shift(1).iloc[i] - l.rolling(20).min().shift(1).iloc[i]) / c.iloc[i]
    vcp = (rng20 <= 0.12 and c.iloc[i] >= 0.95 * h.rolling(250).max().iloc[i] and c.iloc[i] > s50.iloc[i]
           and s50.iloc[i] > s200.iloc[i] and c.iloc[i] > h.shift(1).rolling(20).max().iloc[i] and vol_ok)
    if not (brk52 or vcp):
        return None
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    raw = float(a["raw_close"].iloc[i])
    f = raw / float(c.iloc[i])
    atr = float(tr.rolling(14).mean().iloc[i]) * f
    why = " + ".join(x for x, ok in (("52-week-high breakout on volume", brk52),
                                     ("tight-range (VCP) breakout", vcp)) if ok)
    return {"close": raw, "stop": round(raw - STOP_ATR * atr, 2), "why": why, "both": bool(brk52 and vcp),
            "vol_x": round(float(v.iloc[i] / v50.iloc[i]), 1), "exit_level": round(float(s50.iloc[i]) * f, 2)}


def exit_now(a):
    c = a["close"]
    return bool(c.iloc[-1] < c.rolling(50).mean().iloc[-1])


def scan():
    from .high_prob import universe
    from .positional import _adjusted
    try:
        from .tipcheck import equity_list
        eq = set(equity_list()["SYMBOL"].astype(str))
    except Exception:
        eq = None
    out = []
    for s in universe():
        if eq is not None and s not in eq:
            continue                                  # stocks only (no ETFs / funds)
        try:
            sg = signal(_adjusted(s))
            if sg:
                out.append(dict(sg, symbol=s))
        except Exception:
            continue
    return sorted(out, key=lambda x: (-x["both"], -x["vol_x"]))


def send_evening(day, settings=None, sigs=None):
    from .live_engine import already, issue_tip, tv_link
    from . import safety
    s = settings or load_settings()
    if not s.get("breakout_tips", True):
        return 0
    try:
        from .autopilot import rules as _ap
        if _ap().get("brk_paused"):
            log.info("Breakout: paused by the autopilot (live record)")
            return 0
    except Exception:
        pass
    sigs = scan() if sigs is None else sigs
    log.info("Breakout scan: %d signal(s)", len(sigs))
    n = 0
    for sg in sigs:
        sym = sg["symbol"]
        if already(sym, "NORMAL", str(day)):
            continue
        qty = safety.size(sg["close"], sg["stop"], s, RISK_PCT)
        if qty < 1:
            continue
        msg = (f"• Breakout trade ({sg['why']})\n\n"
               f"Buy #{sym} at the next market open ≈ {sg['close']:,.2f} 📊\n\n"
               f"SL at {sg['stop']:,.2f} ❗️ (safety stop)\n\n"
               f"Exit: the first daily close below its 50-day average (now ≈ {sg['exit_level']:,.2f}) - I'll alert you "
               f"(max {MAX_DAYS} trading days)\n\n"
               f"{RISK_PCT:g}% Risk\n\n"
               f"⭐ RANK - {RANK}/10 · Qty {qty} · volume {sg['vol_x']:g}x normal. Tested 13 years: only "
               f"{STATS['win_pct']:.0f}% of trades win, but winners average {STATS['avg_win_pct']:+.0f}% vs losers "
               f"{STATS['avg_loss_pct']:+.0f}% - avg {STATS['avg_pct']:+.1f}% a trade, ~{STATS['days']} days. Expect "
               f"several small losses before a big winner.\n\n{tv_link(sym, daily=True)}")
        if issue_tip({"time": str(pd.Timestamp.now(tz='Asia/Kolkata').tz_localize(None))[:16], "type": "NORMAL",
                      "symbol": sym, "side": "buy", "entry": sg["close"], "stop": sg["stop"], "targets": "",
                      "rank": RANK, "qty": qty, "status": "open", "hit": 0, "day": str(day), "setup": SETUP}, msg, s):
            n += 1
    return n


def evening_exits(day):
    """Evening: open breakout tips - close below the 50-day average or 60 trading days -> sell at the next open."""
    from .live_engine import _LOCK, load_tips, write_tips, send
    from .positional import _adjusted
    from .autopilot import close_tip
    msgs = []
    with _LOCK:
        t = load_tips()
        if not len(t) or "setup" not in t:
            return msgs
        for i, r in t[(t["status"] == "open") & (t["setup"] == SETUP)].iterrows():
            a = _adjusted(r["symbol"])
            if a is None:
                continue
            since = a[a.index > pd.Timestamp(str(r["day"]))]
            if not len(since):
                continue
            raw = float(a["raw_close"].iloc[-1])
            chg = (raw / float(r["entry"]) - 1) * 100
            quiet = str(r.get("taken", "")).lower() == "no"
            if exit_now(a):
                close_tip(t, i, "done", raw)
                if not quiet:
                    msgs.append(f"🔻 #{r['symbol']} (breakout) - closed below its 50-day average: SELL at the next "
                                f"market open (now {raw:,.2f}, {chg:+.1f}% from the tip).")
            elif len(since) >= MAX_DAYS:
                close_tip(t, i, "time", raw)
                if not quiet:
                    msgs.append(f"⌛ #{r['symbol']} (breakout) - {MAX_DAYS} trading days: sell at the next market "
                                f"open (now {raw:,.2f}, {chg:+.1f}%).")
        write_tips(t)
    for m in msgs:
        send(m, label="exit alert")
    return msgs
