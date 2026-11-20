"""Kite candle downloads in ~10-minute chunks (daemon job 'candles'): whenever the day's Kite login is valid and
outside market hours, repeated every minute until everything Kite has is downloaded, then the daily top-up.
Kite data only (read-only historical API). Progress: results/candle_library.md and /status."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if __name__ == "__main__":
    from swing.config import on_github, load_settings
    from swing.daemon import claim, retry_later
    if on_github() and not claim("candles"):
        print("candles: already done today (skipped)")
        sys.exit(0)
    from swing import candles, kite
    if not kite.logged_in():
        kite.report_unavailable(load_settings(), "Kite candle download", why="Kite is not logged in")
        sys.exit(0)
    r = candles.step(max_requests=1500)
    print("candles:", {k: v for k, v in r.items() if not k.endswith("_complete")})
    candles.report()
    p = candles.progress()
    if r.get("requests") and not p.get("storage_full"):
        retry_later("candles", minutes=1, max_tries=1000)      # more to do: next chunk in a minute
    try:                                   # changed Kite files -> the private R2 bucket (when set up)
        from swing import r2
        r2.push()
    except Exception as e:
        print("R2 upload failed:", type(e).__name__)
    try:
        from swing.ci_save import save
        save("candle library")
    except Exception as e:
        print("save failed:", e)
