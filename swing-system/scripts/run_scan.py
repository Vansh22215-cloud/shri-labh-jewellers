"""Hourly market scan -> Telegram (run during market hours)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from swing.live_scan import run

if __name__ == "__main__":
    print(run(send="--dry" not in sys.argv))
