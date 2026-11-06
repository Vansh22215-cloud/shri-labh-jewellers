"""Hourly TIPS UPDATE: where every tip the owner was given stands right now (replaces the Nifty pulse line).

Covers, each with price now, gain/loss, distance to stop and target, and one plain "what to do":
  1. the system's own tips (evening message; journal/tips.csv, kind 'tip', pending or open)
  2. "BUY ... tomorrow" signals sent by the hourly scans (journal/scan_signals.csv) until the evening list
     confirms or drops them
  3. every tip the owner forwarded to the bot (private file), stocks and index/forex/gold/crypto calls, grouped by
     the channel it came from; finished ones are shown once on the day they finish
"""
import html

import pandas as pd

from .config import JOURNAL, get_logger

log = get_logger()
E = html.escape
SIGNALS_F = JOURNAL / "scan_signals.csv"


def record_signals(day, plans):
    """Remember the hourly-scan buy signals that were sent, so they are followed up every hour."""
    if not plans:
        return
    rows = [{"date": str(day), "symbol": p["symbol"], "entry_low": p["entry_low"], "entry_high": p["entry_high"],
             "stop": p["stop"], "target1": p["target1"], "qty": p.get("qty")} for p in plans]
    old = pd.read_csv(SIGNALS_F) if SIGNALS_F.exists() else pd.DataFrame()
    new = pd.concat([old, pd.DataFrame(rows)], ignore_index=True).drop_duplicates(["date", "symbol"], keep="first")
    new.to_csv(SIGNALS_F, index=False)


def _f(x):
    x = float(x)
    return f"{x:,.5f}".rstrip("0").rstrip(".") if abs(x) < 10 else f"{x:,.2f}" if abs(x) < 10000 else f"{x:,.0f}"


def judge(side, ltp, entry, stop, target, waiting=False, zone=None, hi=None, lo=None):
    """-> (icon, status words, what to do). hi/lo = today's high/low so far (a level touched today counts)."""
    buy = side != "sell"
    if waiting:
        lo_z, hi_z = zone or (entry, entry)
        if lo_z <= ltp <= hi_z:
            return "🟢", "inside the buy zone now", "Can be bought now (only at this price range)."
        if (ltp > hi_z) == buy:
            return "⏳", f"{abs(ltp / (hi_z if buy else lo_z) - 1) * 100:.1f}% past the buy zone", \
                "Don't chase - wait; skip it if it doesn't come back."
        return "⏳", f"{abs(ltp / (lo_z if buy else hi_z) - 1) * 100:.1f}% away from the buy zone", "Wait for the buy zone."
    hit_t = (hi is not None and ((hi >= target) if buy else (lo <= target))) or ((ltp >= target) if buy else (ltp <= target))
    hit_s = (lo is not None and ((lo <= stop) if buy else (hi >= stop))) or ((ltp <= stop) if buy else (ltp >= stop))
    if hit_s:
        return "❌", "stop-loss hit", "Exit if you hold it - the tip has failed."
    if hit_t:
        return "🎯", "target reached", "Book profit (at least part), or move the stop up to protect it."
    to_stop = abs(ltp / stop - 1) * 100
    to_tgt = abs(target / ltp - 1) * 100
    gain = (ltp / entry - 1) * 100 * (1 if buy else -1)
    if to_stop < 1.5:
        return "⚠️", f"close to the stop ({to_stop:.1f}% away)", "Be ready to exit at the stop - no averaging down."
    if to_tgt < 1.5:
        return "🎯", f"close to the target ({to_tgt:.1f}% away)", "Get ready to book profit."
    return ("🟢" if gain >= 0 else "🔴"), ("in profit" if gain >= 0 else "in loss"), "Hold - nothing to do."


def _line(name, origin, side, ltp, entry, stop, target, icon, status, todo, qty=None):
    buy = side != "sell"
    gain = (ltp / entry - 1) * 100 * (1 if buy else -1)
    pnl = f" · ₹{(ltp - entry) * (1 if buy else -1) * qty:+,.0f} on {int(qty)}" if qty and qty == qty else ""
    return (f"{icon} <b>{E(name)}</b> <i>({E(origin)})</i> - {E(status)}\n"
            f"<code>Now {_f(ltp)} ({gain:+.1f}% vs entry {_f(entry)}){pnl}\n"
            f"Stop {_f(stop)} ({abs(ltp / stop - 1) * 100:.1f}% away) · Target {_f(target)} ({abs(target / ltp - 1) * 100:.1f}% away)</code>\n"
            f"👉 {E(todo)}")


def _wait_line(name, origin, side, ltp, zone, stop, target, icon, status, todo):
    return (f"{icon} <b>{E(name)}</b> <i>({E(origin)})</i> - {E(status)}\n"
            f"<code>Now {_f(ltp)} · buy zone {_f(zone[0])}-{_f(zone[1])} · stop {_f(stop)} · target {_f(target)}</code>\n"
            f"👉 {E(todo)}")


def system_tips(snap, tips):
    out = []
    t = tips[(tips["kind"] == "tip") & tips["status"].isin(["pending", "open"])]
    for _, r in t.iterrows():
        s = r["symbol"]
        if s not in snap["close"]:
            continue
        ltp = float(snap["close"][s])
        hi, lo = float(snap["high"].get(s, ltp)), float(snap["low"].get(s, ltp))
        origin = f"system tip {pd.Timestamp(r['date']):%d %b}"
        zone = (float(r["entry_low"]), float(r["entry_high"]))
        if r["status"] == "pending":
            out.append(_wait_line(s, origin, "buy", ltp, zone, r["stop"], r["target1"],
                                  *judge("buy", ltp, None, None, None, waiting=True, zone=zone)))
        else:
            entry = float(r["entry_price"]) if pd.notna(r.get("entry_price")) else sum(zone) / 2
            out.append(_line(s, origin, "buy", ltp, entry, float(r["stop"]), float(r["target1"]),
                             *judge("buy", ltp, entry, float(r["stop"]), float(r["target1"]), hi=hi, lo=lo),
                             qty=r.get("qty")))
    return out


def scan_signals(snap, tips, today):
    if not SIGNALS_F.exists():
        return []
    sg = pd.read_csv(SIGNALS_F)
    sg = sg[pd.to_datetime(sg["date"]) >= pd.Timestamp(today) - pd.Timedelta(days=1)]
    confirmed = set(tips.loc[tips["kind"] == "tip", "symbol"] + " " + tips.loc[tips["kind"] == "tip", "date"].astype(str))
    out = []
    for _, r in sg.drop_duplicates("symbol", keep="last").iterrows():
        s = r["symbol"]
        if s not in snap["close"]:
            continue
        if f"{s} {r['date']}" in confirmed:
            continue                     # it became an evening tip: shown with the system tips
        ltp = float(snap["close"][s])
        zone = (float(r["entry_low"]), float(r["entry_high"]))
        if str(r["date"]) < str(today):
            out.append(f"➖ <b>{E(s)}</b> <i>(scan signal {pd.Timestamp(r['date']):%d %b})</i> - it did NOT make the "
                       f"evening list, so ignore it.\n<code>Now {_f(ltp)}</code>")
            continue
        icon, status, todo = judge("buy", ltp, None, None, None, waiting=True, zone=zone)
        out.append(_wait_line(s, f"scan signal {pd.Timestamp(r['date']):%d %b}", "buy", ltp, zone, r["stop"],
                              r["target1"], icon, status, "Provisional - the 6:40 pm list confirms it. " + todo))
    return out


def forwarded(snap, today):
    from .tipcheck import TIPS_F
    if not TIPS_F.exists():
        return {}
    df = pd.read_csv(TIPS_F)
    groups = {}
    live = df["outcome"].isin(["open", "waiting entry"])
    done_today = df["outcome"].isin(["target", "stop", "expired", "never filled"]) & \
        (df.get("resolved", pd.Series([""] * len(df))).astype(str).str[:10] == str(today))
    for _, r in df[live | done_today].iterrows():
        if pd.isna(r.get("entry")) or pd.isna(r.get("stop")) or pd.isna(r.get("target")):
            continue
        name, side = str(r["symbol"]), str(r.get("side") or "buy")
        tk = r.get("ticker") if isinstance(r.get("ticker"), str) and r.get("ticker") else None
        ltp = None
        if tk is None and name in snap["close"]:
            ltp = float(snap["close"][name])
            hi, lo = float(snap["high"].get(name, ltp)), float(snap["low"].get(name, ltp))
        elif tk:
            try:
                from .market_views import hourly
                h = hourly(tk, period="5d")
                off = float(r.get("offset") or 0) if pd.notna(r.get("offset")) else 0.0
                ltp, hi, lo = float(h["close"].iloc[-1]) + off, None, None
            except Exception:
                ltp = None
        if ltp is None:
            continue
        origin = f"forwarded {pd.Timestamp(str(r['checked'])[:10]):%d %b}, my verdict: " + \
            {"GOOD": "worth considering", "RISKY": "risky", "AVOID": "skip", "NEUTRAL": "coin flip"}.get(
                str(r.get("verdict")), str(r.get("verdict")).lower())
        src = str(r.get("source") or "forwarded") if pd.notna(r.get("source")) else "forwarded"
        if r["outcome"] in ("target", "stop", "expired", "never filled"):
            word = {"target": "✅ RIGHT - target reached", "stop": "❌ WRONG - stop hit",
                    "expired": "⌛ ran out of time", "never filled": "⌛ never reached its entry"}[r["outcome"]]
            groups.setdefault(src, []).append(f"{word}: <b>{E(name)}</b> <i>({E(origin)})</i>\n<code>Now {_f(ltp)}</code>")
            continue
        entry, stop, target = float(r["entry"]), float(r["stop"]), float(r["target"])
        if r["outcome"] == "waiting entry":
            groups.setdefault(src, []).append(_wait_line(name, origin, side, ltp, (entry, entry), stop, target,
                                                         *judge(side, ltp, None, None, None, waiting=True, zone=(entry, entry))))
        else:
            icon, status, todo = judge(side, ltp, entry, stop, target, hi=hi, lo=lo)
            groups.setdefault(src, []).append(_line(name, origin, side, ltp, entry, stop, target, icon, status,
                                                    "If you took it: " + todo[0].lower() + todo[1:]))
    return groups


def symbols_needed():
    """Stocks whose live price the hourly scan must fetch for this update."""
    from . import journal
    from .tipcheck import TIPS_F
    syms = set()
    try:
        t = journal.load_tips()
        syms |= set(t.loc[(t["kind"] == "tip") & t["status"].isin(["pending", "open"]), "symbol"])
    except Exception:
        pass
    if SIGNALS_F.exists():
        sg = pd.read_csv(SIGNALS_F)
        syms |= set(sg.loc[pd.to_datetime(sg["date"]) >= pd.Timestamp.today().normalize() - pd.Timedelta(days=1), "symbol"])
    if TIPS_F.exists():
        df = pd.read_csv(TIPS_F)
        m = df["outcome"].isin(["open", "waiting entry"])
        if "ticker" in df:
            m &= df["ticker"].isna() | (df["ticker"].astype(str) == "")
        syms |= set(df.loc[m, "symbol"].dropna().astype(str))
    return sorted(syms)


def message(snap, tips, ts, today=None):
    today = today or pd.Timestamp(ts).date()
    blocks = [f"⏱ <b>TIPS UPDATE</b> · {pd.Timestamp(ts):%I:%M %p}"]
    st = system_tips(snap, tips)
    if st:
        blocks.append("🤖 <b>System tips</b>\n" + "\n\n".join(st))
    sg = scan_signals(snap, tips, today)
    if sg:
        blocks.append("🔔 <b>Today's scan signals</b>\n" + "\n\n".join(sg))
    fw = forwarded(snap, today)
    for src, lines in fw.items():
        blocks.append(f"📨 <b>Forwarded from {E(src)}</b>\n" + "\n\n".join(lines))
    if len(blocks) == 1:
        blocks.append("No open tips right now. Forward any tip to the bot and it will appear here every hour.")
    n = len(st) + len(sg) + sum(len(v) for v in fw.values())
    blocks.append(f"<i>{n} tip(s) followed. Research, not advice - you decide and place every order yourself.</i>")
    return "\n\n⁣".join(blocks)
