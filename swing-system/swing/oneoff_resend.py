"""ONE-OFF owner request (2026-11-17, sent once): re-send the open tips of a given day as clean cards (the owner deleted the
originals in Telegram). Request: oneoff/resend_request.json {"id": ..., "day": "YYYY-MM-DD", "setup": "RCP"}.
Runs once inside the daemon (where the tip store lives; re-sent 17 Nov) and marks itself done in data/oneoff_done.json."""
import json

import pandas as pd

from .config import DATA, ROOT, get_logger, load_settings

log = get_logger()
REQ_F = ROOT / "oneoff" / "resend_request.json"
DONE_F = DATA / "oneoff_done.json"


def maybe_run(now=None):
    try:
        req = json.loads(REQ_F.read_text())
    except Exception:
        return
    rid = str(req.get("id"))
    try:
        done = json.loads(DONE_F.read_text())
    except Exception:
        done = {}
    if done.get(rid) == "done":
        return
    from . import telegram
    from .bot import tip_card
    from .live_engine import load_tips
    t = load_tips()
    sel = t.iloc[0:0]
    if len(t) and "setup" in t:
        same_kind = t["setup"].astype(str).str.strip() == str(req.get("setup", "RCP"))
        day = str(req.get("day"))
        on_day = t["day"].astype(str).str[:10].eq(day) | t["time"].astype(str).str[:10].eq(day)
        sel = t[same_kind & on_day]
        if not len(sel):                       # fall back: the open tips of that kind from the last 3 days
            recent = pd.to_datetime(t["time"].astype(str).str[:10], errors="coerce") >= pd.Timestamp(day) - pd.Timedelta(days=1)
            sel = t[same_kind & recent & (t["status"].astype(str) == "open")]
    log.info("One-off re-send: tips in store %d, of kind %s %d", len(t),
             req.get("setup"), int((t["setup"].astype(str).str.strip() == str(req.get("setup"))).sum()) if len(t) and "setup" in t else 0)
    s = load_settings()
    if not len(sel) and req.get("rebuild_positional"):
        sel = rebuild_positional(str(req.get("day")), s)
    if len(sel):
        telegram.send(s, f"🔁 Re-sending your {len(sel)} tip(s) from {req.get('day')} as requested:", label="trade tip")
        for _, r in sel.iterrows():
            card = tip_card(r)
            if str(r.get("status")) != "open":
                card += f"\n(status now: {r['status']})"
            telegram.send(s, card, label="trade tip")
    log.info("One-off re-send: %d tip(s)", len(sel))
    done[rid] = "done"
    DONE_F.write_text(json.dumps(done))


def rebuild_positional(day, settings):
    """D113 recovery: the store was empty (tips were lost between runs). Recompute the positional signals exactly as
    the evening scan saw them on `day` (price bars up to that day), rebuild the tips (same stop / quantity rules),
    and put them back into the tip store so they are tracked and get their exit alerts."""
    from . import positional
    from .high_prob import universe
    from .live_engine import load_tips, save_tip
    from .tipcheck import equity_list
    eq = set(equity_list()["SYMBOL"].astype(str))
    cap = float(settings.get("capital", 45000))
    rows = []
    for sym in universe():
        if sym not in eq:
            continue
        try:
            a = positional._adjusted(sym)
            if a is None:
                continue
            a = a[a.index <= pd.Timestamp(day)]
            sg = positional.signal(a) if len(a) >= 300 else None
        except Exception:
            continue
        if not sg:
            continue
        per = max(1e-9, sg["close"] - sg["stop"])
        qty = int(min(cap * positional.RISK_PCT / 100 / per, cap * 0.25 / sg["close"]))
        if qty < 1:
            continue
        rows.append({"time": f"{day} 18:44", "type": "NORMAL", "symbol": sym, "side": "buy", "entry": sg["close"],
                     "stop": sg["stop"], "targets": "", "rank": positional.RANK, "qty": qty, "status": "open", "hit": 0,
                     "day": day, "setup": "RCP"})
    t = load_tips()
    have = set(t.loc[t.get("setup", pd.Series(dtype=str)).astype(str) == "RCP", "symbol"].astype(str)) if len(t) else set()
    for r in rows:
        if r["symbol"] not in have:
            save_tip(r)
    log.info("One-off rebuild: %d positional tip(s) recomputed for %s", len(rows), day)
    return pd.DataFrame(rows)
