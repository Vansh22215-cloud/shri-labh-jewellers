"""VANTAGE INDICATOR live scan (D120): started by the daemon at 9:20 am on trading days, runs until 3:30 pm.
Every ~3 minutes: every NSE stock's VANTAGE signal on today's candle so far -> instant Telegram alert."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd  # noqa: E402

from swing import vantage  # noqa: E402
from swing.config import get_logger, redact  # noqa: E402

log = get_logger()

if __name__ == "__main__":
    sc = vantage.LiveScanner()
    while True:
        now = pd.Timestamp.now(tz="Asia/Kolkata").tz_localize(None)
        if now.hour * 60 + now.minute >= 15 * 60 + 30:
            break
        t0 = time.time()
        try:
            r = vantage.live_step(sc)
            if r.get("live_buys") or r.get("stops") or not r.get("ok"):
                log.info("VANTAGE live %s", r)
        except Exception as e:
            log.warning("VANTAGE live cycle failed: %s", redact(f"{type(e).__name__}: {e}"))
        time.sleep(max(20, 180 - (time.time() - t0)))
    log.info("VANTAGE live: market closed - stopped")
