import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logging  # noqa: E402
# Tests must never write into the real logs/system.log (the daily report summarises that file).
logging.getLogger("swing").addHandler(logging.NullHandler())

from swing.config import load_strategy  # noqa: E402


@pytest.fixture
def params():
    return load_strategy("v1")


def synthetic_panel(n_sym=30, n_days=420, seed=1):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2020-01-01", periods=n_days)
    syms = [f"S{i}" for i in range(n_sym)]
    drift = rng.normal(0.0006, 0.0006, n_sym)
    rets = rng.normal(drift, 0.018, (n_days, n_sym))
    close = pd.DataFrame(100 * np.exp(np.cumsum(rets, axis=0)), index=idx, columns=syms)
    op = close.shift(1).fillna(close) * (1 + rng.normal(0, 0.004, close.shape))
    high = np.maximum(op, close) * (1 + np.abs(rng.normal(0, 0.006, close.shape)))
    low = np.minimum(op, close) * (1 - np.abs(rng.normal(0, 0.006, close.shape)))
    vol = pd.DataFrame(rng.integers(1e5, 5e5, close.shape), index=idx, columns=syms).astype(float)
    deliv = pd.DataFrame(rng.uniform(20, 80, close.shape), index=idx, columns=syms)
    P = {"open": op, "high": high, "low": low, "close": close, "volume": vol, "raw_close": close, "deliv": deliv}
    nifty = close.mean(axis=1)
    mask = pd.DataFrame(True, index=idx, columns=syms)
    return P, nifty, mask


@pytest.fixture
def panel():
    return synthetic_panel()
