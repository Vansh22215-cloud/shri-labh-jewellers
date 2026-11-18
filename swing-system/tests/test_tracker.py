"""Every tip tracked (owner 18 Nov): zone entry, stop / target exits, VANTAGE, no owner data written."""
import pandas as pd

from swing import tracker


def bars(rows, start="2026-11-10"):
    idx = pd.bdate_range(start, periods=len(rows))
    return pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=idx).assign(volume=1e6)


def test_zone_rules():
    d = bars([(100, 101, 99, 100), (101, 103, 100, 102), (102, 104, 95, 96)])
    r = tracker.zone_trade(d, "2026-11-10", 100, 102, 96, 120)
    assert r["status"] == "closed" and r["why"] == "stop-loss" and r["entry"] == 101 and r["exit"] == 96
    r = tracker.zone_trade(d, "2026-11-10", 90, 95, 80, 120)
    assert r["status"].startswith("skipped")
    r = tracker.zone_trade(bars([(100, 101, 99, 100), (101, 125, 100, 124)]), "2026-11-10", 100, 102, 90, 120)
    assert r["why"] == "target 1" and r["exit"] == 120
    r = tracker.zone_trade(bars([(100, 101, 99, 100), (101, 103, 100, 102), (102, 104, 101, 103)]), "2026-11-10", 100, 102, 90, 120)
    assert r["status"] == "open" and r["exit"] == 103


def test_build_writes_no_owner_data(monkeypatch, tmp_path):
    (tmp_path / "j").mkdir()
    pd.DataFrame([{"date": "2026-11-10", "symbol": "AAA", "kind": "tip", "strategy": "a3", "entry_low": 100,
                   "entry_high": 102, "stop": 90, "target1": 120, "qty": 7}]).to_csv(tmp_path / "j" / "tips.csv", index=False)
    monkeypatch.setattr(tracker, "J", tmp_path / "j")
    monkeypatch.setattr(tracker, "CSV", tmp_path / "j" / "all.csv")
    monkeypatch.setattr(tracker, "MD", tmp_path / "j" / "all.md")
    monkeypatch.setattr(tracker, "PRIVATE", tmp_path / "none")
    import swing.vantage as v
    monkeypatch.setattr(v, "_load_signals", lambda: pd.DataFrame())
    d = bars([(100, 101, 99, 100), (101, 103, 100, 102), (102, 104, 101, 103)])
    R = tracker.build(load=lambda s: d)
    assert len(R) == 1 and R.iloc[0]["result_pct"] > 0
    out = (tmp_path / "j" / "all.csv").read_text() + (tmp_path / "j" / "all.md").read_text()
    assert "qty" not in out and "taken" not in out and "capital" not in out.lower()
