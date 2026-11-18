"""D139 no repeat tips: one open tip per stock across channels; blocked repeats are recorded for the Learner."""
import pandas as pd

from swing import registry, vantage


def test_open_stocks_and_block(monkeypatch, tmp_path):
    monkeypatch.setattr(registry, "SUPP", tmp_path / "supp.csv")
    monkeypatch.setattr(vantage, "_load_signals", lambda: pd.DataFrame({"sym": ["TITAN", "ABC"], "status": ["open", "closed"]}))
    import swing.live_engine as le
    monkeypatch.setattr(le, "load_tips", lambda: pd.DataFrame({"symbol": ["INFY", "XYZ"], "type": ["NORMAL", "INTRADAY"],
                                                               "status": ["open", "open"]}))
    o = registry.open_stocks()
    assert o == {"TITAN": "VANTAGE", "INFY": "live engine NORMAL"}
    # VANTAGE close scan: a stock open in the live engine is blocked and recorded; its own open signal is not a repeat
    assert vantage._held_elsewhere("INFY", "VANTAGE", "2026-11-19", {"close": 100, "stop": 90}, {}) is True
    assert vantage._held_elsewhere("TITAN", "VANTAGE", "2026-11-19", {"close": 100, "stop": 90}, {}) is False
    assert vantage._held_elsewhere("TITAN", "VANTAGE live", "2026-11-19", {"close": 100, "stop": 90}, {}) is True
    assert vantage._held_elsewhere("INFY", "VANTAGE", "2026-11-19", {"close": 100}, {"no_repeat_tips": False}) is False
    S = pd.read_csv(tmp_path / "supp.csv")
    assert set(S["symbol"]) == {"INFY", "TITAN"} and len(S) == 2
