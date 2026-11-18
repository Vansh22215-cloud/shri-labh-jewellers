"""ONE list of open tips across every channel that sends to the owner (owner 18 Nov: "no repeat tips - smartly").
A stock that already has an open tip from ANY channel (VANTAGE, live engine) is not sent again by another channel or
another day; the blocked repeat is recorded (data/private/suppressed_repeats.csv) so the Learner can still follow it
and tell whether blocking it was right. Deliberate adds (ADD MORE) are not repeats and are not blocked."""
import pandas as pd

from .config import PRIVATE, get_logger

log = get_logger()
SUPP = PRIVATE / "suppressed_repeats.csv"


def open_stocks():
    """-> {symbol: 'VANTAGE' | 'live engine <type>'} for every open tip that was sent."""
    out = {}
    try:
        from .vantage import _load_signals
        S = _load_signals()
        for s in S.loc[S["status"].astype(str) == "open", "sym"].astype(str):
            out.setdefault(s, "VANTAGE")
    except Exception:
        pass
    try:
        from .live_engine import load_tips
        T = load_tips()
        if len(T):
            o = T[T["status"].astype(str) == "open"]
            for s, t in zip(o["symbol"].astype(str), o["type"].astype(str)):
                if t != "INTRADAY":                                   # same-day trades close by 3:15 pm
                    out.setdefault(s, f"live engine {t}")
    except Exception:
        pass
    return out


def already_open(sym, channel):
    """-> the channel that already holds an open tip on `sym` (other than an exact re-send handled elsewhere), else None."""
    return open_stocks().get(str(sym))


def record_suppressed(sym, channel, held_by, day, ref_price=None, stop=None, why="already an open tip"):
    """Keep the blocked repeat so the Learner can follow it like any idea."""
    try:
        row = pd.DataFrame([{"day": str(day)[:10], "symbol": sym, "channel": channel, "held_by": held_by,
                             "ref_price": ref_price, "stop": stop, "why": why}])
        if SUPP.exists():
            old = pd.read_csv(SUPP, dtype=str)
            if ((old["day"] == str(day)[:10]) & (old["symbol"] == str(sym)) & (old["channel"] == channel)).any():
                return
            row = pd.concat([old, row.astype(str)], ignore_index=True)
        SUPP.parent.mkdir(parents=True, exist_ok=True)
        row.to_csv(SUPP, index=False)
        log.info("Repeat tip blocked: %s from %s (already open via %s)", sym, channel, held_by)
    except Exception as e:
        log.warning("could not record a blocked repeat: %s", type(e).__name__)
