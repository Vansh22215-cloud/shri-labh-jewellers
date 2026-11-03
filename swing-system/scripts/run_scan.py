"""Hourly market scan -> Telegram (run during market hours)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from swing.live_scan import run

if __name__ == "__main__":
    from swing.config import public_print
    public_print(run(send="--dry" not in sys.argv), "scan message")
    try:   # on GitHub: keep the results for the next run (no Claude needed)
        from swing.ci_save import save
        print("save:", save("scan"))
    except Exception as e:
        print("saving results failed:", e)

