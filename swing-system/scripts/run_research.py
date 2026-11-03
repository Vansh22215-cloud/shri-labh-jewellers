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
    from swing.idea_factory import top_up
    n_per_run = int(s.get("research_ideas_per_run", 2))
    top_up(min_open=n_per_run + 2, n_new=n_per_run + 2)   # make sure ideas written on EARLIER runs are waiting
    todo = [p for p in weekly.parse_proposals() if p.get("status") == "proposed" and p.get("written", "") < str(__import__("datetime").date.today())]
    if not todo:   # first run of the day: only ideas dated before today are tested (reason on record first)
        todo = [p for p in weekly.parse_proposals() if p.get("status") == "proposed"][:0]
    for prop in todo[:n_per_run]:
        notes.append(weekly.test_proposal(prop, load_settings(), s["live_strategy"]))
        if notes[-1].startswith("PROMOTED"):
            notes.append("🎉 Upgrade adopted - tomorrow's trades use the improved rules.")
            break
    if not todo:
        notes.append("No idea old enough to test yet (new ideas are written today and tested next run).")
    new = top_up(min_open=n_per_run + 2, n_new=n_per_run + 2)
    if new:
        notes.append("New ideas written for the next runs: " + "; ".join(new))
    research.run()
    notes.append(research.today_line())
    queued = len([p for p in weekly.parse_proposals() if p.get("status") == "proposed"])
    msg = "🔬 Daily research\n" + "\n".join(f"• {n}" for n in notes) + f"\n{queued} ideas queued for the next runs (about 900 in the library)."
    print(msg)
    print(telegram.send(load_settings(), msg))   # owner wants every result on Telegram
