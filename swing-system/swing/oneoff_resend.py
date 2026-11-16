"""ONE-OFF owner request (2026-11-17, sent once): re-send the open tips of a given day as clean cards (the owner deleted the
originals in Telegram). Request: oneoff/resend_request.json {"id": ..., "day": "YYYY-MM-DD", "setup": "RCP"}.
Runs once inside the daemon (where the tip store lives) and marks itself done in data/oneoff_done.json."""
import json

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
    sel = t[(t["day"].astype(str) == str(req.get("day"))) & (t["setup"].astype(str) == str(req.get("setup", "RCP")))] \
        if len(t) and "setup" in t else t.iloc[0:0]
    s = load_settings()
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
