"""Data update routine used by first-time setup and the nightly job."""
import pandas as pd

from . import data_nse, data_prices, universe
from .config import get_logger, load_state, save_state

log = get_logger()


def trading_calendar():
    nifty = data_prices.load("NIFTY50")
    return nifty.index if nifty is not None else pd.DatetimeIndex([])


def refresh(first_time=False, hist_start="2012-09-01"):
    """Download/refresh everything. Returns a dict describing what happened."""
    info = {"errors": []}
    idx_syms = list(data_prices.INDEX_TICKERS)
    if first_time:
        data_prices.download_full(idx_syms)
    else:
        data_prices.update(idx_syms)
    cal = trading_calendar()
    if len(cal) == 0:
        info["errors"].append("Could not download Nifty 50 index data (Yahoo down?)")
        return info

    # Official NSE bhavcopies: every 5th trading day since hist_start + every one of the last 15 days.
    hist_days = cal[cal >= pd.Timestamp(hist_start)]
    # A fresh machine (e.g. GitHub Actions) with the committed universe list only fetches recent days.
    have_hist = len(list(universe.BHAV.glob("*.csv"))) >= 300 or not universe.UNIVERSE_FILE.exists()
    sample = (set(hist_days[::5]) if have_hist else set()) | set(cal[-15:])
    # Today's file too (Yahoo's calendar may not include today yet).
    today = pd.Timestamp.today().normalize()
    if today.weekday() < 5:
        sample.add(today)
    sample = sorted(sample)
    data_nse.download_bhav_dates([d.date() for d in sample])

    hist = universe.build_history()
    syms = set(hist["symbol"])
    n500 = data_nse.nifty500_list()
    syms |= set(n500["Symbol"].dropna())
    syms = sorted(syms)
    info["n_symbols"] = len(syms)
    if first_time:
        data_prices.download_full(syms)
    else:
        data_prices.update(syms)
    try:
        data_nse.deals()
    except Exception as e:
        info["errors"].append(f"Bulk/block deals unavailable: {e}")
    data_prices.liquid_fund_nav()
    try:   # daily FII/DII positioning + delivery data (ROADMAP I1, D1)
        from . import data_delivery, intel_positioning
        recent = [d for d in cal[-10:]]
        intel_positioning.download(recent)
        intel_positioning.build_panel()
        data_delivery.download(recent)
        from . import intel_fno, intel_global
        intel_fno.download(recent)
        intel_global.refresh()
        from . import intel_news
        intel_news.fetch()
        data_delivery.build_panel()
    except Exception as e:
        info["errors"].append(f"positioning/delivery update failed: {e}")
    st = load_state()
    st["last_data_update"] = str(pd.Timestamp.now())
    save_state(st)
    return info
