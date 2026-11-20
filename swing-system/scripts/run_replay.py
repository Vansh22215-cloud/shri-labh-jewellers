"""Once: the practice trader replayed on the last 5 market days (Kite minute candles) -> 5 dashboards, one by one,
and a summary on Telegram (owner 20 Nov). Needs today's Kite login; runs outside market hours."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if __name__ == "__main__":
    from swing.config import DATA, load_settings
    from swing import kite, replay
    if not kite.logged_in():
        kite.report_unavailable(load_settings(), "Practice replay of the last 5 days", why="Kite is not logged in")
        sys.exit(0)
    try:
        out = replay.run(5)
        (DATA / "replay_done.txt").write_text(str(out))
        print("replay:", [(o["day"], o["net"]) for o in out])
    except Exception as e:
        print("replay failed:", type(e).__name__, str(e)[:200])
        w = DATA / "replay_wait.txt"
        n = int(w.read_text() or 0) + 1 if w.exists() else 1
        w.write_text(str(n))                       # the runner waits 30 minutes before the next try
        if n >= 6:
            (DATA / "replay_done.txt").write_text(f"gave up after {n} tries: {type(e).__name__}")
    try:                                   # changed Kite files -> the private R2 bucket (when set up)
        from swing import r2
        r2.push()
    except Exception as e:
        print("R2 upload failed:", type(e).__name__)
    try:
        from swing.ci_save import save
        save("practice replay")
    except Exception as e:
        print("save failed:", e)
