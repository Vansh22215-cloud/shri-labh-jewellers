"""Weekly self-improvement session entry point (Task Scheduler, Saturdays)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from swing.weekly import run

if __name__ == "__main__":
    notes = run()
    from swing.config import public_print
    public_print("\n".join(notes), "weekly notes")
    from swing import telegram
    from swing.config import load_settings
    telegram.send(load_settings(), "🗓 Weekly self-check\n" + "\n".join(f"• {n}" for n in notes)[:3500] +
                  "\nResearch, not advice.")
    try:   # on GitHub: keep the results for the next run (no Claude needed)
        from swing.ci_save import save
        print("save:", save("weekly run"))
    except Exception as e:
        print("saving results failed:", e)

