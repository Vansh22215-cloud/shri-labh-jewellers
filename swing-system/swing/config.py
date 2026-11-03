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

DISCLAIMER = ("Research, not advice. No system can guarantee profit; you can lose money. "
              "You decide and place every order yourself.")

for _d in (DATA, PRICES, BHAV, FUND, EVENTS, REPORTS, STOCKS, JOURNAL, LOGS):
    _d.mkdir(parents=True, exist_ok=True)


def load_settings(path=None):
    """Read settings.yaml. Missing keys fall back to safe defaults."""
    defaults = {
        "capital": 45000, "kill_switch": False, "mode": "paper",
        "paper_start_date": "2026-11-02", "paper_weeks": 8,
        "claude_review": False, "claude_review_max_stocks": 6,
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
