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


def send(settings, text):
    token = (settings.get("telegram_bot_token") or "").strip()
    if not token:
        return "Telegram not set up"
    try:
        chat = str(settings.get("telegram_chat_id") or "").strip() or _chat_id(token)
        if not chat:
            return "Telegram: send any message to your bot first, so it knows where to reply"
        for i in range(0, len(text), 3800):
            requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                          data={"chat_id": chat, "text": text[i:i + 3800]}, timeout=20).raise_for_status()
        return "Telegram message sent"
    except Exception as e:
        log.warning("Telegram failed: %s", e)
        return f"Telegram failed: {e}"
