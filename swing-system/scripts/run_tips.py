"""Replays the owner's tips (tips/inbox.json) on Kite's 1-minute candles -> results/tip_check.md + Telegram."""
import sys
import traceback
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if __name__ == "__main__":
    from swing import tip_check
    try:
        tip_check.run(send=True)
    except Exception:
        print(traceback.format_exc()[-3000:])
    try:
        from swing.ci_save import save
        save("tip check")
    except Exception as e:
        print("save failed:", e)
