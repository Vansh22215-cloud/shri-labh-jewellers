"""Optional Telegram alerts. Needs telegram_bot_token in settings.yaml.
If telegram_chat_id is empty we look it up automatically from the last message
you sent to your bot (so you only need to paste the token)."""
import requests

from .config import get_logger

log = get_logger()


def _chat_id(token):
    r = requests.get(f"https://api.telegram.org/bot{token}/getUpdates", timeout=20).json()
    for u in reversed(r.get("result", [])):
        msg = u.get("message") or u.get("channel_post")
        if msg:
            return msg["chat"]["id"]
    return None


def _remember_chat(chat):
    """Telegram forgets messages after ~24h, so store the chat id permanently in my_secrets.yaml."""
    import os
    import re
    if os.environ.get("GITHUB_ACTIONS"):
        return   # on GitHub the chat id comes from a secret; never write private values to files there
    from .config import ROOT
    f = ROOT / "my_secrets.yaml"
    txt = f.read_text(encoding="utf-8") if f.exists() else ""
    if re.search(r"(?m)^telegram_chat_id:", txt):
        txt = re.sub(r"(?m)^telegram_chat_id:.*$", f'telegram_chat_id: "{chat}"', txt)
    else:
        txt += f'\ntelegram_chat_id: "{chat}"\n'
    f.write_text(txt, encoding="utf-8")


def send(settings, text, html=False):
    token = (settings.get("telegram_bot_token") or "").strip()
    if not token:
        return "Telegram not set up"
    try:
        chat = str(settings.get("telegram_chat_id") or "").strip()
        if not chat:
            chat = _chat_id(token)
            if not chat:
                return "Telegram: open your bot in Telegram and send it any message (e.g. hi), so it knows where to reply"
            _remember_chat(chat)
        chunks = text.split("\n\n\u2063") if html else None   # html: pre-split cards (no broken tags)
        if html:
            buf, parts = "", []
            for c in chunks:
                if len(buf) + len(c) > 3800 and buf:
                    parts.append(buf); buf = ""
                buf += ("\n\n" if buf else "") + c
            parts.append(buf)
            for part in parts:
                requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                              data={"chat_id": chat, "text": part, "parse_mode": "HTML",
                                    "disable_web_page_preview": "true"}, timeout=20).raise_for_status()
            return "Telegram message sent"
        for i in range(0, len(text), 3800):
            requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                          data={"chat_id": chat, "text": text[i:i + 3800],
                                **({"parse_mode": "HTML", "disable_web_page_preview": "true"} if html else {})}, timeout=20).raise_for_status()
        return "Telegram message sent"
    except Exception as e:
        log.warning("Telegram failed: %s", e)
        return f"Telegram failed: {e}"


def send_document(settings, path, caption="", mime="text/html"):
    """Send a file (e.g. the evening HTML report) to the owner's chat."""
    token = (settings.get("telegram_bot_token") or "").strip()
    chat = str(settings.get("telegram_chat_id") or "").strip()
    if not token or not chat:
        return "Telegram not set up"
    try:
        with open(path, "rb") as fh:
            requests.post(f"https://api.telegram.org/bot{token}/sendDocument", data={"chat_id": chat, "caption": caption[:1000]},
                          files={"document": (path.name if hasattr(path, "name") else "report.html", fh, mime)},
                          timeout=60).raise_for_status()
        return "report sent"
    except Exception as e:
        log.warning("Telegram document failed: %s", e)
        return f"Telegram document failed: {e}"
