"""Nightly job entry point (Windows Task Scheduler runs this on weekdays ~6:30 pm)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from swing.nightly import main

if __name__ == "__main__":
    main()
