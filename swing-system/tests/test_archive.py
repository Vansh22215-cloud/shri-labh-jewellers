import io
import tarfile

import numpy as np
import pandas as pd

from swing import archive


def _iso(monkeypatch, tmp_path):
    monkeypatch.setattr(archive, "ARCHIVE", tmp_path / "archive")
    monkeypatch.setattr(archive, "DATA", tmp_path)
    monkeypatch.setattr(archive, "PRIVATE", tmp_path / "private")
    (tmp_path / "private").mkdir()


def test_write_day_is_append_only(monkeypatch, tmp_path):
    _iso(monkeypatch, tmp_path)
    a = pd.DataFrame({"symbol": ["X", "Y"], "close": [10.0, 20.0]})
    assert archive.write_day("eod", "2026-11-03", a) == 2
    b = pd.DataFrame({"symbol": ["X", "Z"], "close": [99.0, 30.0]})      # X already stored -> NOT overwritten
    assert archive.write_day("eod", "2026-11-03", b) == 1
    got = archive.read("eod").set_index("symbol")["close"]
    assert got["X"] == 10.0 and got["Z"] == 30.0 and len(got) == 3


def test_fill_panel_adds_dropped_stock_and_never_replaces_yahoo(monkeypatch, tmp_path):
    _iso(monkeypatch, tmp_path)
    idx = pd.bdate_range("2026-01-01", periods=80)
    for d in idx:
        archive.write_day("eod", d, pd.DataFrame({"symbol": ["GONE", "KEEP"], "open": [5.0, 1.0], "high": [5.0, 1.0],
                                                   "low": [5.0, 1.0], "close": [5.0, 1.0], "adj_close": [5.0, 1.0],
                                                   "volume": [100.0, 100.0], "dividends": [0.0, 0.0], "splits": [0.0, 0.0]}))
    keep = pd.DataFrame({"KEEP": np.full(70, 2.0)}, index=idx[:70])
    P = {c: keep.copy() for c in ("open", "high", "low", "close", "volume", "raw_close")}
    P = archive.fill_panel(P, ["GONE", "KEEP"])
    assert P["close"]["GONE"].notna().sum() == 80                 # delisted stock restored from the archive
    assert (P["close"]["KEEP"].iloc[:70] == 2.0).all()            # Yahoo's own history untouched
    assert (P["close"]["KEEP"].iloc[70:] == 1.0).all()            # gap after Yahoo's end filled


def test_restore_rejects_unsafe_paths_and_merges(monkeypatch, tmp_path):
    _iso(monkeypatch, tmp_path)
    archive.write_day("eod", "2026-11-03", pd.DataFrame({"symbol": ["X"], "close": [1.0]}))
    tp = tmp_path / "b.tar.gz"
    with tarfile.open(tp, "w:gz") as t:
        def add(name, data):
            ti = tarfile.TarInfo(name); ti.size = len(data); t.addfile(ti, io.BytesIO(data))
        buf = io.BytesIO(); pd.DataFrame({"symbol": ["X", "Y"], "close": [9.0, 2.0]}).to_csv(buf, index=False, compression="gzip")
        add("archive/eod/2026/2026-11-03.csv.gz", buf.getvalue())
        add("../evil.txt", b"x")
        add("settings.yaml", b"x")
        add("private/my_trades.csv", b"symbol,qty\nA,1\n")
    n = archive.restore(tp)
    assert n == 2 and not (tmp_path.parent / "evil.txt").exists() and not (tmp_path / "settings.yaml").exists()
    got = archive.read("eod").set_index("symbol")["close"]
    assert got["X"] == 1.0 and got["Y"] == 2.0


def test_full_redownload_never_loses_older_history():
    from swing.data_prices import keep_older_history
    idx = pd.bdate_range("2020-01-01", periods=100)
    old = pd.DataFrame({"close": 10.0, "adj_close": 9.0}, index=idx)
    new = pd.DataFrame({"close": 10.0, "adj_close": 4.5}, index=idx[50:])      # trimmed + re-adjusted
    out = keep_older_history(old, new)
    assert len(out) == 100 and np.allclose(out["adj_close"].iloc[:50], 4.5)
