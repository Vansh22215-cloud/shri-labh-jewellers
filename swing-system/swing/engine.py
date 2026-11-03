"""Builds the inputs (price panel, universe mask, sectors, signals) shared by backtest and live run."""
import pandas as pd

from . import data_nse, data_prices, health, universe
from .strategy import compute_signals
from .config import get_logger

log = get_logger()


def build(params, use_results_filter=False, start="2011-06-01", extra_bar=None):
    """extra_bar (optional, live scans only): {"date", "open", "high", "low", "close", "volume" (Series by
    symbol), "nifty": float} = today's PROVISIONAL bar so far. Signals on it are provisional until the close."""
    hist = universe.load_history()
    n500 = data_nse.nifty500_list()
    syms = sorted(set(hist["symbol"]) | set(n500["Symbol"].dropna()))
    q = health.load_quarantine()
    clean = [s for s in syms if s not in q]
    # Company shares only: a symbol that still trades today but is NOT in NSE's equity list is an ETF/fund
    # (e.g. LIQUIDBEES, GOLDBEES) and is excluded. Delisted stocks are kept (survivorship).
    try:
        from .tipcheck import equity_list
        eq = set(equity_list()["SYMBOL"])
        recent = pd.Timestamp.today() - pd.Timedelta(days=15)
        def _is_fund(sym):
            if sym in eq:
                return False
            f = data_prices.PRICES / f"{sym}.csv"
            if not f.exists():
                return False
            last = f.read_text().rstrip().rsplit("\n", 1)[-1].split(",", 1)[0]
            return pd.Timestamp(last) >= recent
        funds = [s for s in clean if _is_fund(s)]
        clean = [s for s in clean if s not in set(funds)]
        log.info("Excluded %d ETFs/funds from the stock universe", len(funds))
    except Exception as e:
        log.warning("ETF filter unavailable: %s", e)
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
    if extra_bar is not None:
        d = pd.Timestamp(extra_bar["date"]).normalize()
        if d not in idx:
            for k in ("open", "high", "low", "close", "volume"):
                P[k].loc[d] = extra_bar[k].reindex(P[k].columns)
            P["raw_close"].loc[d] = extra_bar["close"].reindex(P["raw_close"].columns)
            nifty = nifty.copy()
            nifty.loc[d] = extra_bar["nifty"]
            idx = P["close"].index
    try:   # NSE delivery % (ROADMAP D1); optional - families that need it check for it
        from .data_delivery import load_panel
        dp = load_panel()
        if dp is not None:
            P["deliv"] = dp.reindex(index=idx, columns=P["close"].columns)
    except Exception as e:
        log.warning("delivery panel unavailable: %s", e)
    try:   # historical results dates -> reaction days (for the earnings-drift family)
        from .fundamentals import results_day_mask
        P["results_day"] = results_day_mask(list(P["close"].columns), idx)
    except Exception as e:
        log.warning("results-day mask unavailable: %s", e)
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
