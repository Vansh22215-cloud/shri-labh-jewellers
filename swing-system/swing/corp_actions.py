"""Stock splits and bonus issues for OPEN tips (micro-inspection 18 Nov: 82 NSE stocks had a split/bonus in 12 months).
After a 2:1 split the price halves overnight while the stored buy price / stop-loss / targets stay in old rupees ->
false "stop-loss hit, exit now" alerts, fake signals, fake -50% results in the Learner.
  1) split_factor(): product of Yahoo's split ratios after a date (2.0 = 2-for-1; price after = before / 2).
  2) rescale_open_tips(): every evening, open VANTAGE signals and open live-engine tips are re-stated in today's rupees
     (once per split; the applied split is remembered in the row), so stops and targets stay correct.
  3) looks_like_split(): same-day guard for the morning a split takes effect (before the evening re-scale): NSE price
     bands make a one-day fall of more than 25% almost impossible except through a split/bonus, so stop alerts wait."""
import pandas as pd

from .config import get_logger

log = get_logger()
SPLIT_GAP = 0.75        # price below 75% of yesterday's close in one session -> treat as a corporate action


def split_factor(d, since, until=None):
    if d is None or "splits" not in d or not len(d):
        return 1.0
    s = d["splits"]
    m = (s.index > pd.Timestamp(str(since)[:10])) & (s > 0)
    if until is not None:
        m &= s.index <= pd.Timestamp(str(until)[:10])
    f = 1.0
    for v in s[m]:
        if v and v == v and v > 0 and abs(v - 1) > 1e-9:
            f *= float(v)
    return f


def looks_like_split(price, prev_close):
    try:
        return float(prev_close) > 0 and float(price) < SPLIT_GAP * float(prev_close)
    except (TypeError, ValueError):
        return False


def _scale(v, f):
    try:
        x = float(v)
        return f"{x / f:.2f}" if x == x else v
    except (TypeError, ValueError):
        return v


def rescale_open_tips(load=None):
    """-> number of open tips re-stated. Splits are applied once (column split_done = last split date applied)."""
    from . import data_prices
    load = load or data_prices.load
    n = 0
    try:
        from . import vantage
        S = vantage._load_signals()
        if len(S):
            if "split_done" not in S:
                S["split_done"] = ""
            for i, r in S[S["status"].astype(str) == "open"].iterrows():
                d = load(r["sym"])
                since = r["split_done"] if str(r["split_done"]) not in ("", "nan") else r["signal"]
                f = split_factor(d, since)
                if f != 1.0:
                    for c in ("close", "stop", "limit_test"):
                        if c in S:
                            S.loc[i, c] = _scale(r[c], f)
                    S.loc[i, "split_done"] = str(d.index[-1].date())
                    log.info("Split/bonus: VANTAGE %s re-stated (factor %.3f)", r["sym"], f)
                    n += 1
            if n:
                vantage._save_signals(S)
    except Exception as e:
        log.warning("split re-scale (VANTAGE) failed: %s", type(e).__name__)
    try:
        from . import live_engine
        with live_engine._LOCK:
            T = live_engine.load_tips()
            if len(T):
                if "split_done" not in T:
                    T["split_done"] = ""
                m = 0
                for i, r in T[(T["status"].astype(str) == "open") & (T["type"].astype(str) == "NORMAL")].iterrows():
                    d = load(str(r["symbol"]))
                    since = r["split_done"] if str(r["split_done"]) not in ("", "nan") else str(r["day"])[:10]
                    f = split_factor(d, since)
                    if f != 1.0:
                        for c in ("entry", "stop", "hi_since", "lo_since"):
                            T.loc[i, c] = _scale(r[c], f)
                        T.loc[i, "targets"] = "/".join(_scale(x, f) for x in str(r["targets"]).split("/") if x)
                        T.loc[i, "split_done"] = str(d.index[-1].date())
                        log.info("Split/bonus: live tip %s re-stated (factor %.3f)", r["symbol"], f)
                        m += 1
                if m:
                    live_engine.write_tips(T)
                n += m
    except Exception as e:
        log.warning("split re-scale (live tips) failed: %s", type(e).__name__)
    return n
