import numpy as np
import pandas as pd

from swing import watchlist as wl

EQ = pd.DataFrame({"SYMBOL": ["INFY", "HDFCBANK", "LT", "TITAN", "TRENT", "BUY"],
                   "NAME OF COMPANY": ["Infosys Limited", "HDFC Bank Limited", "Larsen & Toubro Limited",
                                       "Titan Company Limited", "Trent Limited", "Buy Ltd"]})


def test_extract_symbols_and_names():
    txt = "STOCKS TO WATCH: INFY, HDFC Bank, Larsen & Toubro, #TITAN and Trent - BUY on dips"
    got = wl.extract_symbols(txt, EQ)
    assert set(got) == {"INFY", "HDFCBANK", "LT", "TITAN", "TRENT"} and "BUY" not in got
    assert wl.looks_like_watchlist(txt, EQ) and not wl.looks_like_watchlist("BUY INFY 1500 SL 1450", EQ)


def test_handle_rates_and_keeps_watching(monkeypatch, tmp_path):
    monkeypatch.setattr(wl, "WL_F", tmp_path / "wl.csv")
    monkeypatch.setattr(wl, "extract_symbols", lambda text, eq=None: ["INFY", "TITAN", "LT"])
    monkeypatch.setattr(wl, "assess", lambda s, top=None: {"symbol": s, "price": 100.0, "score": {"INFY": 3, "TITAN": 8, "LT": 6}[s],
                                                           "reasons": ["strong uptrend"], "signal": None})
    monkeypatch.setattr("swing.high_prob.universe", lambda: ["INFY"])
    t = wl.handle("x", "Firm")
    assert t.index("#TITAN") < t.index("#LT") < t.index("#INFY")          # best first
    assert "8/10" in t and "No trade right now" in t
    assert set(wl.watched()) == {"INFY", "TITAN", "LT"}
