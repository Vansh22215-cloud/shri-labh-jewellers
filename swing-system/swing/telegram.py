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


def _post(token, data, tries=4):
    """POST one message; retries network errors / Telegram rate limits (429) / server errors with backoff."""
    import time
    last = None
    for i in range(tries):
        try:
            r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data=data, timeout=30)
            if r.status_code == 429:
                wait = int((r.json().get("parameters") or {}).get("retry_after", 5))
                time.sleep(min(60, wait + 1))
                continue
            if r.status_code >= 500:
                last = f"HTTP {r.status_code}"
                time.sleep(3 * (i + 1))
                continue
            return r                       # 2xx, or a 4xx we cannot fix by retrying
        except requests.RequestException as e:
            last = type(e).__name__
            time.sleep(3 * (i + 1))
    raise RuntimeError(f"Telegram unreachable after {tries} tries ({last})")


def _plain(html_text):
    """HTML message -> plain text (used if Telegram rejects the formatting, so the message still arrives)."""
    import html as _h
    import re
    return _h.unescape(re.sub(r"</?(b|i|u|s|pre|code|a)(\s[^>]*)?>", "", html_text))


def _split(text, limit=3800):
    """Split at line breaks so no part is over Telegram's limit and no line (or HTML tag) is cut in half."""
    parts, buf = [], ""
    for line in text.split("\n"):
        while len(line) > limit:                         # a single very long line
            if buf:
                parts.append(buf); buf = ""
            parts.append(line[:limit]); line = line[limit:]
        if len(buf) + len(line) + 1 > limit and buf:
            parts.append(buf); buf = ""
        buf += ("\n" if buf else "") + line
    if buf:
        parts.append(buf)
    return parts or [""]


def _balanced(part):
    """Close <pre>/<b>/<i> left open by a split, so each HTML part is valid on its own."""
    import re
    out = part
    for tag in ("pre", "b", "i"):
        opens = len(re.findall(rf"<{tag}>", part)); closes = len(re.findall(rf"</{tag}>", part))
        if opens > closes:
            out += f"</{tag}>" * (opens - closes)
        elif closes > opens:
            out = f"<{tag}>" * (closes - opens) + out
    return out


# Owner's choice (D95): Telegram carries ONLY these. Everything else is written to the log, not sent.
ALLOWED = ("trade tip", "exit alert", "kite login", "company of the day")


def allowed(settings, label):
    return label in (settings.get("telegram_allowed") or ALLOWED)


def send(settings, text, html=False, label="message"):
    """Send a message to the owner. Never raises. Every result is logged in one public-safe line
    (length only, never contents), so a missing message can always be traced in the GitHub log."""
    if not allowed(settings, label):
        log.info("Telegram %s not sent - muted (owner's choice: only tips, exit alerts, Kite login, company "
                 "of the day)", label)
        return "muted"
    token = (settings.get("telegram_bot_token") or "").strip()
    if not token:
        log.warning("Telegram %s NOT sent: no bot token", label)
        return "Telegram not set up"
    try:
        chat = str(settings.get("telegram_chat_id") or "").strip()
        if not chat:
            chat = _chat_id(token)
            if not chat:
                log.warning("Telegram %s NOT sent: no chat id", label)
                return "Telegram: open your bot in Telegram and send it any message (e.g. hi), so it knows where to reply"
        if html:   # html messages may be pre-split into cards with a marker; keep cards whole when possible
            text = text.replace("\n\n\u2063", "\n\n")
        parts = _split(text)
        fallback = 0
        for part in parts:
            data = {"chat_id": chat, "text": _balanced(part) if html else part, "disable_web_page_preview": "true"}
            if html:
                data["parse_mode"] = "HTML"
            r = _post(token, data)
            if r.status_code == 400 and html:          # formatting rejected: send it as plain text instead
                fallback += 1
                r = _post(token, {"chat_id": chat, "text": _plain(part), "disable_web_page_preview": "true"})
            if r.status_code >= 300:
                raise RuntimeError(f"HTTP {r.status_code}: {r.text[:120]}")
        log.info("Telegram %s sent (%d chars, %d part(s)%s)", label, len(text), len(parts),
                 f", {fallback} as plain text" if fallback else "")
        return "Telegram message sent"
    except Exception as e:
        log.warning("Telegram %s FAILED: %s", label, e)
        return f"Telegram failed: {e}"


def send_document(settings, path, caption="", mime="text/html", label="file"):
    """Send a file (e.g. the evening HTML report) to the owner's chat."""
    if not allowed(settings, label):
        log.info("Telegram %s not sent - muted (owner's choice)", label)
        return "muted"
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
