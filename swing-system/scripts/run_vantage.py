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
        print("vantage:", vantage.run(source="kite" if job == "vantage" else "yahoo"))
    except Exception as e:
        print("vantage failed:", redact(f"{type(e).__name__}: {e}"))
        raise
