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
    import re
    from .config import ROOT
    f = ROOT / "my_secrets.yaml"
    txt = f.read_text(encoding="utf-8") if f.exists() else ""
    if re.search(r"(?m)^telegram_chat_id:", txt):
        txt = re.sub(r"(?m)^telegram_chat_id:.*$", f'telegram_chat_id: "{chat}"', txt)
    else:
        txt += f'\ntelegram_chat_id: "{chat}"\n'
    f.write_text(txt, encoding="utf-8")


def send(settings, text):
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
        for i in range(0, len(text), 3800):
            requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                          data={"chat_id": chat, "text": text[i:i + 3800]}, timeout=20).raise_for_status()
        return "Telegram message sent"
    except Exception as e:
        log.warning("Telegram failed: %s", e)
        return f"Telegram failed: {e}"
