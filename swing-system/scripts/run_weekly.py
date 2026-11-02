"""Weekly self-improvement session entry point (Task Scheduler, Saturdays)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from swing.weekly import run

if __name__ == "__main__":
    for line in run():
        print(line)
