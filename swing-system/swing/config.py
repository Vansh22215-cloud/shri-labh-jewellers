"""Settings (settings.yaml) and folder paths of the ATLAS rebuild (owner 20 Nov: start again, Kite data only).

Everything is relative to the project folder, so the system works wherever
the folder is copied (Windows or Linux).
"""
import json
import logging
import os
import re
import time
from pathlib import Path

# D114: GitHub's computers run on UTC. The whole system thinks in Indian time (market hours, "today", dates of
# tips, trades and reports): between midnight and 5:30 am IST a UTC 'today' was still yesterday. Every program
# imports this module first, so the process clock is set to IST here once.
os.environ["TZ"] = "Asia/Kolkata"
try:
    time.tzset()
except AttributeError:      # Windows has no tzset (the owner's own PC is already on IST)
    pass

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"                 # private GitHub cache only (never in git)
PRIVATE = DATA / "private"           # personal records: tips, trades, Kite login pass
COMPANY = DATA / "company"           # NSE filings read for the Company of the Quarter
LOGS = ROOT / "logs"
RESULTS = ROOT / "results"           # public, non-personal results (test reports, learner reports) - saved to git
STATE = DATA / "state.json"
DISCLAIMER = "Research, not advice. You decide and place every order yourself."
for _d in (DATA, PRIVATE, COMPANY, LOGS, RESULTS):
    _d.mkdir(parents=True, exist_ok=True)


def on_github():
    import os
    return os.environ.get("GITHUB_ACTIONS") == "true"


def public_print(text, label="message"):
    """Print to the console, but on GitHub (public logs) only a one-line summary - never trade/position details."""
    if on_github():
        print(f"{label}: {len(str(text or ''))} characters (contents hidden: public log)")
    else:
        print(text)


def load_settings(path=None):
    """Read settings.yaml. Missing keys fall back to safe defaults; an unreadable file turns the kill switch ON."""
    defaults = {"capital": 0, "kill_switch": False, "stop_loss_pct": 1.0, "telegram_bot_token": "",
                "telegram_chat_id": "", "risk_limits": {"risk_per_trade_pct": 1, "max_order_pct": 25, "daily_loss_pct": 2}}
    p = Path(path) if path else ROOT / "settings.yaml"
    try:
        user = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception as e:
        logging.getLogger("swing").error("settings.yaml unreadable (%s); kill switch forced ON", e)
        user = {"kill_switch": True}
    defaults.update(user)
    for env_key, key in (("TELEGRAM_BOT_TOKEN", "telegram_bot_token"), ("TELEGRAM_CHAT_ID", "telegram_chat_id")):
        if os.environ.get(env_key):
            defaults[key] = os.environ[env_key]
    defaults["telegram_bot_token"] = clean_bot_token(defaults.get("telegram_bot_token"))
    sec = ROOT / "my_secrets.yaml"           # local PC only, never uploaded
    if path is None and sec.exists():
        try:
            defaults.update({k: v for k, v in (yaml.safe_load(sec.read_text(encoding="utf-8")) or {}).items() if v})
        except Exception as e:
            logging.getLogger("swing").error("my_secrets.yaml unreadable: %s", e)
    return defaults


def load_state():
    try:
        return json.loads(STATE.read_text())
    except Exception:
        return {}


def save_state(state):
    STATE.write_text(json.dumps(state, indent=2, default=str))


import re as _re

# SECURITY (audit 17 Nov): a Telegram bot token reached a committed report through an error message that contained
# the API URL. Every log line (file AND console = the public GitHub log) and every text built from logs is now
# scrubbed of anything that looks like a credential.
_SECRET_PATTERNS = [
    (_re.compile(r"bot\d{6,12}:[A-Za-z0-9_-]{30,}"), "bot<REDACTED>"),
    (_re.compile(r"\b\d{6,12}:AA[A-Za-z0-9_-]{30,}"), "<REDACTED-TELEGRAM-TOKEN>"),
    (_re.compile(r"(?i)(access_token|api_secret|api_key|request_token|checksum|authorization)(['\"]?\s*[:=]\s*['\"]?)"
                 r"[A-Za-z0-9:_\-.]{8,}"), r"\1\2<REDACTED>"),
    (_re.compile(r"(?i)token\s+[A-Za-z0-9]{6,}:[A-Za-z0-9]{8,}"), "token <REDACTED>"),
]


def redact(text):
    """Remove anything that looks like a credential from a text (logs, reports, messages)."""
    s = str(text)
    for rx, rep in _SECRET_PATTERNS:
        s = rx.sub(rep, s)
    return s


class _RedactFilter(logging.Filter):
    def filter(self, record):
        try:
            record.msg = redact(record.getMessage())
            record.args = ()
        except Exception:
            pass
        return True


def get_logger():
    """One log file for everything; the daily report summarises it in plain English."""
    log = logging.getLogger("swing")
    if not any(isinstance(f, _RedactFilter) for f in log.filters):
        log.addFilter(_RedactFilter())
    if not log.handlers:
        log.setLevel(logging.INFO)
        fh = logging.FileHandler(LOGS / "system.log", encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        log.addHandler(fh)
        sh = logging.StreamHandler()
        sh.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
        log.addHandler(sh)
    return log


_TOKEN_RE = re.compile(r"(\d{6,12}:[A-Za-z0-9_-]{30,})")


def clean_bot_token(v):
    """Common paste mistakes in the GitHub Secret are repaired: spaces / line breaks, quotes, a leading 'bot', or
    the whole Telegram URL pasted instead of the key (owner 17 Nov: the rotated key was refused)."""
    v = re.sub(r"\s+", "", str(v or "")).strip("'\"`")
    m = _TOKEN_RE.search(v)
    return m.group(1) if m else v


def token_shape(v):
    """What is wrong with the bot key's FORMAT - never the key itself (safe for the public log)."""
    v = str(v or "")
    if not v:
        return "missing (TELEGRAM_BOT_TOKEN secret is empty or not set)"
    if ":" not in v:
        return f"no ':' in it ({len(v)} characters) - not a bot key; copy it again from @BotFather"
    a, b = v.split(":", 1)
    probs = []
    if not a.isdigit():
        probs.append("the part before ':' is not all digits")
    if len(b) != 35:
        probs.append(f"the part after ':' has {len(b)} characters (a bot key has 35)")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", b):
        probs.append("the part after ':' has characters a bot key never has")
    return "; ".join(probs) or "format looks right (digits:35 characters) - so Telegram has a different/newer key"
