"""Telegram bot: forward any stock tip to your bot and it replies GOOD / RISKY / AVOID within seconds.

Security: the bot ONLY answers the owner's chat (telegram_chat_id in my_secrets.yaml). Messages from
anyone else are ignored. It never places orders and never asks for broker logins.
Runs continuously (Windows: starts at log-on via Task Scheduler). Telegram keeps unread messages
for ~24 hours, so tips forwarded while the PC was off are answered when it comes back on.
"""
import json
import os
import time

import re

import requests

from . import tipcheck
from .config import DATA, PRIVATE, DISCLAIMER, REPORTS, get_logger, load_settings, load_state

log = get_logger()
OFFSET = DATA / "bot_offset.txt"
HELP = ("Forward me any stock tip (from a channel, group or friend) and I'll check it against real prices:\n"
        "• GOOD / RISKY / AVOID with reasons\n• the odds from that stock's own 5-year history vs what you need "
        "after Zerodha charges\n• red flags: no stop-loss, pump-and-dump stocks, results, trend\n\n"
        "You can also type a tip, e.g.  BUY TATASTEEL 175 SL 170 TGT 185\n"
        "Index, forex, gold, crude and crypto views/setups work too (Nifty, Bank Nifty, Sensex, EURUSD, USDINR, "
        "XAUUSD, BTC ...), e.g. 'Nifty weakness only below 24290' or 'XAUUSD BUY 2650 SL 2640 TP 2670'. "
        "I track every one and message you when it is right, wrong or runs out of time.\n"
        "/report - tonight's report summary\n/score - how forwarded tips have actually turned out\n"
        "/bought SYMBOL QTY PRICE [STOP] - record a trade you placed (e.g. /bought ICICIBANK 5 1425 1340)\n"
        "/sold SYMBOL [PRICE] - record that you sold it\n/trades - your open trades\n"
        "Order tickets: tap ✅ I placed it after placing a ticket in the Kite app (records it for you).\n"
        "/status - is Kite connected, live test price, last alert check\n/kite - get a Kite login link now\n"
        "Every morning ~8:45 I send a Kite login link - one tap keeps live Zerodha prices on for the day.\n\n"
        + DISCLAIMER)


def _api(token, method, **params):
    r = requests.post(f"https://api.telegram.org/bot{token}/{method}", data=params, timeout=70)
    return r.json()


def _source(msg):
    fo = msg.get("forward_origin") or {}
    if fo.get("type") == "channel":
        return fo.get("chat", {}).get("title", "channel")
    if fo.get("type") == "user":
        return fo.get("sender_user", {}).get("first_name", "user")
    if fo.get("type") == "hidden_user":
        return fo.get("sender_user_name", "hidden user")
    if fo.get("type") == "chat":
        return fo.get("sender_chat", {}).get("title", "group")
    if msg.get("forward_from_chat"):
        return msg["forward_from_chat"].get("title", "channel")
    if msg.get("forward_from"):
        return msg["forward_from"].get("first_name", "user")
    return "typed by you"


def _report_summary():
    st = load_state()
    f = REPORTS / "latest.html"
    if not f.exists():
        return "No report yet."
    import re
    txt = f.read_text(encoding="utf-8")
    head = re.search(r"class='card banner[^']*'>(.*?)</div>", txt, re.S)
    why = re.findall(r"<li>(.*?)</li>", txt.split("<h2>Why</h2>")[1].split("</ul>")[0]) if "<h2>Why</h2>" in txt else []
    return f"Report {st.get('last_trading_day', '')}: {head.group(1) if head else '?'}\n" + "\n".join(f"- {w}" for w in why)


def _score_text():
    sc = tipcheck.source_scorecard()
    if not sc:
        return "No forwarded tip has finished yet (target, stop or time-out). Keep forwarding tips - I track them all."
    lines = ["How forwarded tips actually turned out:"]
    for k, v in sc["by_source"].items():
        lines.append(f"• {k}: {v['tips']} tips, target hit {v['target_hit_pct']}%, stop hit {v['stop_hit_pct']}%")
    lines.append("By my verdict:")
    for k, v in sc["by_verdict"].items():
        lines.append(f"• {k}: {v['tips']} tips, target hit {v['target_hit_pct']}%, stop hit {v['stop_hit_pct']}%")
    return "\n".join(lines)


def trade_command(text):
    """/bought SYMBOL QTY PRICE [STOP]  |  /sold SYMBOL [PRICE]  |  /trades   (updates data/my_trades.csv)"""
    import pandas as pd
    from . import data_prices, journal
    from .config import DATA, load_settings, load_strategy
    parts = text.split()
    cmd = parts[0].lower()
    my = journal.load_my_trades()
    if cmd == "/trades":
        if my.empty:
            return "No open trades recorded. Use /bought SYMBOL QTY PRICE [STOP]."
        return "Your open trades:\n" + "\n".join(f"- {r.symbol}: {int(r.qty)} @ {r.buy_price} (stop {r.stop})" for r in my.itertuples())
    if len(parts) < 2:
        return "Usage: /bought ICICIBANK 5 1425 1340   or   /sold ICICIBANK 1500"
    sym = parts[1].upper()
    if cmd == "/bought":
        try:
            qty, price = int(parts[2]), float(parts[3])
        except Exception:
            return "Usage: /bought SYMBOL QTY PRICE [STOP], e.g. /bought ICICIBANK 5 1425 1340"
        stop = float(parts[4]) if len(parts) > 4 else None
        if stop is None:   # default: the tips strategy's stop (3 x ATR below the buy price, or 2 x for v1)
            s_ = load_settings()
            p = load_strategy(s_.get("aggressive_strategy", "a1") if s_.get("tips_mode") == "aggressive" else s_["live_strategy"])
            df = data_prices.load(sym)
            if df is not None and len(df) > 20:
                tr = (df["high"] - df["low"]).tail(14).mean()
                stop = round(price - p["stop_atr_mult"] * tr, 2)
        from .risk import check as risk_check
        ok, why, _n = risk_check("buy", qty, price, stop) if stop else (False, ["No stop-loss could be set."], {})
        row = pd.DataFrame([{"symbol": sym, "buy_date": str(pd.Timestamp.today().date()), "buy_price": price,
                             "qty": qty, "stop": stop}])
        out = pd.concat([my[my["symbol"] != sym], row], ignore_index=True)
        out.to_csv(journal.MY_TRADES, index=False)
        risk_line = ("\n🛡 Risk check: PASS." if ok else "\n🛡 Risk check: WARNING - " + " ".join(why) +
                     " (recorded anyway - it's your trade).")
        return (f"Recorded: bought {qty} {sym} @ {price}" + (f", stop {stop}. Set this stop as a GTT in Kite now." if stop
                                                             else ".") + risk_line)
    if cmd == "/sold":
        if sym not in set(my["symbol"]):
            return f"{sym} is not in your open trades."
        r = my[my["symbol"] == sym].iloc[0]
        px = float(parts[2]) if len(parts) > 2 else None
        f = PRIVATE / "closed_trades.csv"
        rec = pd.DataFrame([{"symbol": sym, "buy_date": r["buy_date"], "buy_price": r["buy_price"], "qty": r["qty"],
                             "exit_date": str(pd.Timestamp.today().date()), "exit_price": px,
                             "pnl": round((px - float(r["buy_price"])) * float(r["qty"]), 2) if px else None}])
        (pd.concat([pd.read_csv(f), rec]) if f.exists() else rec).to_csv(f, index=False)
        my[my["symbol"] != sym].to_csv(journal.MY_TRADES, index=False)
        return f"Recorded: sold {sym}" + (f" @ {px}. P&L Rs {rec.iloc[0]['pnl']:,.0f}" if px else "") + ". Delete its GTT in Kite."
    return "Unknown command."


def _restore_backup(token, doc):
    """The owner forwarded a backup file the system sent earlier -> merge it back (trades, tips, data archive)."""
    import requests
    from . import archive
    try:
        info = _api(token, "getFile", file_id=doc["file_id"])
        path = (info.get("result") or {}).get("file_path")
        if not path:
            return "Could not download that file from Telegram (files over 20 MB can't be restored by the bot)."
        r = requests.get(f"https://api.telegram.org/file/bot{token}/{path}", timeout=120)
        r.raise_for_status()
        tmp = DATA / "restore.tar.gz"
        tmp.write_bytes(r.content)
        n = archive.restore(tmp)
        tmp.unlink(missing_ok=True)
        return f"Backup restored: {n} files/rows merged. Nothing already stored was overwritten."
    except Exception as e:
        log.error("restore failed: %s", type(e).__name__)
        return f"Restore failed ({type(e).__name__}). The file must be one the system sent you."


def _read_picture(token, msg):
    """A forwarded chart picture -> what chart_reader found on it (None if no picture / it failed).
    The picture is kept only in memory/temp and deleted at once (it can be personal)."""
    import tempfile
    photo = (msg.get("photo") or [None])[-1]
    doc = msg.get("document") or {}
    fid = photo["file_id"] if photo else (doc.get("file_id") if str(doc.get("mime_type", "")).startswith("image/") else None)
    if not fid:
        return None
    try:
        info = _api(token, "getFile", file_id=fid).get("result") or {}
        r = requests.get(f"https://api.telegram.org/file/bot{token}/{info['file_path']}", timeout=60)
        r.raise_for_status()
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=True) as f:
            f.write(r.content); f.flush()
            from .chart_reader import read_image
            out = read_image(f.name)
        log.info("Chart picture read: %d words, %d lines, %d pattern names", len(out["text"].split()),
                 len(out["levels"]), len(out["patterns"]))
        return out
    except Exception as e:
        log.warning("Chart picture could not be read: %s", type(e).__name__)
        return {"text": "", "levels": [], "patterns": [], "axis": False, "failed": True}


def handle(token, owner, msg, capital):
    chat = str(msg["chat"]["id"])
    if owner and chat != owner:
        log.warning("Ignored a message from a stranger's chat %s", chat)
        return owner
    if not owner and msg["chat"].get("type") == "private":
        owner = chat
    text = (msg.get("text") or msg.get("caption") or "").strip()
    doc = msg.get("document") or {}
    image = None
    if not str(doc.get("file_name", "")).startswith(("swing-backup-", "swing-archive-")):
        image = _read_picture(token, msg)
        if image and image.get("text"):
            text = (text + "\n" + image["text"]).strip()     # caption first, then what is written on the chart
        if image and image.get("range"):
            from . import market_views
            if not market_views.find_instrument(text) and not tipcheck.parse(text).get("symbol"):
                from .chart_reader import guess_instrument
                g = guess_instrument(image["range"])
                if g:
                    image["guessed"] = g
                    text = g + " " + text
    if str(doc.get("file_name", "")).startswith(("swing-backup-", "swing-archive-")):
        reply = _restore_backup(token, doc)
    elif not text:
        reply = ("I couldn't read any words or prices on that picture. Forward it with its caption, or type the "
                 "name and level, e.g. 'Nifty weakness below 24290'.")
    elif re.search(r"(?:kite_|request_token=)([A-Za-z0-9]{8,64})", text):
        # the login hand-back: "/start kite_XXXX", "kite_XXXX", or the whole login page address pasted in
        from . import kite
        ok, reply = kite.exchange(re.search(r"(?:kite_|request_token=)([A-Za-z0-9]{8,64})", text).group(1))
        if not ok and kite.logged_in():
            reply = "✅ Already connected to Kite for today - this code was used already, nothing more to do."
    elif text.lower().startswith(("/kite", "/login")):
        from . import kite
        reply = (f"🔑 Log in to Kite: {kite.login_url()}\nAfter logging in, tap Start in Telegram - or, if nothing "
                 "happens, copy the message the page shows and send it here.") if kite.configured() else \
            "Kite is not set up (the API key/secret are missing in GitHub Secrets)."
    elif text.startswith("/start") or text.startswith("/help"):
        reply = HELP
    elif text.startswith("/status"):
        reply = status_text()
    elif text.startswith("/report"):
        reply = _report_summary()
    elif text.startswith("/score"):
        reply = _score_text()
    elif text.lower().startswith(("/bought", "/sold", "/trades")):
        reply = trade_command(text)
    else:
        tipcheck.LAST_TICKET = None
        try:
            reply = tipcheck.check_text(text, source=_source(msg), capital=capital, image=image)
            if image and "What I read on the picture" not in reply:
                reply = ("🖼 I read your chart picture" + (" (it was hard to read - blurry or small)" if not image.get("axis")
                         else "") + ".\n\n" + reply)
        except Exception as e:
            log.error("tip check failed: %s", e)
            reply = "Sorry, I hit an error checking that tip. It has been logged and will be fixed."
    _send_reply(token, chat, reply, msg["message_id"])
    t = getattr(tipcheck, "LAST_TICKET", None)
    if t:
        tipcheck.LAST_TICKET = None
        try:
            send_ticket(token, chat, t)
        except Exception as e:
            log.warning("sending ticket failed: %s", type(e).__name__)
    return owner


def status_text():
    """/status: is Kite connected, a live test price and where it came from, the alerts' last check."""
    import json as _j
    from . import kite
    from .config import DATA
    L = ["🩺 System status"]
    if not kite.configured():
        L.append("Kite: not set up (keys missing in GitHub Secrets) - using Yahoo prices.")
    elif kite.logged_in():
        q = kite.quotes(["NIFTY50", "RELIANCE"])
        if q:
            L.append("Kite: ✅ connected until 6 am - live prices from Zerodha.")
            L += [f"Test: {k} {v['last']:,.2f} (Zerodha, live)" for k, v in q.items()]
        else:
            L.append("Kite: logged in, but Zerodha did not answer the price test just now - using Yahoo meanwhile.")
    else:
        L.append(f"Kite: not logged in today - using Yahoo prices. Log in: {kite.login_url()}")
    try:
        a = _j.loads((DATA / "alerts_last.json").read_text())
        L.append(f"Alerts: last check {a['at'][11:16]} on {a['source']} prices, {a['priced']} of {a['items']} "
                 "trades/tips priced (checked every minute 9:15-3:30 on market days).")
    except Exception:
        L.append("Alerts: no check yet (they run every minute 9:15-3:30 on market days).")
    return "\n".join(L)


def handle_button(token, owner, cq):
    """A tap on a ticket button (✅ I placed it / ⏭ Skip). Only the owner's taps count."""
    chat = str(((cq.get("message") or {}).get("chat") or {}).get("id", ""))
    if owner and chat != owner:
        _api(token, "answerCallbackQuery", callback_query_id=cq["id"], text="Not your ticket.")
        return
    from .risk import on_button
    try:
        reply = on_button(cq.get("data", ""))
    except Exception as e:
        log.error("ticket button failed: %s", type(e).__name__)
        reply = "Sorry, that button failed (logged). You can type /bought SYMBOL QTY PRICE STOP instead."
    _api(token, "answerCallbackQuery", callback_query_id=cq["id"], text=reply[:190])
    _api(token, "sendMessage", chat_id=chat, text=reply[:4000])


def send_ticket(token, chat, t):
    """Send an order ticket with its two buttons."""
    import json as _j
    from .risk import buttons, ticket_text
    b = buttons(t)
    params = dict(chat_id=chat, text=ticket_text(t), parse_mode="HTML")
    if b:
        params["reply_markup"] = _j.dumps(b)
    return _api(token, "sendMessage", **params)


def _send_reply(token, chat, reply, reply_to):
    """Cards are formatted (bold headings); if Telegram rejects the formatting, the same words go as plain text."""
    import html as _h
    import re as _re
    if "<b>" in reply:
        r = _api(token, "sendMessage", chat_id=chat, text=reply[:4000], parse_mode="HTML",
                 disable_web_page_preview="true", reply_to_message_id=reply_to)
        if not isinstance(r, dict) or r.get("ok", True) is not False:
            return
        reply = _h.unescape(_re.sub(r"</?(b|i|pre|code)>", "", reply))
    _api(token, "sendMessage", chat_id=chat, text=reply[:4000], reply_to_message_id=reply_to)


def _updates_problem(token, owner, res, offset):
    """Telegram refused to hand over messages. Log why (never the token), fix the common cause, tell the owner."""
    code, desc = res.get("error_code"), str(res.get("description", ""))[:200]
    log.warning("Bot: Telegram getUpdates refused (%s): %s", code, desc)
    if code == 409 and "webhook" in desc.lower():
        # a webhook (set by some other tool) blocks reading messages: switch it off, keep waiting messages
        d = _api(token, "deleteWebhook", drop_pending_updates="false")
        log.info("Bot: webhook removed (%s)", d.get("ok"))
        res = _api(token, "getUpdates", offset=offset, timeout=0)
        if res.get("ok"):
            return res
    try:
        from .daemon import claim_once
        if owner and claim_once("bot read problem"):
            hint = ("Another program or website is also connected to your bot and reads its messages first. "
                    "Close/disconnect it (only this system should use the bot)." if code == 409 else
                    "Telegram did not accept the bot key - check TELEGRAM_BOT_TOKEN in GitHub Secrets."
                    if code in (401, 404) else "Telegram had a problem; I keep trying every minute.")
            _api(token, "sendMessage", chat_id=owner,
                 text=f"⚠️ I can't read your messages right now (Telegram said: {desc or code}).\n{hint}")
    except Exception:
        pass
    return {"ok": False, "result": []}


def poll_once():
    """Answer every waiting message once and exit (used by GitHub Actions every hour)."""
    s = load_settings()
    token = (s.get("telegram_bot_token") or "").strip()
    if not token:
        return 0
    owner = str(s.get("telegram_chat_id") or "").strip()
    offset = int(OFFSET.read_text()) if OFFSET.exists() else 0
    res = _api(token, "getUpdates", offset=offset, timeout=0)
    if not res.get("ok", False):
        res = _updates_problem(token, owner, res, offset)
    n = 0
    for u in res.get("result", []):
        OFFSET.write_text(str(u["update_id"] + 1))
        msg = u.get("message")
        if msg:
            owner = handle(token, owner, msg, float(s.get("capital", 45000)))
            n += 1
        cq = u.get("callback_query")
        if cq:
            handle_button(token, owner, cq)
            n += 1
    if n:
        log.info("Bot: answered %d message(s)", n)
    return n
