"""NSE trading days: weekdays minus NSE's official trading holidays (www.nseindia.com/api/holiday-master,
read once a week; a built-in copy of the remaining 2026 holidays is used if NSE cannot be reached).
On a holiday: no Kite login message, no live feed, no practice trading, and history downloads may run all day."""
import json
import time
from datetime import date

import pandas as pd

from .config import DATA, get_logger

log = get_logger()
CACHE = DATA / "nse_holidays.json"
BUILTIN = {"2026-08-15", "2026-09-14", "2026-10-02", "2026-10-20", "2026-11-10", "2026-11-24", "2026-12-25"}
_MEM = {}


def holidays():
    if "h" in _MEM and time.time() - _MEM["t"] < 3600:
        return _MEM["h"]
    h = set(BUILTIN)
    try:
        if CACHE.exists() and time.time() - CACHE.stat().st_mtime < 7 * 86400:
            h |= set(json.loads(CACHE.read_text()))
        else:
            import requests
            ua = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36",
                  "Referer": "https://www.nseindia.com/resources/exchange-communication-holidays"}
            s = requests.Session()
            s.get("https://www.nseindia.com/resources/exchange-communication-holidays", headers=ua, timeout=20)
            j = s.get("https://www.nseindia.com/api/holiday-master?type=trading", headers=ua, timeout=30).json()
            got = {str(pd.Timestamp(x["tradingDate"]).date()) for x in j.get("CM", []) if "tradingDate" in x
                   and "*" not in str(x.get("description", ""))}            # * = special (muhurat) session
            if got:
                CACHE.write_text(json.dumps(sorted(got)))
                h |= got
    except Exception as e:
        log.info("NSE holiday list: %s (built-in list used)", type(e).__name__)
    _MEM.update(h=h, t=time.time())
    return h


def is_trading_day(d=None):
    d = pd.Timestamp(d or date.today())
    return d.weekday() < 5 and str(d.date()) not in holidays()
