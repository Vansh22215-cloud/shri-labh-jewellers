"""Daily research session: test ONE pre-registered idea from IMPROVEMENTS.md, refresh the market-regime
study, and send a short Telegram summary. (Scheduled weekdays 20:17 IST.)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from swing import research, telegram, weekly
from swing.config import load_settings

if __name__ == "__main__":
    s = load_settings()
    notes = []
    todo = [p for p in weekly.parse_proposals() if p.get("status") == "proposed"]
    if todo:
        notes.append(weekly.test_proposal(todo[0], s, s["live_strategy"]))
    else:
        notes.append("No untested ideas left in IMPROVEMENTS.md - Claude should add new, pre-registered ones.")
    research.run()
    notes.append(research.today_line())
    msg = "🔬 Daily research\n" + "\n".join(f"• {n}" for n in notes) + f"\n{len(todo) - 1 if todo else 0} ideas left to test."
    print(msg)
    # research results stay in the reports/dashboard; no Telegram (owner wants only actionable messages)
