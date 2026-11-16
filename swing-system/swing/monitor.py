"""NO SILENT FAILURES (audit 17 Nov 2026) - the owner always knows whether the system is working.

Called from the daemon every minute:
  heartbeat()        - records that the system is alive; after a gap (no run for > 20 minutes) the first run back
                       sends a 'recovered' message saying how long it was down
  kill_switch_watch()- the kill switch turning ON/OFF is confirmed on Telegram
  housekeeping()     - delivers undelivered critical messages (outbox) and clears a safety stop only when the
                       integrity check passes
  daily_status()     - 7:20 pm on weekdays: ONE message: did each part run, what was sent, and WHY there were no tips
                       (no opportunity / market closed / data unavailable / strategy problem / system not running)
  weekly_health()    - Saturday morning: live record of every strategy, skipped signals, safety events, backups
"""
import json
import time

import pandas as pd

from .config import DATA, PRIVATE, get_logger, load_settings

log = get_logger()
HB_F = DATA / "heartbeat.json"
_STARTED = {"done": False}
_LAST = {"house": 0.0}


def _send(text):
    try:
        from . import telegram
        return telegram.send_reliable(load_settings(), text, label="system status")
    except Exception:
        return False


def heartbeat(now):
    try:
        prev = json.loads(HB_F.read_text())
    except Exception:
        prev = {}
    if not _STARTED["done"]:
        _STARTED["done"] = True
        last = prev.get("last")
        if last:
            gap = (pd.Timestamp(now).tz_localize(None) - pd.Timestamp(last)).total_seconds() / 60 \
                if pd.Timestamp(now).tzinfo else (pd.Timestamp(now) - pd.Timestamp(last)).total_seconds() / 60
            if gap > 20:
                _send(f"🔄 System recovered: it was not running from {pd.Timestamp(last):%d %b %H:%M} to "
                      f"{pd.Timestamp(now):%H:%M} ({gap / 60:.1f} h). It has restarted by itself; open tips are "
                      "being checked again now. Tips or exit alerts that fell in that gap may have been missed.")
    HB_F.write_text(json.dumps({"last": str(pd.Timestamp(now).tz_localize(None) if pd.Timestamp(now).tzinfo
                                            else pd.Timestamp(now))[:19]}))


def kill_switch_watch(settings):
    st_f = DATA / "kill_switch_state.json"
    try:
        old = json.loads(st_f.read_text()).get("on")
    except Exception:
        old = None
    on = bool(settings.get("kill_switch"))
    if old is not None and on != old:
        _send("🛑 KILL SWITCH ON - no new trade tips will be sent. Exit alerts for open tips keep working."
              if on else "✅ Kill switch OFF - new trade tips are allowed again.")
    if old != on:
        st_f.write_text(json.dumps({"on": on}))


def housekeeping(settings):
    if time.time() - _LAST["house"] < 60:
        return
    _LAST["house"] = time.time()
    try:
        from . import telegram
        telegram.flush_outbox(settings)
    except Exception as e:
        log.warning("outbox flush failed: %s", type(e).__name__)
    try:
        from . import safety
        if safety.emergency_active():
            safety.try_clear(settings)
    except Exception as e:
        log.warning("safety check failed: %s", type(e).__name__)


def _today_tips(day):
    from .live_engine import load_tips
    t = load_tips()
    if not len(t):
        return t, t
    sent = t[t["time"].astype(str).str[:10] == day]
    closed = t[t.get("closed_at", pd.Series(dtype=str)).astype(str).str[:10] == day] if "closed_at" in t else t.iloc[0:0]
    return sent, closed


def status_text(now):
    """The daily status message (also used by /health)."""
    from . import safety
    s = load_settings()
    day = str(pd.Timestamp(now).date())
    L = [f"🩺 DAILY STATUS · {pd.Timestamp(now):%a %d %b}", ""]
    try:
        ev = json.loads((DATA / "evening_status.json").read_text())
    except Exception:
        ev = {}
    sent, closed = _today_tips(day)
    try:
        eng = json.loads((DATA / "engine_status.json").read_text())
    except Exception:
        eng = {}
    from .health import traded_today
    traded = traded_today(pd.Timestamp(now).tz_localize(None) if pd.Timestamp(now).tzinfo else pd.Timestamp(now))
    if traded is False:
        L.append("📅 Market closed today (weekend / holiday) - no scans needed.")
    if eng.get("date") == day:
        L.append(f"⚙️ Live engine: ran {eng.get('from', '?')}-{eng.get('to', '?')}, Kite data from "
                 f"{eng.get('kite_from', 'never (not logged in)')}, {eng.get('downloads', 0)} candle downloads.")
    elif traded:
        L.append("⚙️ Live engine: did NOT run today (no Kite login or the system was down) - no intraday / F&O scan.")
    if ev.get("date") == day:
        if not ev.get("fresh"):
            L.append(f"⚠️ Evening scan: prices were NOT fresh (last {ev.get('last_bar')}) - no new tips (safe skip).")
        else:
            c = ev.get("counts", {})
            L.append("🌙 Evening scan ran: " + ", ".join(f"{k} {v}" for k, v in c.items() if "tips" in k or "picks" in k)
                     or "🌙 Evening scan ran.")
        if ev.get("failed"):
            L.append("❌ Evening jobs that FAILED: " + ", ".join(ev["failed"]) + " (the rest ran).")
    elif traded is not False and pd.Timestamp(now).hour >= 19:
        L.append("❌ Evening scan has NOT run yet today.")
    n_sent = len(sent)
    L.append(f"📨 Tips sent today: {n_sent}" + (" (" + ", ".join(f"{k} {v}" for k, v in
                                                       sent.groupby(sent['type'].astype(str)).size().items()) + ")"
                                                if n_sent else ""))
    L.append(f"🚪 Tips closed today: {len(closed)}")
    try:
        from .live_engine import load_tips
        t = load_tips()
        L.append(f"📌 Open tips being watched: {int((t['status'].astype(str) == 'open').sum()) if len(t) else 0}")
    except Exception:
        L.append("❌ Tip store unreadable")
    try:
        sk = pd.read_csv(safety.SKIPPED_F)
        sk = sk[sk["time"].astype(str).str[:10] == day]
        if len(sk):
            L.append(f"🛡 Signals skipped by the safety gate: {len(sk)} (top reason: {sk['reason'].mode().iloc[0][:80]})")
    except Exception:
        pass
    em = safety.emergency_active()
    L.append(f"🛑 SAFETY STOP ACTIVE: {em['reason']}" if em else
             ("🛑 Kill switch ON" if s.get("kill_switch") else "✅ Safety: normal"))
    try:
        box = [l for l in (PRIVATE / "outbox.jsonl").read_text().splitlines() if l.strip()]
        if box:
            L.append(f"📮 {len(box)} message(s) waiting to be delivered (Telegram problems).")
    except Exception:
        pass
    if n_sent == 0:
        if traded is False:
            why = "market closed"
        elif ev.get("date") == day and not ev.get("fresh"):
            why = "data unavailable (stale prices)"
        elif ev.get("failed"):
            why = "a strategy job failed (see above)"
        elif em or s.get("kill_switch"):
            why = "tips are paused by the safety system"
        elif ev.get("date") != day and pd.Timestamp(now).hour >= 19:
            why = "the evening scan did not run (system problem)"
        else:
            why = "no stock met the tested rules today (normal)"
        L.append(f"ℹ️ Why no tips: {why}.")
    L.append("Research, not advice.")
    return "\n".join(L)


def daily_status(now):
    from .daemon import claim_once
    t = pd.Timestamp(now)
    if t.weekday() < 5 and (t.hour, t.minute) >= (19, 20) and claim_once("daily status", now):
        _send(status_text(now))


def weekly_health(now):
    from .daemon import claim_once
    t = pd.Timestamp(now)
    if t.weekday() != 5 or (t.hour, t.minute) < (10, 30) or not claim_once("weekly health", now):
        return
    from . import autopilot, safety
    L = [f"📊 WEEKLY STRATEGY HEALTH · week to {t:%d %b}", ""]
    h = autopilot.strategy_health()
    names = {"DIP": "Dip-buy", "POS": "Positional", "AI": "AI picks", "INTRA": "Intraday (experimental)",
             "FNO": "F&O (experimental)", "DISC": "Discovered"}
    for k, v in h.items():
        L.append(f"• {names.get(k, k)}: last {v['n']} closed tips - {v['win_pct']}% in profit, avg {v['avg_pct']:+.2f}% "
                 f"(tested ~{autopilot.EXPECT.get(k, 0):.0f}%)")
    if not h:
        L.append("• No closed tips yet - the live record builds up as tips close.")
    r = autopilot.rules()
    if any(r.get(k) for k in ("dip_rank10_only", "pos_paused", "intra_paused", "ai_paused")):
        L.append("🤖 Autopilot restrictions active: " + ", ".join(k for k in ("dip_rank10_only", "pos_paused",
                                                                              "intra_paused", "ai_paused") if r.get(k)))
    try:
        hist = (safety._state().get("history") or [])[-5:]
        wk = [x for x in hist if pd.Timestamp(x["on"]) >= t.tz_localize(None) - pd.Timedelta(days=7)] \
            if t.tzinfo else [x for x in hist if pd.Timestamp(x["on"]) >= t - pd.Timedelta(days=7)]
        if wk:
            L.append(f"🛑 Safety stops this week: {len(wk)} (last: {wk[-1]['reason'][:80]})")
    except Exception:
        pass
    try:
        from . import ml_ranker
        m = ml_ranker._load_model_file() or {}
        L.append(f"🧠 AI model: trained {m.get('trained', '?')}, validation rank-correlation {m.get('val_ic', '?')}")
    except Exception:
        pass
    L.append("Research, not advice.")
    _send("\n".join(L))


def engine_status(e, now, kite_on):
    """Called by the live engine every few minutes: what it is doing (for the daily status)."""
    try:
        f = DATA / "engine_status.json"
        try:
            st = json.loads(f.read_text())
        except Exception:
            st = {}
        day = str(pd.Timestamp(now).date())
        if st.get("date") != day:
            st = {"date": day, "from": f"{pd.Timestamp(now):%H:%M}"}
        st["to"] = f"{pd.Timestamp(now):%H:%M}"
        st["downloads"] = int(st.get("downloads_base", 0)) + int(getattr(e, "_downloads", 0))
        if kite_on and not st.get("kite_from"):
            st["kite_from"] = f"{pd.Timestamp(now):%H:%M}"
        st["funnel"] = dict(getattr(e, "funnel", {}))
        f.write_text(json.dumps(st, indent=1))
    except Exception:
        pass
