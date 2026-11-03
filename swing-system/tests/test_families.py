"""Every strategy family must run, produce some signals on random data, and never look ahead."""
import numpy as np
import pytest

from swing import backtest
from swing.families import DELIVERY_FAMILIES, FAMILIES, LIBRARY_FAMILIES, SHORT_FAMILIES, base_indicators, family_signals
from tests.conftest import synthetic_panel


@pytest.mark.parametrize("fam", FAMILIES + SHORT_FAMILIES + DELIVERY_FAMILIES + LIBRARY_FAMILIES)
def test_family_runs_and_backtests(params, fam):
    P, nifty, mask = synthetic_panel(n_sym=60, n_days=520, seed=5)
    B = base_indicators(P, nifty, mask, {}, params)
    p = dict(params, family=fam, use_regime_filter=False)
    sig = family_signals(B, p)
    assert sig["eligible"].shape == P["close"].shape
    eq, tr, _ = backtest.run(P, sig, p, P["close"].index[260], P["close"].index[-1], 45000)
    assert np.isfinite(eq).all()


@pytest.mark.parametrize("fam", FAMILIES + SHORT_FAMILIES + DELIVERY_FAMILIES + LIBRARY_FAMILIES)
def test_family_no_lookahead(params, fam):
    P, nifty, mask = synthetic_panel(n_sym=40, n_days=480, seed=7)
    p = dict(params, family=fam)
    full = family_signals(base_indicators(P, nifty, mask, {}, p), p)
    cut = 430
    Pc = {k: v.iloc[:cut] for k, v in P.items()}
    part = family_signals(base_indicators(Pc, nifty.iloc[:cut], mask.iloc[:cut], {}, p), p)
    d = P["close"].index[cut - 1]
    assert (full["eligible"].loc[d] == part["eligible"].loc[d]).all()
    assert np.allclose(full["score"].loc[d].fillna(-9), part["score"].loc[d].fillna(-9))


def test_delivery_filter_uses_only_past_average(params):
    P, nifty, mask = synthetic_panel(n_sym=30, n_days=420, seed=9)
    B = base_indicators(P, nifty, mask, {}, params)
    d = P["close"].index[300]
    expected = P["deliv"].iloc[280:300].mean()       # the 20 days BEFORE d
    assert np.allclose(B["deliv_avg"].loc[d].values, expected.values)
