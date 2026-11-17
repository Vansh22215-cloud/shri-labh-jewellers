import numpy as np
import pandas as pd

from swing import ml_ranker as ml


def test_features_shape_and_target():
    rng = np.random.default_rng(1)
    c = 100 * np.exp(np.cumsum(0.01 * rng.standard_normal(400)))
    o = np.r_[c[0], c[:-1]]
    d = pd.DataFrame({"open": o, "high": np.maximum(o, c) * 1.01, "low": np.minimum(o, c) * 0.99, "close": c,
                      "volume": 1e5}, index=pd.bdate_range("2024-01-01", periods=400))
    f = ml.features(d)
    assert set(ml.STOCK) - {"rs_r20", "rs_r60"} <= set(f.columns)
    assert np.isclose(f["fwd"].iloc[100], o[111] / o[101] - 1) and f["fwd"].iloc[-1] != f["fwd"].iloc[-1]


def test_send_evening_respects_room_and_open(monkeypatch, tmp_path):
    from swing import live_engine as le
    monkeypatch.setattr(le, "TIPS_F", tmp_path / "tips.csv")
    sent = []
    monkeypatch.setattr(le, "send", lambda text, label="trade tip": sent.append(text))
    sc = pd.DataFrame({"symbol": [f"S{i}" for i in range(8)], "score": np.linspace(0.7, 0.5, 8),
                       "close": 100.0, "atr": 2.0})
    s = {"capital": 45000, "ai_top": 3, "ai_max_open": 4, "ai_picks": True}
    assert ml.send_evening("2026-11-17", s, sc) == 3
    assert "AI pick" in sent[0] and "RANK - 6/10" in sent[0]
    assert ml.send_evening("2026-11-18", s, sc) == 1          # 4 open at most, and open symbols are skipped
    # (risk caps count only tips the owner confirmed with /bought - these 3 are unconfirmed)
