import numpy as np
import pandas as pd
import pytest

from swing import catalog
from swing.families import base_indicators, family_signals
from tests.conftest import synthetic_panel


def test_catalog_loads_every_record():
    cat = catalog.load()
    assert len(cat) == 297 and not catalog.validate(cat)
    kinds = pd.Series([v["_type"] for v in cat.values()]).value_counts()
    assert kinds["chart_pattern"] == 52 and kinds["candlestick"] == 69 and kinds["indicator"] == 176


def test_pivots_are_confirmed_only_after_right_bars():
    idx = pd.bdate_range("2024-01-01", periods=12)
    low = pd.DataFrame({"A": [10, 9, 8, 7, 8, 9, 10, 11, 12, 13, 14, 15]}, index=idx, dtype=float)
    B = {"h": low + 1, "l": low}
    PLv, PLi, _, _ = catalog.pivots(B, L=3, R=3, k=3)
    # the low at bar 3 is only known at bar 6 (3 right-side bars closed)
    assert np.isnan(PLv[5, 0, -1]) and PLv[6, 0, -1] == 7 and PLi[6, 0, -1] == 3


@pytest.mark.parametrize("fam", ["cdl_cdlhammer", "cdl_cdlengulfing", "cp_double_bottom", "cp_inverse_head_and_shoulders",
                                 "cp_ascending_triangle", "cp_breakout_retest", "cp_wyckoff_spring"])
def test_catalog_family_no_lookahead(params, fam):
    P, nifty, mask = synthetic_panel(n_sym=25, n_days=420, seed=11)
    p = dict(params, family=fam)
    full = family_signals(base_indicators(P, nifty, mask, {}, p), p)
    cut = 380
    Pc = {k: v.iloc[:cut] for k, v in P.items()}
    part = family_signals(base_indicators(Pc, nifty.iloc[:cut], mask.iloc[:cut], {}, p), p)
    d = P["close"].index[cut - 1]
    assert (full["eligible"].loc[d] == part["eligible"].loc[d]).all()
