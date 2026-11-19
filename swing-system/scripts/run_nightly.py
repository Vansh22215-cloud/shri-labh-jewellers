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
    try:   # company of the day (all NSE companies, deep fundamental analysis) - its own job, so a problem in the
        import subprocess   # trades part can never stop it; it is retried if Telegram did not take the message
        subprocess.run([sys.executable, str(Path(__file__).resolve().parent / "company_of_day.py")], timeout=1800)
    except Exception as e:
        print("company of the day failed:", e)
    try:   # lifelong store: keep everything collected today (prices incl. stocks Yahoo may drop, hourly, 5-min,
        from swing import archive          # news, statement years) - the research data grows every day
        archive.run_daily()
    except Exception as e:
        print("archive failed:", e)
    try:   # splits / bonuses: open tips re-stated in today's rupees (no false stop alerts, true results)
        from swing.corp_actions import rescale_open_tips
        print("split re-scale:", rescale_open_tips())
    except Exception as e:
        print("split re-scale failed:", e)
    try:   # VANTAGE live scorecard (owner 18 Nov): every tip sent, scored; saved to GitHub for the research
        from swing import scorecard
        scorecard.run()
    except Exception as e:
        print("scorecard failed:", e)
    try:   # EVERY tip from EVERY source tracked one by one (owner 18 Nov: "this mistake should not happen again")
        from swing import tracker
        tracker.run()
    except Exception as e:
        print("tracker failed:", e)
    try:   # THE LEARNER (owner 18 Nov): situation + journey of every idea, live vs the test, when it works, lessons
        from swing import learning
        learning.run()
    except Exception as e:
        print("learner failed:", e)
    try:   # ATLAS Foundry strategies the owner approved: silent live record, or tips + exit alerts (second yes)
        from swing import foundry_shadow
        foundry_shadow.run()
    except Exception as e:
        print("foundry strategies failed:", e)
    try:   # THE WHY-ENGINE (owner 19 Nov): expected vs actual for every finished tip, surprises, why, history check
        from swing import why_engine
        why_engine.run()
    except Exception as e:
        print("why-engine failed:", e)
    try:   # silent forward record of promoter buying (owner 18 Nov; no messages, no tip changes)
        from swing import shadow
        shadow.run()
    except Exception as e:
        print("shadow record failed:", e)
    try:   # on GitHub: keep the results for the next run (no Claude needed)
        from swing.ci_save import save
        print("save:", save("nightly run"))
    except Exception as e:
        print("saving results failed:", e)

