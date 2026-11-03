"""Telegram tip-check bot (runs continuously; Windows starts it at log-on)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from swing.bot import run_forever

if __name__ == "__main__":
    run_forever()
