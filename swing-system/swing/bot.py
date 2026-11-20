"""Telegram bot of the rebuilt ATLAS. Answers ONLY the owner's chat. Never places orders, never asks for broker logins.

Commands:
  /kite            the Kite login link (also sent at 8:45 am on weekdays)
  /status          Kite login, live feed, candle library, live strategies, kill switch
  /capital [N]     show / set your trading money (quantities follow it)
  /stop, /resume   kill switch: no new tips / tips again (exit alerts for open tips always go out)
  /tips            open tips
  /strategies      every strategy written so far: tested? live?
  /test NAME       test a strategy on Kite data (runs outside market hours; the result comes here)
  /learn NAME      the Learner's summary for a strategy
  /approve NAME    let a TESTED strategy send live tips (your decision); /unapprove NAME stops it
Forward a backup file the system sent you to restore it."""
import json
import re
import time

import pandas as pd
import requests

from .config import DATA, RESULTS, ROOT, DISCLAIMER, get_logger, load_settings

log = get_logger()
OFFSET = DATA / "bot_offset.txt"
HELP = ("ATLAS - your strategies, tested on Kite data, scanned live on every NSE stock.\n\n"
        "/status - is everything running\n/kite - Kite login link\n/capital - your trading money; /capital 60000 to change\n"
        "/stop - no new tips; /resume - tips again\n/tips - open tips\n/strategies - your strategies: tested? live?\n"
        "/test NAME - test a strategy on Kite history\n/learn NAME - where and why it works or fails\n"
        "/approve NAME - let a tested strategy send live tips; /unapprove NAME - stop it\n\n" + DISCLAIMER)
TOKEN_REFUSED_SINCE = None
_READ_FAIL_SINCE = None


# ----------------------------------------------------------------------------- settings edits (owner only)
def _settings_text():
    return (ROOT / "settings.yaml").read_text(encoding="utf-8")


def _settings_write(txt):
    p = ROOT / "settings.yaml"
    tmp = p.with_suffix(".tmp")
    tmp.write_text(txt, encoding="utf-8")
    tmp.replace(p)


def capital_command(text):
    parts = text.replace(",", "").split()
    cur = float(load_settings().get("capital") or 0)
    if len(parts) < 2:
        return f"Trading money now: ₹{cur:,.0f}. To change it: /capital 60000"
    try:
        amt = int(float(parts[1].replace("₹", "")))
    except ValueError:
        return "Use: /capital 60000"
    if not 10000 <= amt <= 10_000_000:
        return "Please give an amount between ₹10,000 and ₹1 crore."
    if cur and not 0.5 * cur <= amt <= 2 * cur and (len(parts) < 3 or parts[2].lower() != "sure"):
        return f"That is a big change from ₹{cur:,.0f} to ₹{amt:,.0f}. If it is right, send: /capital {amt} sure"
    new, n = re.subn(r"(?m)^capital:\s*[0-9.]+", f"capital: {amt}", _settings_text(), count=1)
    if n != 1:
        return "Could not find the capital line in settings.yaml - nothing changed."
    _settings_write(new)
    return f"✅ Trading money set to ₹{amt:,.0f} (was ₹{cur:,.0f}). New tips are sized on it; open tips keep theirs."


def kill_command(on):
    new, n = re.subn(r"(?m)^kill_switch:\s*\w+", f"kill_switch: {'true' if on else 'false'}", _settings_text(), count=1)
    if n != 1:
        return "Could not find the kill_switch line in settings.yaml - nothing changed."
    _settings_write(new)
    return ("⛔ Kill switch ON: no new tips. Exit alerts for open tips still come. /resume to start again." if on else
            "✅ Kill switch OFF: approved strategies send tips again.")


def _live_list(names):
    new, n = re.subn(r"(?m)^live_strategies:.*$", "live_strategies: [" + ", ".join(names) + "]", _settings_text(), count=1)
    if n != 1:
        new = _settings_text().rstrip() + "\nlive_strategies: [" + ", ".join(names) + "]\n"
    _settings_write(new)


def approve_command(text, on=True):
    from .strategy import load_all
    parts = text.split()
    if len(parts) < 2:
        return "Use: /approve NAME (see /strategies)"
    name = parts[1].strip()
    S = load_all()
    live = list(load_settings().get("live_strategies") or [])
    if on:
        if name not in S:
            return f"No strategy called {name}. /strategies lists them."
        if not (RESULTS / "tests" / f"{name}.json").exists():
            return f"{name} has not been tested on Kite data yet - send /test {name} first."
        if name in live:
            return f"{name} already sends live tips."
        _live_list(live + [name])
        return f"✅ {name} approved by you: it sends live tips from the next market candle (stop {S[name].stop_fraction() * 100:.1f}%)."
    if name not in live:
        return f"{name} is not live."
    _live_list([x for x in live if x != name])
    return f"⏹ {name} stopped: no more live tips from it (open tips are still watched until they close)."


def strategies_text():
    from .strategy import load_all
    S = load_all()
    live = set(load_settings().get("live_strategies") or [])
    if not S:
        return "No strategies yet - tell me your first one and I will write and test it on Kite data."
    L = ["Your strategies:"]
    for k, st in S.items():
        f = RESULTS / "tests" / f"{k}.json"
        res = ""
        if f.exists():
            a = (json.loads(f.read_text()).get("all") or {})
            res = f" - tested: {a.get('trades', 0):,} trades, {a.get('win_pct')}% won, avg {a.get('avg_net_pct', 0):+.2f}% after costs"
        else:
            res = " - not tested yet"
        L.append(f"• {k} ({st.interval}, {st.kind}){res}{' - 🟢 LIVE' if k in live else ''}")
    return "\n".join(L)


def test_command(text):
    from .daemon import TEST_QUEUE
    from .strategy import load_all
    parts = text.split()
    if len(parts) < 2:
        return "Use: /test NAME (see /strategies)"
    name = parts[1]
    if name not in load_all():
        return f"No strategy called {name}."
    try:
        q = json.loads(TEST_QUEUE.read_text())
    except Exception:
        q = []
    if name not in q:
        q.append(name)
        TEST_QUEUE.write_text(json.dumps(q))
    from .candles import ORDER, complete, progress
    iv = load_all()[name].interval
    if iv in ("minute", "3minute"):
        return (f"{name} uses {iv} candles, but 1-minute history is not downloaded (your choice, 20 Nov). Say the word "
                "if tests show 1-minute would help, and the download starts.")
    wait = "" if complete(iv) else (f" Kite {iv} history is still downloading ({progress().get(iv)} stocks done) - "
                                    "the test starts by itself when it is complete.")
    return (f"🧪 {name} queued for its test on Kite history (every NSE stock). It runs outside market hours; the "
            "result and the Learner's summary come here." + wait)


def learn_text(text):
    parts = text.split()
    if len(parts) < 2:
        return "Use: /learn NAME"
    f = RESULTS / "learner" / f"{parts[1]}.json"
    if not f.exists():
        return f"No Learner report for {parts[1]} yet (it is made after its test)."
    a = json.loads(f.read_text())
    L = [f"🧠 Learner - {parts[1]}"]
    for lab in ("test", "live"):
        if lab in a:
            L.append(f"{'Kite test' if lab == 'test' else 'Live tips'}: {a[lab]['trades']:,} trades, {a[lab]['win_pct']}% won, "
                     f"avg {a[lab]['avg_net_pct']:+.2f}% after costs")
    better = [g for g in a.get("groups", []) if g.get("better")][:4]
    worse = [g for g in a.get("groups", []) if g.get("worse")][:4]
    if better:
        L.append("Works best: " + "; ".join(f"{g['context'].replace('_', ' ')} {g['value']} ({g['avg_net_pct']:+.2f}%, {g['trades']})" for g in better))
    if worse:
        L.append("Fails: " + "; ".join(f"{g['context'].replace('_', ' ')} {g['value']} ({g['avg_net_pct']:+.2f}%, {g['trades']})" for g in worse))
    L += ["Ideas to test:"] + [f"• {i}" for i in a.get("ideas", [])[:5]]
    L.append("Full report: results/learner/" + parts[1] + ".md")
    return "\n".join(L)


def open_tips_text():
    from .tips import load_tips
    T = load_tips()
    o = T[T["exit_time"].isna()] if len(T) else T
    if not len(o):
        return "No open tips."
    return "Open tips:\n" + "\n".join(f"• {r.sym} ({r.strategy}): bought ≈ ₹{r.entry:,.2f}, stop ₹{r.stop:,.2f}"
                                      + (f", target ₹{r.target:,.2f}" if r.target == r.target and r.target else "")
                                      for r in o.itertuples())


def status_text():
    from . import candles, kite
    from .daemon import _FEED
    s = load_settings()
    L = [f"Kite: {'✅ logged in' if kite.logged_in() else '❌ not logged in (/kite)'}"]
    f = _FEED.get("feed")
    if f is not None and f.alive():
        st = f.status()
        L.append(f"Live feed: {st['instruments']:,} instruments, {st['ticks']:,} updates, last {st['last_tick_s']}s ago")
    else:
        L.append("Live feed: off (runs 9:08 am - 3:32 pm on weekdays when logged in)")
    try:
        p = candles.progress()
        L.append("Candle library (stocks complete): " + ", ".join(f"{i} {p[i]}" for i in candles.ORDER)
                 + (" - storage limit reached" if p.get("storage_full") else ""))
    except Exception:
        L.append("Candle library: not started")
    live = s.get("live_strategies") or []
    L.append(f"Live strategies: {', '.join(live) if live else 'none'}")
    L.append(f"Kill switch: {'⛔ ON' if s.get('kill_switch') else 'off'} · capital ₹{float(s.get('capital') or 0):,.0f} · "
             f"stop-loss {s.get('stop_loss_pct', 1)}%")
    return "\n".join(L)


# ----------------------------------------------------------------------------- Telegram plumbing
def _api(token, method, **params):
    r = requests.post(f"https://api.telegram.org/bot{token}/{method}", data=params, timeout=70)
    return r.json()


def _restore_backup(token, doc):
    from . import backup
    try:
        info = _api(token, "getFile", file_id=doc["file_id"])
        path = (info.get("result") or {}).get("file_path")
        if not path:
            return "Could not download that file from Telegram."
        r = requests.get(f"https://api.telegram.org/file/bot{token}/{path}", timeout=120)
        r.raise_for_status()
        return f"Backup restored: {backup.restore(r.content)} file(s) merged. Nothing already stored was overwritten."
    except Exception as e:
        log.error("restore failed: %s", type(e).__name__)
        return f"Restore failed ({type(e).__name__}). The file must be one the system sent you."


def handle(token, owner, msg):
    chat = str(msg["chat"]["id"])
    if owner and chat != owner:
        log.warning("Ignored a message from another chat")
        return owner
    if not owner and msg["chat"].get("type") == "private":
        owner = chat
    text = (msg.get("text") or msg.get("caption") or "").strip()
    doc = msg.get("document") or {}
    low = text.lower()
    if str(doc.get("file_name", "")).startswith("atlas-backup-"):
        reply = _restore_backup(token, doc)
    elif re.search(r"(?:kite_|request_token=)([A-Za-z0-9]{8,64})", text):
        from . import kite
        ok, reply = kite.exchange(re.search(r"(?:kite_|request_token=)([A-Za-z0-9]{8,64})", text).group(1))
        if not ok and kite.logged_in():
            reply = "✅ Already connected to Kite for today - nothing more to do."
    elif low.startswith(("/kite", "/login")):
        from . import kite
        reply = (f"🔑 Log in to Kite: {kite.login_url()}\nAfter logging in, tap Start in Telegram.") if kite.configured() else \
            "Kite is not set up (the API key/secret are missing in GitHub Secrets)."
    elif low.startswith(("/start", "/help")) or not text:
        reply = HELP
    elif low.startswith("/status"):
        reply = status_text()
    elif low.startswith("/capital"):
        reply = capital_command(text)
    elif low.startswith("/stop"):
        reply = kill_command(True)
    elif low.startswith("/resume"):
        reply = kill_command(False)
    elif low.startswith("/tips"):
        reply = open_tips_text()
    elif low.startswith("/strategies"):
        reply = strategies_text()
    elif low.startswith("/test"):
        reply = test_command(text)
    elif low.startswith("/learn"):
        reply = learn_text(text)
    elif low.startswith("/approve"):
        reply = approve_command(text, True)
    elif low.startswith("/unapprove"):
        reply = approve_command(text, False)
    else:
        reply = "I only understand the commands below.\n\n" + HELP
    for i in range(0, max(1, len(reply)), 3900):
        _api(token, "sendMessage", chat_id=chat, text=reply[i:i + 3900], disable_web_page_preview="true")
    return owner


def _updates_problem(token, owner, res, offset):
    global _READ_FAIL_SINCE, TOKEN_REFUSED_SINCE
    code, desc = res.get("error_code"), str(res.get("description", ""))[:200]
    log.warning("Bot: Telegram getUpdates refused (%s): %s", code, desc)
    if code == 409 and "webhook" in desc.lower():
        _api(token, "deleteWebhook", drop_pending_updates="false")
        res = _api(token, "getUpdates", offset=offset, timeout=0)
        if res.get("ok"):
            return res
    if code in (401, 404):
        if not TOKEN_REFUSED_SINCE:
            from .config import token_shape
            log.warning("Bot: the bot key was refused. Its format: %s", token_shape(token))
        TOKEN_REFUSED_SINCE = TOKEN_REFUSED_SINCE or time.time()
    return {"ok": False, "result": []}


def poll_once():
    """Answer every waiting message once."""
    global _READ_FAIL_SINCE, TOKEN_REFUSED_SINCE
    s = load_settings()
    token = (s.get("telegram_bot_token") or "").strip()
    if not token:
        return 0
    owner = str(s.get("telegram_chat_id") or "").strip()
    offset = int(OFFSET.read_text()) if OFFSET.exists() else 0
    res = _api(token, "getUpdates", offset=offset, timeout=0)
    if not res.get("ok", False):
        res = _updates_problem(token, owner, res, offset)
    else:
        _READ_FAIL_SINCE = TOKEN_REFUSED_SINCE = None
    n = 0
    for u in res.get("result", []):
        OFFSET.write_text(str(u["update_id"] + 1))
        msg = u.get("message")
        if msg:
            owner = handle(token, owner, msg)
            n += 1
    return n
