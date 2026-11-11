"""Saturday job: weekly self-checks (logged), then the owner's weekly summary + the week's full report file."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from swing.weekly import run

if __name__ == "__main__":
    from swing.config import on_github
    from swing.daemon import claim
    if on_github() and not claim("weekly"):
        print("weekly: already done (skipped)")
        sys.exit(0)
    notes = run()
    from swing.config import public_print
    public_print("\n".join(notes), "weekly notes")
    from swing import telegram
    from swing.config import load_settings
    # owner's choice: the Saturday message is channel scorecards + every tip of the week (technical notes stay in the log)
    try:
        from swing.tip_status import weekly_summary
        telegram.send(load_settings(), weekly_summary(), html=True, label="weekly summary")
    except Exception as e:
        print("weekly summary failed:", type(e).__name__, e)
    try:   # the full report of the week's last evening, once a week
        import json
        from pathlib import Path as _P
        from swing.config import DATA
        rep = json.loads((DATA / "state.json").read_text()).get("last_report")
        if rep and _P(rep).exists():
            telegram.send_document(load_settings(), _P(rep), "This week's full report (open in your browser)")
    except Exception as e:
        print("weekly report file failed:", type(e).__name__)
    try:   # on GitHub: keep the results for the next run (no Claude needed)
        from swing.ci_save import save
        print("save:", save("weekly run"))
    except Exception as e:
        print("saving results failed:", e)

