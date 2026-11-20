"""Kite historical downloads in small chunks (owner 20 Nov: "whatever Kite is giving - go for it ... right now").
Daemon job 'kite_download': whenever the day's Kite login is valid, outside market hours (never 8:45 am - 3:50 pm
on weekdays), ~10 minutes of requests per run, repeated until everything Kite has is downloaded:
  1) daily candles of every NSE stock + indices, all available (kite_daily), then the coverage report;
  2) 60/15/5/1-minute candles of the current top-300 (kite_candles), then their report.
Not logged in -> one Telegram note a day. Kite data only; nothing here touches live tips or rules."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

CHUNK = 1500                     # requests per run (~9-10 minutes at Kite's 3 a second)

if __name__ == "__main__":
    from swing.config import on_github, load_settings
    from swing.daemon import claim, retry_later
    if on_github() and not claim("kite_download"):
        print("kite_download: already running/done (skipped)")
        sys.exit(0)
    from swing import kite, kite_daily, kite_candles
    s = load_settings()
    if not kite.logged_in():
        kite.report_unavailable(s, "Kite history download", why="Kite is not logged in")
        sys.exit(0)
    if kite_daily.coverage() < 0.999:
        r = kite_daily.download(max_requests=CHUNK)
        print("kite daily:", r)
        if kite_daily.coverage() >= 0.9:
            try:
                print("coverage:", kite_daily.coverage_report())
            except Exception as e:
                print("coverage report failed:", type(e).__name__)
    else:
        print("kite candles:", kite_candles.step(max_requests=CHUNK))
        kite_candles.report()
    if not (kite_daily.coverage() >= 0.999 and kite_candles.progress()["complete"]):
        retry_later("kite_download", minutes=1, max_tries=400)        # next chunk in the next minute
    try:
        from swing.ci_save import save
        save("kite history download")
    except Exception as e:
        print("save failed:", e)
