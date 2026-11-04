"""Nightly job entry point (Windows Task Scheduler runs this on weekdays ~6:30 pm)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from swing.nightly import main

if __name__ == "__main__":
    from swing.config import on_github
    from swing.daemon import claim
    if on_github() and not claim("nightly"):
        print("nightly: already done (skipped)")
        sys.exit(0)
    main()
    try:   # company of the day (all NSE companies, deep fundamental analysis) - after the trades message
        from swing.company_research import run as company_of_day
        company_of_day()
    except Exception as e:
        print("company of the day failed:", e)
    try:   # lifelong store: keep everything collected today (prices incl. stocks Yahoo may drop, hourly, 5-min,
        from swing import archive          # news, statement years) - the research data grows every day
        archive.run_daily()
    except Exception as e:
        print("archive failed:", e)
    try:   # on GitHub: keep the results for the next run (no Claude needed)
        from swing.ci_save import save
        print("save:", save("nightly run"))
    except Exception as e:
        print("saving results failed:", e)

