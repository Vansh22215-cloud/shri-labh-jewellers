"""VANTAGE INDICATOR scan of every NSE stock (daemon jobs 'vantage' at 3:40 pm with Kite's candle, 'vantage2' at
6:50 pm with Yahoo's when the first had no Kite data)."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from swing.config import redact  # noqa: E402
from swing import vantage  # noqa: E402

if __name__ == "__main__":
    job = os.environ.get("SWING_CLAIMED", "vantage")
    try:
        r = vantage.run(source="kite" if job == "vantage" else "yahoo")
        print("vantage:", r)
        if job == "vantage2" and not r.get("ok") and str(r.get("why", "")).startswith("prices not ready"):
            from swing.daemon import retry_later
            retry_later("vantage2", minutes=20, max_tries=12)   # Yahoo lags: try again every 20 min (to ~11 pm)
    except Exception as e:
        print("vantage failed:", redact(f"{type(e).__name__}: {e}"))
        raise
