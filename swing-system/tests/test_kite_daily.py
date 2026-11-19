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


def test_load_is_kite_first_by_default(tmp_path, monkeypatch):
    monkeypatch.setattr(data_prices, "_load_yahoo", lambda s: _yahoo())
    monkeypatch.setattr(kd, "frame", lambda s: _yahoo() * 0 + 5)
    monkeypatch.delenv("SWING_PRICE_SOURCE", raising=False)
    assert data_prices.load("X")["close"].iloc[0] == 5.0                 # Kite by default
    monkeypatch.setenv("SWING_PRICE_SOURCE", "yahoo")
    assert data_prices.load("X")["close"].iloc[0] == 100.0               # forced old source (comparisons only)
    monkeypatch.delenv("SWING_PRICE_SOURCE")
    monkeypatch.setattr(kd, "frame", lambda s: None)                      # Kite has nothing -> Yahoo, and it says so
    data_prices.PROVENANCE["yahoo"].clear()
    assert data_prices.load("Y")["close"].iloc[0] == 100.0 and "Y" in data_prices.PROVENANCE["yahoo"]
    assert "Yahoo only 1" in data_prices.provenance_line()


def test_frame_fills_only_missing_days_from_yahoo(tmp_path, monkeypatch):
    monkeypatch.setattr(kd, "BASE", tmp_path)
    y = _yahoo(split_at=39, factor=1.0)
    k = y[["open", "high", "low", "close", "volume"]].iloc[30:35].copy() + 1     # Kite has 5 days, slightly different
    k.to_csv(tmp_path / "BBB.csv", index_label="date")
    monkeypatch.setattr(data_prices, "_load_yahoo", lambda s: y)
    kd._ADJ["v"] = True
    f = kd.frame("BBB")
    assert len(f) == 40 and f["close"].iloc[31] == 101.0 and f["close"].iloc[0] == 100.0
    assert f.attrs["pure_kite"] is False


def test_download_skips_without_login(monkeypatch):
    from swing import kite
    monkeypatch.setattr(kite, "logged_in", lambda: False)
    assert kd.download() == {"skipped": "not logged in"}


def test_strict_mode_never_uses_yahoo_and_reports_gaps(tmp_path, monkeypatch):
    monkeypatch.setattr(kd, "BASE", tmp_path)
    y = _yahoo(split_at=39, factor=1.0)
    k = y[["open", "high", "low", "close", "volume"]].iloc[30:35].copy() + 1
    k.to_csv(tmp_path / "KITE.csv", index_label="date")
    monkeypatch.setattr(data_prices, "_load_yahoo", lambda s: y)
    kd._ADJ["v"] = True
    monkeypatch.setenv("SWING_PRICE_SOURCE", "kite_strict")
    for v in data_prices.PROVENANCE.values():
        v.clear()
    f = data_prices.load("KITE")
    assert len(f) == 5 and f["close"].iloc[0] == 101.0                  # Kite days only, no Yahoo filling
    assert data_prices.load("NOTONKITE") is None                        # missing -> None (reported), not Yahoo
    assert "NOTONKITE" in data_prices.PROVENANCE["missing"] and not data_prices.PROVENANCE["yahoo"]
    assert "STRICT KITE" in data_prices.provenance_line() and "Yahoo: none" in data_prices.provenance_line()


def test_split_detection_from_kite_prices():
    idx = pd.bdate_range("2024-01-01", periods=6)
    k = pd.DataFrame({"open": [200, 201, 202, 101, 102, 103.0], "close": [200, 201, 202, 101, 102, 103.0]}, index=idx)
    assert kd.split_factors_from_prices(k) == {idx[3]: 2.0}
    crash = pd.DataFrame({"open": [100, 100, 82, 81.0], "close": [100, 100, 81, 80.0]}, index=idx[:4])
    assert kd.split_factors_from_prices(crash) == {}                    # an 18% crash is not a bonus
