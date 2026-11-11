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


RESULT = {"target": "✅ RIGHT - reached the target", "stop": "❌ WRONG - hit the stop", "expired": "⌛ ran out of time",
          "never filled": "⌛ never reached its entry", "closed": "closed"}
VERDICT_WORD = {"GOOD": "worth considering", "RISKY": "risky", "AVOID": "skip", "NEUTRAL": "coin flip",
                "UNKNOWN": "couldn't judge"}
DAYS_KEPT = 60          # every tip from the last 60 days is listed


def _since(ltp, then, side="buy"):
    try:
        then = float(then)
    except (TypeError, ValueError):
        return ""
    if not then or then != then:
        return ""
    ch = (ltp / then - 1) * 100 * (1 if side != "sell" else -1)
    return f" ({ch:+.1f}% since then, was {_f(then)})"


def system_tips(snap, tips, today=None):
    """All system tips of the last 60 days: open/pending in full, finished ones as one result line."""
    out = []
    t = tips[tips["kind"] == "tip"].copy()
    if not len(t):
        return out
    t = t[pd.to_datetime(t["date"]) >= pd.Timestamp.today().normalize() - pd.Timedelta(days=DAYS_KEPT)]
    for _, r in t.sort_values("date", ascending=False).iterrows():
        s = r["symbol"]
        origin = f"system tip {pd.Timestamp(r['date']):%d %b}"
        ltp = float(snap["close"][s]) if s in snap["close"] else None
        zone = (float(r["entry_low"]), float(r["entry_high"]))
        if r["status"] not in ("pending", "open"):
            res = str(r.get("exit_reason") or r["status"])
            pnl = f" · result ₹{float(r['pnl']):+,.0f}" if pd.notna(r.get("pnl")) else ""
            out.append(f"🏁 <b>{E(s)}</b> <i>({E(origin)})</i> - finished: {E(res)}{pnl}"
                       + (f"\n<code>Now {_f(ltp)}</code>" if ltp else ""))
            continue
        if ltp is None:
            out.append(f"❔ <b>{E(s)}</b> <i>({E(origin)})</i> - no live price this hour (data source); shown again next hour.")
            continue
        hi, lo = float(snap["high"].get(s, ltp)), float(snap["low"].get(s, ltp))
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
    from .journal import tips_start
    if tips_start():
        sg = sg[sg["date"].astype(str) >= tips_start()]
    confirmed = set(tips.loc[tips["kind"] == "tip", "symbol"] + " " + tips.loc[tips["kind"] == "tip", "date"].astype(str))
    out = []
    for _, r in sg.drop_duplicates("symbol", keep="last").iterrows():
        s = r["symbol"]
        if f"{s} {r['date']}" in confirmed:
            continue                     # it became an evening tip: shown with the system tips
        if s not in snap["close"]:
            out.append(f"❔ <b>{E(s)}</b> <i>(scan signal {pd.Timestamp(r['date']):%d %b})</i> - no live price this hour.")
            continue
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


def _market_price(tk, offset, cache):
    if tk not in cache:
        try:
            from .market_views import hourly
            h = hourly(tk, period="5d")
            cache[tk] = float(h["close"].iloc[-1]) if h is not None and len(h) else None
        except Exception:
            cache[tk] = None
    return cache[tk] + offset if cache[tk] is not None else None


def forwarded(snap, today, since=None):
    """EVERY forwarded tip of the last 60 days, grouped by channel, newest first:
    tracked ones in full; finished ones with their result; ones that could not be tracked (skip verdict, option,
    missing stop/target) with the price change since forwarding. 🆕 = forwarded since the last update."""
    from .tipcheck import TIPS_F
    if not TIPS_F.exists():
        return {}
    df = pd.read_csv(TIPS_F)
    if not len(df):
        return {}
    df["_t"] = pd.to_datetime(df["checked"], errors="coerce")
    df = df[df["_t"] >= pd.Timestamp.today().normalize() - pd.Timedelta(days=DAYS_KEPT)]
    df = df.sort_values("_t", ascending=False)
    df["_key"] = df["symbol"].astype(str) + "|" + df["source"].astype(str) + "|" + df["side"].astype(str)
    df = df.drop_duplicates("_key", keep="first")              # the same tip forwarded twice: latest only
    groups, cache = {}, {}
    for _, r in df.iterrows():
        src = str(r.get("source")) if pd.notna(r.get("source")) and str(r.get("source")) else "forwarded"
        new = "🆕 " if since is not None and r["_t"] > pd.Timestamp(since) else ""
        when = f"{r['_t']:%d %b}"
        if pd.isna(r.get("symbol")) or not str(r.get("symbol")).strip() or str(r.get("symbol")) == "nan":
            raw = str(r.get("raw") or "")[:60].replace("\n", " ")
            groups.setdefault(src, []).append(f"{new}❔ <i>(forwarded {when})</i> I couldn't read a stock or market "
                                              f"in it: “{E(raw)}…” - forward it with the name to track it.")
            continue
        name, side = str(r["symbol"]), str(r.get("side") or "buy")
        trade_side = "sell" if side == "sell" else "buy"
        tk = r.get("ticker") if isinstance(r.get("ticker"), str) and r.get("ticker") else None
        off = float(r.get("offset") or 0) if "offset" in r and pd.notna(r.get("offset")) else 0.0
        hi = lo = None
        if tk:
            ltp = _market_price(tk, off, cache)
        elif name in snap["close"]:
            ltp = float(snap["close"][name])
            hi, lo = float(snap["high"].get(name, ltp)), float(snap["low"].get(name, ltp))
        else:
            ltp = None
        verdict = VERDICT_WORD.get(str(r.get("verdict")), str(r.get("verdict")).lower())
        origin = f"forwarded {when}, my verdict: {verdict}"
        if ltp is None:
            groups.setdefault(src, []).append(f"{new}❔ <b>{E(name)}</b> <i>({E(origin)})</i> - no live price this hour.")
            continue
        outcome = str(r.get("outcome"))
        has_levels = all(pd.notna(r.get(k)) for k in ("entry", "stop", "target"))
        if outcome in RESULT:
            groups.setdefault(src, []).append(
                f"{new}{RESULT[outcome]}: <b>{E(name)}</b> <i>({E(origin)})</i>\n<code>Now {_f(ltp)}"
                f"{_since(ltp, r.get('entry'), trade_side)}</code>")
            continue
        if outcome in ("open", "waiting entry") and has_levels:
            entry, stop, target = float(r["entry"]), float(r["stop"]), float(r["target"])
            if outcome == "waiting entry":
                groups.setdefault(src, []).append(new + _wait_line(
                    name, origin, trade_side, ltp, (entry, entry), stop, target,
                    *judge(trade_side, ltp, None, None, None, waiting=True, zone=(entry, entry))))
            else:
                icon, status, todo = judge(trade_side, ltp, entry, stop, target, hi=hi, lo=lo)
                groups.setdefault(src, []).append(new + _line(name, origin, trade_side, ltp, entry, stop, target, icon,
                                                              status, "If you took it: " + todo[0].lower() + todo[1:]))
            continue
        # not tracked to a result (skip verdict, option tip, no levels): still shown, with the move since then
        why = ("option tip - I show the stock's move" if "option" in outcome or any(x in side for x in ("CE", "PE"))
               else "no stop/target to track" if not has_levels else "not tracked")
        groups.setdefault(src, []).append(
            f"{new}📌 <b>{E(name)}{(' ' + E(side)) if any(x in side for x in ('CE', 'PE')) else ''}</b> <i>({E(origin)})</i> - {E(why)}"
            f"\n<code>Now {_f(ltp)}{_since(ltp, r.get('ltp'), trade_side)}</code>")
    return groups


def symbols_needed():
    """Stocks whose live price the hourly scan must fetch for this update (every tip of the last 60 days)."""
    from . import journal
    from .tipcheck import TIPS_F
    syms = set()
    cut = pd.Timestamp.today().normalize() - pd.Timedelta(days=DAYS_KEPT)
    try:
        t = journal.load_tips()
        t = t[(t["kind"] == "tip") & (pd.to_datetime(t["date"]) >= cut)]
        syms |= set(t["symbol"])
    except Exception:
        pass
    if SIGNALS_F.exists():
        sg = pd.read_csv(SIGNALS_F)
        syms |= set(sg.loc[pd.to_datetime(sg["date"]) >= pd.Timestamp.today().normalize() - pd.Timedelta(days=1), "symbol"])
    if TIPS_F.exists():
        df = pd.read_csv(TIPS_F)
        m = pd.to_datetime(df["checked"], errors="coerce") >= cut
        if "ticker" in df:
            m &= df["ticker"].isna() | (df["ticker"].astype(str) == "")
        syms |= set(df.loc[m, "symbol"].dropna().astype(str)) - {"nan", ""}
    return sorted(syms)


def message(snap, tips, ts, today=None, since=None):
    today = today or pd.Timestamp(ts).date()
    blocks = [f"⏱ <b>TIPS UPDATE</b> · {pd.Timestamp(ts):%I:%M %p} · every tip of the last {DAYS_KEPT} days"]
    st = system_tips(snap, tips, today)
    if st:
        blocks.append("🤖 <b>System tips</b>\n" + "\n\n".join(st))
    sg = scan_signals(snap, tips, today)
    if sg:
        blocks.append("🔔 <b>Today's scan signals</b>\n" + "\n\n".join(sg))
    fw = forwarded(snap, today, since)
    for src, lines in fw.items():
        blocks.append(f"📨 <b>Forwarded from {E(src)}</b> ({len(lines)})\n" + "\n\n".join(lines))
    if len(blocks) == 1:
        blocks.append("No tips yet. Forward any tip to the bot and it will appear here every hour.")
    n = len(st) + len(sg) + sum(len(v) for v in fw.values())
    n_new = sum(l.startswith("🆕") for v in fw.values() for l in v)
    blocks.append(f"<i>{n} tip(s) listed" + (f", {n_new} new since the last update (🆕)" if n_new else "") +
                  ". Research, not advice - you decide and place every order yourself.</i>")
    return "\n\n\u2063".join(blocks)


# ----------------------------------------------------------------------------- Saturday weekly summary
def daily_snap(symbols):
    """Last daily close/high/low of each stock (weekend: Friday's bar), from the stored price files."""
    from . import data_prices
    out = {k: {} for k in ("close", "high", "low")}
    for s in symbols:
        try:
            df = data_prices.load(s)
            if df is None or not len(df):
                continue
            last = df.iloc[-1]
            out["close"][s], out["high"][s], out["low"][s] = float(last["close"]), float(last["high"]), float(last["low"])
        except Exception:
            continue
    return {k: pd.Series(v, dtype=float) for k, v in out.items()}


def _state(side, ltp, entry, stop, target, outcome=None):
    """-> (bucket, icon, words) for the weekly overview."""
    if outcome in ("target",):
        return "right", "✅", "closed - target reached"
    if outcome in ("stop",):
        return "wrong", "❌", "closed - stop hit"
    if outcome in ("expired", "never filled"):
        return "nores", "⌛", "closed - " + ("ran out of time" if outcome == "expired" else "never reached entry")
    if outcome == "waiting entry":
        return "waiting", "⏳", "waiting for its entry"
    if ltp is None or entry is None:
        return "untracked", "📌", "not tracked (no levels / option / skip)"
    g = (ltp / entry - 1) * 100 * (1 if side != "sell" else -1)
    return ("profit", "🟢", f"open, {g:+.1f}%") if g >= 0 else ("loss", "🔴", f"open, {g:+.1f}%")


def weekly_summary(today=None):
    """Owner's Saturday message: channel scorecards + every tip of the week (closed/open, profit/loss)."""
    from . import journal
    from .tipcheck import TIPS_F
    from .market_views import source_record
    today = pd.Timestamp(today or pd.Timestamp.today()).normalize()
    week0 = today - pd.Timedelta(days=7)
    rows, buckets = [], {}
    tips = journal.load_tips()
    t = tips[tips["kind"] == "tip"]
    t = t[(pd.to_datetime(t["date"]) >= week0) | t["status"].isin(["pending", "open"])]
    fw = pd.read_csv(TIPS_F) if TIPS_F.exists() else pd.DataFrame(columns=["checked", "outcome", "symbol"])
    fw["_t"] = pd.to_datetime(fw["checked"], errors="coerce")
    fw = fw[((fw["_t"] >= week0) | fw["outcome"].isin(["open", "waiting entry"])) & fw["symbol"].notna()]
    fw = fw.sort_values("_t", ascending=False).drop_duplicates(["symbol", "source", "side"], keep="first")
    no_tk = fw["ticker"].isna() | (fw["ticker"].astype(str) == "") if "ticker" in fw else pd.Series(True, index=fw.index)
    stock_syms = set(t["symbol"]) | set(fw.loc[no_tk, "symbol"].astype(str))
    snap = daily_snap(sorted(stock_syms))
    sys_lines = []
    for _, r in t.sort_values("date").iterrows():
        s = r["symbol"]
        ltp = float(snap["close"][s]) if s in snap["close"] else None
        if r["status"] in ("pending",):
            b, icon, words = "waiting", "⏳", "waiting for the buy zone"
        elif r["status"] == "open":
            entry = float(r["entry_price"]) if pd.notna(r.get("entry_price")) else (r["entry_low"] + r["entry_high"]) / 2
            b, icon, words = _state("buy", ltp, entry, r["stop"], r["target1"])
            if pd.notna(r.get("qty")) and ltp:
                words += f", ₹{(ltp - entry) * float(r['qty']):+,.0f} on {int(r['qty'])}"
        else:
            pnl = float(r["pnl"]) if pd.notna(r.get("pnl")) else 0
            b = "right" if pnl > 0 else "wrong"
            icon, words = ("✅" if pnl > 0 else "❌"), f"closed ({r.get('exit_reason') or r['status']}), ₹{pnl:+,.0f}"
        buckets[b] = buckets.get(b, 0) + 1
        sys_lines.append(f"{icon} <b>{E(s)}</b> <i>({pd.Timestamp(r['date']):%d %b})</i> - {E(words)}")
    by_src, cache = {}, {}
    for _, r in fw.iterrows():
        src = str(r.get("source")) if pd.notna(r.get("source")) and str(r.get("source")) else "forwarded"
        name, side = str(r["symbol"]), str(r.get("side") or "buy")
        tk = r.get("ticker") if isinstance(r.get("ticker"), str) and r.get("ticker") else None
        off = float(r.get("offset") or 0) if "offset" in r and pd.notna(r.get("offset")) else 0.0
        ltp = _market_price(tk, off, cache) if tk else (float(snap["close"][name]) if name in snap["close"] else None)
        tracked = r["outcome"] in ("open", "waiting entry", "target", "stop", "expired", "never filled") and \
            pd.notna(r.get("entry"))
        b, icon, words = _state("sell" if side == "sell" else "buy", ltp, float(r["entry"]) if tracked else None,
                                r.get("stop"), r.get("target"), r["outcome"] if tracked else None)
        if b == "untracked" and ltp and pd.notna(r.get("ltp")):
            words += f"; {(ltp / float(r['ltp']) - 1) * 100:+.1f}% since forwarded"
        buckets[b] = buckets.get(b, 0) + 1
        by_src.setdefault(src, []).append(f"{icon} <b>{E(name)}</b> <i>({r['_t']:%d %b})</i> - {E(words)}")
    n = len(sys_lines) + sum(len(v) for v in by_src.values())
    word = {"right": "✅ right", "wrong": "❌ wrong", "nores": "⌛ no result", "profit": "🟢 open in profit",
            "loss": "🔴 open in loss", "waiting": "⏳ waiting for entry", "untracked": "📌 not tracked"}
    head = (f"🗓 <b>WEEKLY SUMMARY</b> · week to {today:%d %b %Y}\n{n} tip(s) this week: " +
            ", ".join(f"{buckets[k]} {word[k]}" for k in word if buckets.get(k)) if n else
            f"🗓 <b>WEEKLY SUMMARY</b> · week to {today:%d %b %Y}\nNo tips this week.")
    blocks = [head]
    cards = []
    allfw = pd.read_csv(TIPS_F) if TIPS_F.exists() else pd.DataFrame(columns=["source"])
    for src in sorted(set(allfw["source"].dropna().astype(str)) - {""}):
        g = allfw[allfw["source"] == src]
        rec = source_record(src, allfw)
        n_open = int(g["outcome"].isin(["open", "waiting entry"]).sum())
        cards.append(f"• {E(rec)}" + (f" {n_open} still open." if n_open else ""))
    if cards:
        blocks.append("📒 <b>Channel scorecards</b> (all time)\n" + "\n".join(cards))
    if sys_lines:
        blocks.append("🤖 <b>System tips</b>\n" + "\n".join(sys_lines))
    for src, lines in by_src.items():
        blocks.append(f"📨 <b>{E(src)}</b>\n" + "\n".join(lines))
    extra = []
    try:
        import json
        from .config import DATA
        rw = json.loads((DATA / "research_week.json").read_text())
        wk = {d: v for d, v in rw.items() if d >= str(week0.date())}
        tested, adopted = sum(v["tested"] for v in wk.values()), sum(v["adopted"] for v in wk.values())
        extra.append(f"🔬 Research: {tested} ideas tested this week, {adopted} adopted"
                     + (" - the tips strategy was upgraded." if adopted else " - the tips strategy is unchanged."))
    except Exception:
        pass
    try:
        from .daemon import SCAN_SLOTS, _load
        st = _load()
        days = [today - pd.Timedelta(days=i) for i in range(1, 8)]
        due = [(d_, h, m) for d_ in days if d_.weekday() < 5 for h, m in SCAN_SLOTS]
        ran = sum(1 for d_, h, m in due if st.get(f"scan {h:02d}:{m:02d} {d_:%Y-%m-%d}"))
        extra.append(f"🩺 System: {ran} of {len(due)} hourly updates ran this week.")
    except Exception:
        pass
    try:
        from .intraday_paper import week_line
        extra.append(week_line(today))
    except Exception:
        pass
    if extra:
        blocks.append("\n".join(extra))
    blocks.append("<i>Research, not advice - you decide and place every order yourself.</i>")
    return "\n\n⁣".join(blocks)
