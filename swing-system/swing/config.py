"""Loads settings.yaml and strategy versions; defines folder paths.

Everything is relative to the project folder, so the system works wherever
the folder is copied (Windows or Linux).
"""
import json
import logging
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
PRICES = DATA / "prices"
BHAV = DATA / "bhavcopy"
FUND = DATA / "fundamentals"
EVENTS = DATA / "events"
QUARANTINE = DATA / "quarantine.json"
REPORTS = ROOT / "reports"
STOCKS = ROOT / "stocks"
JOURNAL = ROOT / "journal"
LOGS = ROOT / "logs"
STRATEGIES = ROOT / "strategies"
STATE = DATA / "state.json"
# Personal files (your trades, forwarded tips). The GitHub repository is PUBLIC: these live only in the private
# Actions cache and your own Telegram backups, never in git, logs or public artifacts.
PRIVATE = DATA / "private"
ARCHIVE = DATA / "archive"     # lifelong append-only store of everything collected (swing/archive.py)

DISCLAIMER = ("Research, not advice. No system can guarantee profit; you can lose money. "
              "You decide and place every order yourself.")

for _d in (DATA, PRICES, BHAV, FUND, EVENTS, REPORTS, STOCKS, JOURNAL, LOGS, PRIVATE, ARCHIVE):
    _d.mkdir(parents=True, exist_ok=True)
for _f in ("my_trades.csv", "closed_trades.csv", "forwarded_tips.csv"):   # one-time move from the old place
    if (DATA / _f).exists() and not (PRIVATE / _f).exists():
        (DATA / _f).rename(PRIVATE / _f)


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
    """Read settings.yaml. Missing keys fall back to safe defaults."""
    defaults = {
        "capital": 45000, "kill_switch": False, "mode": "paper",
        "paper_start_date": "2026-11-02", "paper_weeks": 8,

        "telegram_bot_token": "", "telegram_chat_id": "", "live_strategy": "v1",
        "tips_mode": "validated", "aggressive_strategy": "a1", "aggressive_hard_stop_pct": 20,
    }
    p = Path(path) if path else ROOT / "settings.yaml"
    try:
        user = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception as e:  # broken file -> safest behaviour: no tips
        logging.getLogger("swing").error("settings.yaml unreadable (%s); kill switch forced ON", e)
        user = {"kill_switch": True}
    defaults.update(user)
    # On GitHub Actions the private values come from environment variables (repository secrets), never a file.
    import os
    for env_key, key in (("TELEGRAM_BOT_TOKEN", "telegram_bot_token"), ("TELEGRAM_CHAT_ID", "telegram_chat_id")):
        if os.environ.get(env_key):
            defaults[key] = os.environ[env_key]
    # Private values (e.g. Telegram token) live in my_secrets.yaml, which is never uploaded to GitHub.
    sec = ROOT / "my_secrets.yaml"
    if path is None and sec.exists():
        try:
            defaults.update({k: v for k, v in (yaml.safe_load(sec.read_text(encoding="utf-8")) or {}).items() if v})
        except Exception as e:
            logging.getLogger("swing").error("my_secrets.yaml unreadable: %s", e)
    return defaults


def load_strategy(name):
    return json.loads((STRATEGIES / f"{name}.json").read_text(encoding="utf-8"))


def load_state():
    try:
        return json.loads(STATE.read_text())
    except Exception:
        return {}


def save_state(state):
    STATE.write_text(json.dumps(state, indent=2, default=str))


def get_logger():
    """One log file for everything; the daily report summarises it in plain English."""
    log = logging.getLogger("swing")
    if not log.handlers:
        log.setLevel(logging.INFO)
        fh = logging.FileHandler(LOGS / "system.log", encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        log.addHandler(fh)
        sh = logging.StreamHandler()
        sh.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
        log.addHandler(sh)
    return log
