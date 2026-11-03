"""Builds the inputs (price panel, universe mask, sectors, signals) shared by backtest and live run."""
import pandas as pd

from . import data_nse, data_prices, health, universe
from .strategy import compute_signals
from .config import get_logger

log = get_logger()


def build(params, use_results_filter=False, start="2011-06-01"):
    hist = universe.load_history()
    n500 = data_nse.nifty500_list()
    syms = sorted(set(hist["symbol"]) | set(n500["Symbol"].dropna()))
    q = health.load_quarantine()
    clean = [s for s in syms if s not in q]
    P = data_prices.panel(clean, start=start)
    if not P:
        raise RuntimeError("No price data available")
    nifty = data_prices.adjusted(data_prices.load("NIFTY50"))["close"]
    # Use only dates on which Nifty traded (drops stray non-trading-day rows from Yahoo).
    idx = P["close"].index.intersection(nifty.index)
    # Never use today's bar before the market has closed (it would be a half-day, incomplete bar).
    now = pd.Timestamp.now(tz="Asia/Kolkata").tz_localize(None)
    if now.hour < 16:
        idx = idx[idx < now.normalize()]
    P = {k: v.loc[idx] for k, v in P.items()}
    mask = universe.membership_mask(hist, idx, list(P["close"].columns))
    # Live: today's universe = most recent month's list (same rule, latest data).
    industry = dict(zip(n500["Symbol"], n500["Industry"]))
    results_soon = None
    if use_results_filter:
        from .fundamentals import results_soon_mask
        results_soon = results_soon_mask(list(P["close"].columns), idx,
                                         days_ahead=int(round(params["exclude_results_within_days"] * 7 / 5)))
    sig = compute_signals(P, nifty, mask, industry, params, results_soon=results_soon)
    coverage = {
        "universe_symbols_ever": int(hist["symbol"].nunique()),
        "with_price_data": int(sum(1 for s in hist["symbol"].unique() if s in P["close"].columns)),
        "quarantined": len(q),
    }
    return P, sig, nifty, industry, coverage, hist
