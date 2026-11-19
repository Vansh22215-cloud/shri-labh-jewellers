import pandas as pd

from swing import kite_daily as kd, data_prices


def _yahoo(n=40, split_at=20, factor=2.0):
    idx = pd.bdate_range("2024-01-01", periods=n)
    close = pd.Series(100.0, index=idx)
    sp = pd.Series(0.0, index=idx)
    sp.iloc[split_at] = factor
    return pd.DataFrame({"open": close, "high": close + 1, "low": close - 1, "close": close, "adj_close": close * 0.98,
                         "volume": 1000.0, "dividends": 0.0, "splits": sp})


def test_frame_unadjusted_kite_gets_split_factors(tmp_path, monkeypatch):
    monkeypatch.setattr(kd, "BASE", tmp_path)
    y = _yahoo()
    k = y[["open", "high", "low", "close", "volume"]].copy()
    k.iloc[:20, :4] *= 2.0                                     # Kite unadjusted: old prices twice as high
    k.to_csv(tmp_path / "AAA.csv", index_label="date")
    monkeypatch.setattr(data_prices, "_load_yahoo", lambda s: y)
    kd._ADJ.clear()
    kd._ADJ["v"] = False
    f = kd.frame("AAA")
    assert abs(f["close"].iloc[0] - 100.0) < 1e-9 and abs(f["adj_close"].iloc[0] - 98.0) < 1e-9


def test_load_prefers_kite_only_when_asked(tmp_path, monkeypatch):
    monkeypatch.setattr(data_prices, "_load_yahoo", lambda s: _yahoo())
    monkeypatch.setattr(kd, "frame", lambda s: _yahoo() * 0 + 5)
    monkeypatch.delenv("SWING_PRICE_SOURCE", raising=False)
    assert data_prices.load("X")["close"].iloc[0] == 100.0
    monkeypatch.setenv("SWING_PRICE_SOURCE", "kite")
    assert data_prices.load("X")["close"].iloc[0] == 5.0


def test_download_skips_without_login(monkeypatch):
    from swing import kite
    monkeypatch.setattr(kite, "logged_in", lambda: False)
    assert kd.download() == {"skipped": "not logged in"}
