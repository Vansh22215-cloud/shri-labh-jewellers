"""Time Machine (adapted from 'trader-timemachine'): replay a trade 10,000 times before risking a rupee.

Each replay builds a possible future, bar by bar, by drawing (at random, with replacement) real bars from the
instrument's OWN recent history - daily bars of the last year for swing trades, 15-minute bars for short charts -
as moves relative to the previous close (so gaps, wide days and quiet days all appear as often as they really
did). Each replay stops at the first touch of the target or the stop; if both fall in the same bar the stop is
counted first (conservative). Result: out of 100 replays, how many hit the target first, the stop first, or
neither within the time allowed. Seeded, so the same trade gives the same numbers.

It is a simulation, not a prediction: it cannot know about results, news or halts the recent bars never had.
"""
import numpy as np
import pandas as pd

N = 10000


def moves(bars, lookback=250):
    """Relative (high, low, close) of each bar vs the previous close, from the last `lookback` bars."""
    b = bars[["high", "low", "close"]].astype(float).dropna().tail(lookback + 1)
    prev = b["close"].shift(1)
    m = pd.DataFrame({"h": b["high"] / prev, "l": b["low"] / prev, "c": b["close"] / prev}).dropna()
    m = m[(m["h"] >= m["l"]) & (m["l"] > 0)]
    return m.to_numpy()


def simulate(bars, side, entry, stop, target, horizon, n=N, seed=19, lookback=250):
    """-> {'target','stop','neither' (out of 100), 'median_bars', 'n', 'sample'} or None if too little history."""
    mv = moves(bars, lookback)
    if len(mv) < 30 or not entry or not stop or not target or horizon < 1:
        return None
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(mv), size=(n, int(horizon)))
    H, L, C = mv[idx, 0], mv[idx, 1], mv[idx, 2]
    prev = entry * np.cumprod(np.concatenate([np.ones((n, 1)), C[:, :-1]], axis=1), axis=1)
    hi, lo = prev * H, prev * L
    if side == "sell":
        hit_t, hit_s = lo <= target, hi >= stop
    else:
        hit_t, hit_s = hi >= target, lo <= stop
    big = int(horizon) + 1
    first_t = np.where(hit_t.any(1), hit_t.argmax(1), big)
    first_s = np.where(hit_s.any(1), hit_s.argmax(1), big)
    tgt = first_t < first_s                      # same bar -> stop first
    stp = (first_s <= first_t) & (first_s < big)
    nei = ~tgt & ~stp
    done = np.where(tgt, first_t, np.where(stp, first_s, big))
    return {"target": round(tgt.mean() * 100, 1), "stop": round(stp.mean() * 100, 1),
            "neither": round(nei.mean() * 100, 1),
            "median_bars": int(np.median(done[done < big]) + 1) if (done < big).any() else None,
            "n": n, "sample": len(mv)}


def line(tm, unit="days", source="its own last year of daily bars"):
    """One plain-words line for a reply / message."""
    if not tm:
        return None
    med = f"; usually decided within {tm['median_bars']} {unit}" if tm.get("median_bars") else ""
    if tm["neither"] >= 60:
        verdict = "most likely NEITHER level is reached in the time allowed (the levels are far for this window)"
    elif tm["target"] > tm["stop"] + 5:
        verdict = "more often the target"
    elif tm["stop"] > tm["target"] + 5:
        verdict = "more often the stop"
    else:
        verdict = "close to a coin flip"
    return (f"Out of 100 replays: 🎯 {tm['target']:.0f} hit the target first, ❌ {tm['stop']:.0f} the stop first, "
            f"⌛ {tm['neither']:.0f} neither - {verdict}{med}. (10,000 replays from {source}.)")
