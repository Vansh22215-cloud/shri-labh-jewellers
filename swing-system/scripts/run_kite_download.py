"""Kite historical downloads (owner 19 Nov: Kite to the full; 20 Nov: its own job so a long research job can never
squeeze it out). Daemon job 'kite_download' on weekdays from 6:55 pm, right after the nightly job, while the day's
Kite login is valid: Kite daily candles for every NSE stock since 2011 (no nightly limit until complete), then
15-minute / 5-minute history for the top-300, then the coverage report. Not logged in -> one Telegram note."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if __name__ == "__main__":
    from swing.config import on_github, load_settings
    from swing.daemon import claim, retry_later
    if on_github() and not claim("kite_download"):
        print("kite_download: already done (skipped)")
        sys.exit(0)
    from swing import kite, kite_daily, kite_history
    s = load_settings()
    if not kite.logged_in():
        kite.report_unavailable(s, "Kite history download (evening)", why="Kite is not logged in this evening")
        sys.exit(0)
    r = kite_daily.download(max_requests=20000 if kite_daily.coverage() < 0.9 else 4000)
    print("kite daily:", r)
    if kite_daily.coverage() >= 0.9:
        print("kite 15/5-minute:", kite_history.run())
        try:
            print("coverage:", kite_daily.coverage_report())
        except Exception as e:
            print("coverage report failed:", type(e).__name__)
    elif r.get("stopped") or r.get("requests", 0) >= 20000:
        retry_later("kite_download", minutes=10, max_tries=6)       # continue in the next run tonight
    try:
        from swing.ci_save import save
        save("kite history download")
    except Exception as e:
        print("save failed:", e)
