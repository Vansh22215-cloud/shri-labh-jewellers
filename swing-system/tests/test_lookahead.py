"""Look-ahead checks: a signal on day t must not change when future data is added."""
import numpy as np

from swing.strategy import compute_signals
from swing import health
from tests.conftest import synthetic_panel


def test_signals_do_not_use_future(params):
    P, nifty, mask = synthetic_panel()
    full = compute_signals(P, nifty, mask, {}, params)
    for cut in (300, 350, 400):
        Pc = {k: v.iloc[:cut] for k, v in P.items()}
        part = compute_signals(Pc, nifty.iloc[:cut], mask.iloc[:cut], {}, params)
        d = P["close"].index[cut - 1]
        for k in ("score", "atr", "rs_rank"):
            a, b = full[k].loc[d], part[k].loc[d]
            assert np.allclose(a.fillna(-9), b.fillna(-9)), k
        assert (full["eligible"].loc[d] == part["eligible"].loc[d]).all()
        assert full["regime_ok"].loc[d] == part["regime_ok"].loc[d]


def test_some_signals_exist(params):
    P, nifty, mask = synthetic_panel(n_sym=60, n_days=500, seed=3)
    s = compute_signals(P, nifty, mask, {}, params)
    assert s["eligible"].values.sum() > 0


def test_unadjusted_close_reconstruction():
    import pandas as pd
    idx = pd.bdate_range("2024-01-01", periods=4)
    df = pd.DataFrame({"close": [50, 50, 50, 50], "splits": [0, 0, 2.0, 0]}, index=idx)
    raw = health.raw_unadjusted_close(df)
    assert list(raw) == [100, 100, 50, 50]
