"""Audit 17 Nov: TRUNCATION TEST for every live strategy - the decision for day X computed with data up to X must be
identical to the decision for day X computed with the full history (any difference = the code peeks at the future)."""
import numpy as np
import pandas as pd

from swing import confirmations, high_prob, orderflow, positional
from swing.rolling_profile import signals as rcp


def _data(n=600, seed=11):
    rng = np.random.default_rng(seed)
    c = 100 * np.exp(np.cumsum(0.0008 + 0.02 * rng.standard_normal(n)))
    o = np.r_[c[0], c[:-1]] * (1 + 0.003 * rng.standard_normal(n))
    h = np.maximum(o, c) * (1 + np.abs(0.01 * rng.standard_normal(n)))
    l = np.minimum(o, c) * (1 - np.abs(0.01 * rng.standard_normal(n)))
    v = rng.integers(1e5, 1e6, n).astype(float)
    return pd.DataFrame({"open": o, "high": h, "low": l, "close": c, "adj_close": c, "volume": v},
                        index=pd.bdate_range("2023-01-02", periods=n))


def test_rolling_candle_profile_never_uses_future_bars():
    d = _data()
    full = rcp(d[["open", "high", "low", "close", "volume"]], "price")
    for x in (300, 377, 450, 599):
        part = rcp(d.iloc[:x + 1][["open", "high", "low", "close", "volume"]], "price")
        assert bool(part["buy"].iloc[-1]) == bool(full["buy"].iloc[x])
        assert bool(part["sell"].iloc[-1]) == bool(full["sell"].iloc[x])


def test_confirmations_and_order_blocks_never_use_future_bars():
    d = _data(seed=5)
    o, h, l, c = (d[k].values for k in ("open", "high", "low", "close"))
    f_vix, f_wt, f_sq = confirmations.vix_fix_spike(h, l, c), confirmations.wavetrend_oversold(h, l, c), \
        confirmations.squeeze_on(h, l, c)
    f_msb, f_sw = confirmations.msb_order_block(o, h, l, c), confirmations.swing_low_hold(o, h, l, c)
    f_ob = orderflow.order_block_touches(d)[0]
    for x in (250, 333, 480, 599):
        p = d.iloc[:x + 1]
        po, ph, pl, pc = (p[k].values for k in ("open", "high", "low", "close"))
        assert confirmations.vix_fix_spike(ph, pl, pc)[-1] == f_vix[x]
        assert confirmations.wavetrend_oversold(ph, pl, pc)[-1] == f_wt[x]
        assert confirmations.squeeze_on(ph, pl, pc)[-1] == f_sq[x]
        assert confirmations.msb_order_block(po, ph, pl, pc)[-1] == f_msb[x]
        assert confirmations.swing_low_hold(po, ph, pl, pc)[-1] == f_sw[x]
        assert orderflow.order_block_touches(p)[0][-1] == f_ob[x]


def test_dip_buy_and_positional_signals_use_only_past_data():
    d = _data(seed=3)
    for x in range(260, 600, 23):
        a = d.iloc[:x + 1]
        s1 = high_prob.signal(a)
        s2 = high_prob.signal(d.iloc[:x + 1].copy())
        assert (s1 is None) == (s2 is None)
        adj = high_prob.adjusted(a)
        adj["volume"] = a["volume"]
        p1 = positional.signal(adj)
        full = high_prob.adjusted(d)
        full["volume"] = d["volume"]
        p2 = positional.signal(full.iloc[:x + 1])
        assert (p1 is None) == (p2 is None)


def test_ml_features_use_only_past_data_and_target_only_future():
    from swing import ml_ranker
    d = _data(seed=9)
    f_full = ml_ranker.features(d)
    for x in (300, 450, 580):
        f_part = ml_ranker.features(d.iloc[:x + 1])
        cols = [c for c in ml_ranker.STOCK if c in f_part.columns]
        a, b = f_part[cols].iloc[-1], f_full[cols].iloc[x]
        assert np.allclose(a.fillna(-9).values, b.fillna(-9).values, rtol=1e-6, atol=1e-9)
    # the target (fwd) at day x uses open[x+1] .. open[x+11]: unknown on day x, and only used as a training label
    o = d["open"].values
    assert np.isclose(f_full["fwd"].iloc[100], o[111] / o[101] - 1)
