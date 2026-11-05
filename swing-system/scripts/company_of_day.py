"""Company of the day: refresh ~120 companies' statements and send the best-scoring one to Telegram.
On GitHub the always-on run (swing/daemon.py) starts this every weekday evening after the trades message,
and retries it (up to 3 times) if Telegram did not accept the message."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from swing.company_research import run

if __name__ == "__main__":
    from swing.config import on_github, public_print
    from swing.daemon import claim, failed
    if on_github() and not claim("company"):
        print("company: already done (skipped)")
        sys.exit(0)
    try:
        res, msg = run(send="--dry" not in sys.argv,
                       batch=int(sys.argv[sys.argv.index("--batch") + 1]) if "--batch" in sys.argv else 120)
        public_print(msg, "company message")
        print("company:", res)
        if "failed" in res.lower() or "not set up" in res.lower():
            failed("company")
    except Exception as e:
        print("company of the day failed:", type(e).__name__, e)
        failed("company")
    try:   # on GitHub: keep the results for the next run (no Claude needed)
        from swing.ci_save import save
        print("save:", save("company of the day"))
    except Exception as e:
        print("saving results failed:", e)
