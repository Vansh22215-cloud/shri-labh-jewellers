"""NSE daily DELIVERY data (official 'Security-wise Delivery Position' MTO files, public archive).

Delivery % = share of the day's traded quantity that was actually delivered (bought to keep), as opposed to
intraday speculation. A breakout on high delivery suggests genuine investor buying (ROADMAP D1).
Files are cached forever in data/delivery/YYYYMMDD.csv (EQ series only); a wide panel
(date x symbol of delivery %) is built in data/delivery_panel.csv.gz.
"""
import io
import time
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from .config import DATA, get_logger
from .data_nse import _get

log = get_logger()
DELIV = DATA / "delivery"
DELIV.mkdir(parents=True, exist_ok=True)
PANEL = DATA / "delivery_panel.csv.gz"


def _parse(raw, d):
    lines = raw.decode("latin-1").splitlines()
    rows = []
    for ln in lines:
        parts = ln.split(",")
        if len(parts) >= 7 and parts[0].strip() == "20" and parts[3].strip() == "EQ":
            try:
                rows.append((parts[2].strip(), float(parts[4]), float(parts[5]), float(parts[6])))
            except ValueError:
                continue
    return pd.DataFrame(rows, columns=["symbol", "traded_qty", "deliv_qty", "deliv_pct"])


def fetch(d):
    d = pd.Timestamp(d)
    f = DELIV / f"{d:%Y%m%d}.csv"
    if f.exists():
        return f.stat().st_size > 0
    raw = _get(f"/archives/equities/mto/MTO_{d:%d%m%Y}.DAT")
    if raw is None:
        if (pd.Timestamp.today() - d).days > 3:
            f.write_text("")
        return False
    df = _parse(raw, d)
    df.to_csv(f, index=False)
    time.sleep(0.3)
    return True


def download(dates, workers=2):
    dates = [pd.Timestamp(x) for x in dates]
    todo = [d for d in dates if not (DELIV / f"{d:%Y%m%d}.csv").exists()]
    log.info("Delivery files to download: %d", len(todo))
    done = 0
    with ThreadPoolExecutor(workers) as ex:
        for ok in ex.map(fetch, todo):
            done += 1
            if done % 200 == 0:
                log.info("delivery %d/%d", done, len(todo))


def build_panel():
    frames = []
    for f in sorted(DELIV.glob("*.csv")):
        if f.stat().st_size == 0:
            continue
        x = pd.read_csv(f, usecols=["symbol", "deliv_pct"])
        x["date"] = pd.Timestamp(f.stem)
        frames.append(x)
    long = pd.concat(frames)
    wide = long.pivot_table(index="date", columns="symbol", values="deliv_pct", aggfunc="last").sort_index()
    wide.to_csv(PANEL, compression="gzip")
    log.info("Delivery panel: %d days x %d symbols", *wide.shape)
    return wide


def load_panel():
    if not PANEL.exists():
        return None
    return pd.read_csv(PANEL, index_col=0, parse_dates=True)
