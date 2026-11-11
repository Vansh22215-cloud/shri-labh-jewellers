import numpy as np
import pandas as pd

from swing import timemachine as tm


def _bars(drift, vol=0.01, n=300, seed=1):
    r = np.random.default_rng(seed).normal(drift, vol, n)
    c = 100 * np.exp(np.cumsum(r))
    return pd.DataFrame({"high": c * 1.006, "low": c * 0.994, "close": c})


def test_drift_shows_up_in_the_odds_and_is_repeatable():
    up = tm.simulate(_bars(0.004), "buy", 100, 95, 105, 20)
    down = tm.simulate(_bars(-0.004), "buy", 100, 95, 105, 20)
    assert up["target"] > up["stop"] and down["stop"] > down["target"]
    assert abs(up["target"] + up["stop"] + up["neither"] - 100) < 0.2
    assert tm.simulate(_bars(0.004), "buy", 100, 95, 105, 20) == up            # seeded: same numbers
    s = tm.simulate(_bars(-0.004), "sell", 100, 105, 95, 20)
    assert s["target"] > s["stop"]                                             # sell side mirrors


def test_far_levels_say_neither_and_little_history_says_nothing():
    t = tm.simulate(_bars(0.0, vol=0.002), "buy", 100, 80, 120, 5)
    assert t["neither"] > 90 and "NEITHER" in tm.line(t)
    assert tm.simulate(_bars(0.0, n=10), "buy", 100, 95, 105, 5) is None
    assert tm.line(None) is None
