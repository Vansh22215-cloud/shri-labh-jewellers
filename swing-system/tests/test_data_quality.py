import numpy as np
import pandas as pd

from swing import data_prices, health


def _df(closes, splits=None):
    idx = pd.bdate_range("2024-01-01", periods=len(closes))
    c = pd.Series(closes, index=idx, dtype=float)
    return pd.DataFrame({"open": c, "high": c * 1.01, "low": c * 0.99, "close": c, "adj_close": c,
                         "volume": 1000.0, "dividends": 0.0, "splits": splits or [0.0] * len(closes)}, index=idx)


def test_benchmark_spike_repair():
    df = _df([100, 101, 10.1, 10.2, 102, 103])
    fixed = data_prices.repair_isolated_spikes(df)
    assert fixed["close"].pct_change().abs().max() < 0.05


def test_unadjusted_bonus_jump_is_quarantined():
    closes = list(np.linspace(100, 110, 60)) + list(np.linspace(55, 60, 60))   # bonus not adjusted
    probs = health.check_symbol("X", _df(closes), {})
    assert any("jump" in p for p in probs)


def test_clean_series_passes_and_constant_ratio_ok():
    closes = list(np.linspace(100, 150, 120))
    df = _df(closes)
    nse = df["close"].iloc[::5] * 1.09   # constant offset (e.g. demerger back-adjustment) is fine...
    nse.iloc[-3:] = df["close"].iloc[::5].iloc[-3:]  # ...as long as recent prices match exactly
    probs = health.check_symbol("X", df, {"X": nse})
    assert not any("erratic" in p for p in probs)


def test_erratic_disagreement_is_quarantined():
    closes = list(np.linspace(100, 150, 200))
    df = _df(closes)
    nse = df["close"].iloc[::5].copy()
    nse.iloc[::2] *= 1.05
    probs = health.check_symbol("X", df, {"X": nse})
    assert any("erratic" in p for p in probs)
