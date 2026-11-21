"""Old task name from the GitHub "Run workflow" menu (its default is "nightly"). Those jobs were removed in the
21 Nov rebuild (D162); every job now runs inside the always-on run, so this simply starts it (same as "bot")."""
import runpy
from pathlib import Path

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).resolve().parent / "bot_poll.py"), run_name="__main__")
