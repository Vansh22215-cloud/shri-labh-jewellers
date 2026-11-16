"""AUTOPILOT (D109) - lets the system run for years without Claude: it grades itself and acts.

1. close_tip(): every closed tip gets its real result (% of the entry; options: the underlying's move), so the
   system knows how each strategy is doing LIVE, not just in back-tests.
2. strategy_health(): per strategy family - DIP (dip-buy), POS (positional), INTRA (intraday), FNO - over its
   last 30 closed tips: win rate and average result, compared with what the tests promised.
3. throttle(): what the live record allows -
     DIP  : live avg < 0 over >= 20 tips  -> only rank-10 (tier A) dip-buys are sent
     POS  : live avg < 0 over >= 20 tips  -> positional tips paused for 60 days, then retried automatically
     INTRA: live avg < 0 over >= 30 tips  -> intraday tips paused until the SHADOW record (every setup followed,
            sent or not) turns positive again; min rank 7 when the shadow record is clearly good (>= 60% winners,
            avg >= +0.15R over >= 40), else the owner's min_rank
   Each change is told ONCE on Telegram ('system problem' label - rare) with the numbers.
4. health_alert(): problems the evening health check finds (stale prices, failing self-tests, Kite data down)
   reach the owner once a day instead of only going to the log.
State is kept in data/autopilot.json (market data only).
"""
import json

import pandas as pd

from .config import DATA, get_logger, load_settings

log = get_logger()
STATE_F = DATA / "autopilot.json"
EXPECT = {"DIP": 72.0, "POS": 45.0, "INTRA": 50.0, "FNO": 50.0, "AI": 52.0, "DISC": 53.0}      # tested win rates (D98/D104/D105)


def _state():
    try:
        return json.loads(STATE_F.read_text())
    except Exception:
        return {}


def _save(s):
    STATE_F.write_text(json.dumps(s, indent=1))


def family(row):
    st, ty = str(row.get("setup", "")), str(row.get("type", ""))
    if ty == "FNO":
        return "FNO"
    if ty == "INTRADAY":
        return "INTRA"
    if st == "RCP":
        return "POS"
    if st == "AI":
        return "AI"
    if st.startswith("DS"):
        return "DISC"
    return "DIP"


def close_tip(t, i, status, px=None, now=None):
    """Mark tip row i closed with its real result. px = exit price of the STOCK / underlying."""
    for col in ("status", "closed_at"):
        if col not in t or t[col].dtype != object:
            t[col] = (t[col] if col in t else None)
            t[col] = t[col].astype(object)
    t.loc[i, "status"] = status
    t.loc[i, "closed_at"] = str(now or pd.Timestamp.now(tz="Asia/Kolkata").tz_localize(None))[:16]
    try:
        r = t.loc[i]
        e = float(r["entry"])
        if px is None:
            if status == "stop":
                px = float(r["stop"])
            elif status == "done":
                tg = [float(x) for x in str(r.get("targets", "")).split("/") if x and x != "nan"]
                px = tg[-1] if tg else None
        if px is not None and e > 0:
            sgn = 1 if str(r.get("side", "buy")) == "buy" else -1
            t.loc[i, "result_pct"] = round(sgn * (float(px) / e - 1) * 100, 2)
    except Exception:
        pass


def strategy_health(n=30):
    from .live_engine import load_tips
    t = load_tips()
    out = {}
    if not len(t) or "result_pct" not in t:
        return out
    c = t[t["result_pct"].notna()].copy()
    c["fam"] = [family(r) for _, r in c.iterrows()]
    for f, g in c.groupby("fam"):
        g = g.sort_values("closed_at").tail(n)
        out[f] = {"n": int(len(g)), "win_pct": round(float((g["result_pct"] > 0).mean() * 100), 1),
                  "avg_pct": round(float(g["result_pct"].mean()), 2)}
    return out


def _notify(text):
    try:
        from . import telegram
        telegram.send(load_settings(), text, label="autopilot" if text.startswith("🤖") else "system problem")
    except Exception:
        pass


def throttle(now=None):
    """Recompute what the live record allows; notify once per change. Returns the state."""
    now = pd.Timestamp(now or pd.Timestamp.now(tz="Asia/Kolkata").tz_localize(None))
    s = _state()
    h = strategy_health()
    old = dict(s.get("rules", {}))
    rules = {}
    d = h.get("DIP", {})
    rules["dip_rank10_only"] = bool(d.get("n", 0) >= 20 and d.get("avg_pct", 0) < 0)
    p = h.get("POS", {})
    until = s.get("pos_paused_until")
    if until and now >= pd.Timestamp(until):
        until = None                                               # 60 days are over: retry
    if p.get("n", 0) >= 20 and p.get("avg_pct", 0) < 0 and not until and not old.get("pos_paused"):
        until = str((now + pd.Timedelta(days=60)).date())
    rules["pos_paused"] = bool(until)
    s["pos_paused_until"] = until
    a = h.get("AI", {})
    au = s.get("ai_paused_until")
    if au and now >= pd.Timestamp(au):
        au = None
    if a.get("n", 0) >= 30 and a.get("avg_pct", 0) < 0 and not au and not old.get("ai_paused"):
        au = str((now + pd.Timedelta(days=60)).date())
    rules["ai_paused"] = bool(au)
    s["ai_paused_until"] = au
    i = h.get("INTRA", {})
    from .live_engine import live_record
    sh = live_record(last_n=80, min_n=40)
    good = [k for k, v in sh.items() if v["n"] >= 40 and v["win_pct"] >= 60 and v["avg_r"] >= 0.15]
    shadow_ok = any(v["n"] >= 20 and v["avg_r"] > 0 for v in sh.values())
    if i.get("n", 0) >= 30 and i.get("avg_pct", 0) < 0:
        rules["intra_paused"] = not shadow_ok
    else:
        rules["intra_paused"] = bool(old.get("intra_paused")) and not shadow_ok
    rules["intra_rank7_setups"] = sorted(good)
    s["rules"], s["health"], s["checked"] = rules, h, str(now)[:16]
    _save(s)
    msgs = {"dip_rank10_only": ("dip-buy: only the strongest (10/10) tips are sent now", "dip-buy: back to normal"),
            "pos_paused": (f"positional tips paused until {until}", "positional tips resumed"),
            "intra_paused": ("intraday tips paused until the followed setups prove positive again",
                             "intraday tips resumed"),
            "ai_paused": (f"AI picks paused until {au}", "AI picks resumed")}
    for k, (on, off) in msgs.items():
        if bool(rules.get(k)) != bool(old.get(k)) and (rules.get(k) or k in old):
            fam = {"dip_rank10_only": "DIP", "pos_paused": "POS", "intra_paused": "INTRA", "ai_paused": "AI"}[k]
            x = h.get(fam, {})
            _notify(f"🤖 Autopilot: {on if rules.get(k) else off}. Live record of the last {x.get('n', 0)} closed "
                    f"tips: {x.get('win_pct', 0)}% in profit, avg {x.get('avg_pct', 0):+.2f}% "
                    f"(tested: ~{EXPECT[fam]:.0f}% in profit). Nothing for you to do.")
    if rules.get("intra_rank7_setups") != old.get("intra_rank7_setups"):
        log.info("Autopilot: intraday setups allowed from rank 7: %s", ", ".join(good) or "none")
    return s


def rules():
    return _state().get("rules", {})


def health_alert(problems, now=None):
    """Evening health-check problems -> one Telegram message a day (they used to go only into the muted report)."""
    if not problems:
        return False
    day = str(pd.Timestamp(now or pd.Timestamp.now(tz="Asia/Kolkata")).date())
    s = _state()
    if s.get("health_alert_day") == day:
        return False
    _notify("⚠️ System problem (evening check):\n• " + "\n• ".join(p[:200] for p in problems[:5]) +
            "\nThe system keeps running and retries tomorrow.")
    s["health_alert_day"] = day
    _save(s)
    return True


def kite_watch(quotes_ok, logged_in, now):
    """During market hours: logged in but no Kite quotes for 30 minutes -> one alert a day (e.g. subscription
    ended, or Zerodha changed something)."""
    s = _state()
    day = str(now.date())
    if not logged_in or quotes_ok:
        s["kite_bad_since"] = None
        _save(s)
        return False
    since = s.get("kite_bad_since")
    if not since:
        s["kite_bad_since"] = str(now)[:16]
        _save(s)
        return False
    if (now - pd.Timestamp(since)).total_seconds() >= 1800 and s.get("kite_alert_day") != day:
        _notify("⚠️ System problem: logged in to Kite, but Zerodha has sent no prices for 30 minutes. Check that "
                "your Kite Connect subscription is active (developers.kite.trade). Meanwhile Yahoo prices are used.")
        s["kite_alert_day"] = day
        _save(s)
        return True
    return False
