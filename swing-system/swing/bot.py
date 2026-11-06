"""Telegram bot: forward any stock tip to your bot and it replies GOOD / RISKY / AVOID within seconds.

Security: the bot ONLY answers the owner's chat (telegram_chat_id in my_secrets.yaml). Messages from
anyone else are ignored. It never places orders and never asks for broker logins.
Runs continuously (Windows: starts at log-on via Task Scheduler). Telegram keeps unread messages
for ~24 hours, so tips forwarded while the PC was off are answered when it comes back on.
"""
import json
import os
import time

import requests

from . import tipcheck
from .config import DATA, PRIVATE, DISCLAIMER, REPORTS, get_logger, load_settings, load_state
from .telegram import _remember_chat

log = get_logger()
OFFSET = DATA / "bot_offset.txt"
LOCK = DATA / "bot.lock"
HELP = ("Forward me any stock tip (from a channel, group or friend) and I'll check it against real prices:\n"
        "• GOOD / RISKY / AVOID with reasons\n• the odds from that stock's own 5-year history vs what you need "
        "after Zerodha charges\n• red flags: no stop-loss, pump-and-dump stocks, results, trend\n\n"
        "You can also type a tip, e.g.  BUY TATASTEEL 175 SL 170 TGT 185\n"
        "Index, forex, gold, crude and crypto views/setups work too (Nifty, Bank Nifty, Sensex, EURUSD, USDINR, "
        "XAUUSD, BTC ...), e.g. 'Nifty weakness only below 24290' or 'XAUUSD BUY 2650 SL 2640 TP 2670'. "
        "I track every one and message you when it is right, wrong or runs out of time.\n"
        "/report - tonight's report summary\n/score - how forwarded tips have actually turned out\n"
        "/bought SYMBOL QTY PRICE [STOP] - record a trade you placed (e.g. /bought ICICIBANK 5 1425 1340)\n"
        "/sold SYMBOL [PRICE] - record that you sold it\n/trades - your open trades\n\n" + DISCLAIMER)


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
        row = pd.DataFrame([{"symbol": sym, "buy_date": str(pd.Timestamp.today().date()), "buy_price": price,
                             "qty": qty, "stop": stop}])
        out = pd.concat([my[my["symbol"] != sym], row], ignore_index=True)
        out.to_csv(journal.MY_TRADES, index=False)
        return f"Recorded: bought {qty} {sym} @ {price}" + (f", stop {stop}. Set this stop as a GTT in Kite now." if stop else ".")
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


def handle(token, owner, msg, capital):
    chat = str(msg["chat"]["id"])
    if owner and chat != owner:
        log.warning("Ignored a message from a stranger's chat %s", chat)
        return owner
    if not owner and msg["chat"].get("type") == "private":
        owner = chat
        _remember_chat(chat)
    text = (msg.get("text") or msg.get("caption") or "").strip()
    doc = msg.get("document") or {}
    if str(doc.get("file_name", "")).startswith(("swing-backup-", "swing-archive-")):
        reply = _restore_backup(token, doc)
    elif not text:
        reply = "Send or forward the tip as text (I can't read pictures of tips yet)."
    elif text.startswith("/start") or text.startswith("/help"):
        reply = HELP
    elif text.startswith("/report"):
        reply = _report_summary()
    elif text.startswith("/score"):
        reply = _score_text()
    elif text.lower().startswith(("/bought", "/sold", "/trades")):
        reply = trade_command(text)
    else:
        try:
            reply = tipcheck.check_text(text, source=_source(msg), capital=capital)
        except Exception as e:
            log.error("tip check failed: %s", e)
            reply = "Sorry, I hit an error checking that tip. It has been logged and will be fixed."
    _api(token, "sendMessage", chat_id=chat, text=reply[:4000], reply_to_message_id=msg["message_id"])
    return owner


def run_forever():
    if LOCK.exists():
        try:
            pid = int(LOCK.read_text())
            os.kill(pid, 0)
            log.info("Bot already running (pid %s)", pid)
            return
        except Exception:
            pass
    LOCK.write_text(str(os.getpid()))
    backoff = 5
    log.info("Telegram tip-check bot started")
    while True:
        try:
            s = load_settings()
            token = (s.get("telegram_bot_token") or "").strip()
            if not token:
                time.sleep(300)
                continue
            owner = str(s.get("telegram_chat_id") or "").strip()
            offset = int(OFFSET.read_text()) if OFFSET.exists() else 0
            res = _api(token, "getUpdates", offset=offset, timeout=50)
            for u in res.get("result", []):
                OFFSET.write_text(str(u["update_id"] + 1))
                msg = u.get("message")
                if msg:
                    owner = handle(token, owner, msg, float(s.get("capital", 45000)))
            backoff = 5
        except Exception as e:
            log.warning("bot loop error: %s (retrying in %ss)", type(e).__name__, backoff)   # never log the token
            time.sleep(backoff)
            backoff = min(backoff * 2, 300)


def poll_once():
    """Answer every waiting message once and exit (used by GitHub Actions every hour)."""
    s = load_settings()
    token = (s.get("telegram_bot_token") or "").strip()
    if not token:
        return 0
    owner = str(s.get("telegram_chat_id") or "").strip()
    offset = int(OFFSET.read_text()) if OFFSET.exists() else 0
    res = _api(token, "getUpdates", offset=offset, timeout=0)
    n = 0
    for u in res.get("result", []):
        OFFSET.write_text(str(u["update_id"] + 1))
        msg = u.get("message")
        if msg:
            owner = handle(token, owner, msg, float(s.get("capital", 45000)))
            n += 1
    return n
