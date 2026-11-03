import numpy as np
import pandas as pd
import pytest

from swing import catalog
from swing.families import base_indicators, family_signals
from tests.conftest import synthetic_panel


def test_catalog_loads_every_record():
    cat = catalog.load()
    assert len(cat) == 791 and not catalog.validate(cat)
    kinds = pd.Series([v["_type"] for v in cat.values()]).value_counts()
    assert kinds["chart_pattern"] == 148 and kinds["candlestick"] == 130 and kinds["indicator"] == 324
    assert kinds["market_structure"] == 85 and kinds["quant_feature"] == 104
    al = catalog.aliases()
    assert len(al) > 1000 and all(f"{k}/{i}" in cat for k, i in al.values() if k in kinds.index)


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


V2_FAMS = [f for f in catalog.families() if f.startswith(("cdx_", "ms_"))] + \
    [f"cp_{x}" for x in catalog.CHART_DETECTORS[17:]]


@pytest.mark.parametrize("fam", V2_FAMS)
def test_v2_family_runs_and_has_no_lookahead(params, fam):
    P, nifty, mask = synthetic_panel(n_sym=20, n_days=420, seed=5)
    p = dict(params, family=fam)
    full = family_signals(base_indicators(P, nifty, mask, {}, p), p)
    cut = 380
    Pc = {k: v.iloc[:cut] for k, v in P.items()}
    part = family_signals(base_indicators(Pc, nifty.iloc[:cut], mask.iloc[:cut], {}, p), p)
    for d in P["close"].index[cut - 5:cut]:
        assert (full["eligible"].loc[d] == part["eligible"].loc[d]).all(), d


def test_quant_features_compute(params):
    from swing.features import QUANT_IMPL, quant_feature
    P, nifty, mask = synthetic_panel(n_sym=10, n_days=300, seed=3)
    B = base_indicators(P, nifty, mask, {}, params)
    for fid in QUANT_IMPL:
        x = quant_feature(fid, B)
        if x is not None:
            assert x.shape == B["c"].shape, fid


def test_v2_indicators_compute_without_lookahead(params):
    from swing.features import INDICATOR_V2, indicator_v2
    P, nifty, mask = synthetic_panel(n_sym=6, n_days=330, seed=9)
    B = base_indicators(P, nifty, mask, {}, params)
    cut = 300
    Pc = {k: v.iloc[:cut] for k, v in P.items()}
    Bc = base_indicators(Pc, nifty.iloc[:cut], mask.iloc[:cut], {}, params)
    d = P["close"].index[cut - 1]
    for iid in INDICATOR_V2:
        full, part = indicator_v2(iid, B), indicator_v2(iid, Bc)
        if full is None:
            continue
        assert full.shape == B["c"].shape, iid
        a, b = full.loc[d].astype(float).values, part.loc[d].astype(float).values
        assert np.allclose(a, b, equal_nan=True, rtol=1e-6, atol=1e-9), iid
