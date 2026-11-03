"""Answer waiting Telegram messages once, then exit (GitHub Actions runs this every hour)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from swing.bot import poll_once

if __name__ == "__main__":
    print("answered", poll_once())
    try:   # on GitHub: keep the results for the next run (no Claude needed)
        from swing.ci_save import save
        print("save:", save("bot"))
    except Exception as e:
        print("saving results failed:", e)

