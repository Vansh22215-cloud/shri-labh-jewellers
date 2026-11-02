"""First-time data download (takes 20-60 minutes). Safe to re-run: everything is cached."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from swing.update import refresh

if __name__ == "__main__":
    print(refresh(first_time=True))
