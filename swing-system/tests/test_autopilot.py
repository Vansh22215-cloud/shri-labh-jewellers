import pandas as pd

from swing import autopilot as ap
from swing import live_engine as le


def _setup(tmp_path, monkeypatch, rows):
    monkeypatch.setattr(le, "TIPS_F", tmp_path / "tips.csv")
    monkeypatch.setattr(le, "SHADOW_F", tmp_path / "shadow.csv")
    monkeypatch.setattr(ap, "STATE_F", tmp_path / "ap.json")
    sent = []
    monkeypatch.setattr(ap, "_notify", lambda text: sent.append(text))
    pd.DataFrame(rows).to_csv(tmp_path / "tips.csv", index=False)
    return sent


def test_close_tip_records_real_result():
    t = pd.DataFrame([{"entry": 100.0, "stop": 95.0, "targets": "105/110", "side": "buy", "status": "open"},
                      {"entry": 100.0, "stop": 105.0, "targets": "95", "side": "sell", "status": "open"}])
    ap.close_tip(t, 0, "stop")
    ap.close_tip(t, 1, "done")
    assert t.loc[0, "result_pct"] == -5.0 and t.loc[1, "result_pct"] == 5.0 and t.loc[0, "closed_at"]


def test_throttle_pauses_losing_positional_and_tells_once(tmp_path, monkeypatch):
    rows = [{"type": "NORMAL", "setup": "RCP", "symbol": f"S{i}", "side": "buy", "entry": 100, "stop": 90,
             "status": "time", "closed_at": f"2026-10-{1 + i % 28:02d} 15:00", "result_pct": -2.0} for i in range(25)]
    sent = _setup(tmp_path, monkeypatch, rows)
    s = ap.throttle("2026-11-16")
    assert s["rules"]["pos_paused"] and s["pos_paused_until"] == "2027-01-15" and len(sent) == 1
    ap.throttle("2026-11-17")
    assert len(sent) == 1                                  # no repeat
    s = ap.throttle("2027-01-16")                          # 60 days over -> retried
    assert s["rules"]["pos_paused"] is False or s["pos_paused_until"] != "2027-01-15"


def test_dip_rank10_only_when_live_avg_negative(tmp_path, monkeypatch):
    rows = [{"type": "NORMAL", "setup": "HP", "symbol": f"S{i}", "side": "buy", "entry": 100, "stop": 90,
             "status": "done", "closed_at": f"2026-10-{1 + i % 28:02d}", "result_pct": -1.0 if i % 3 else 0.5}
            for i in range(24)]
    _setup(tmp_path, monkeypatch, rows)
    assert ap.throttle("2026-11-16")["rules"]["dip_rank10_only"] is True


def test_health_alert_once_a_day(tmp_path, monkeypatch):
    sent = _setup(tmp_path, monkeypatch, [])
    assert ap.health_alert(["Price data is not up to date"], "2026-11-16")
    assert not ap.health_alert(["again"], "2026-11-16") and len(sent) == 1
    assert not ap.health_alert([], "2026-11-17")


def test_kite_watch_alerts_after_30_minutes(tmp_path, monkeypatch):
    sent = _setup(tmp_path, monkeypatch, [])
    t0 = pd.Timestamp("2026-11-17 10:00")
    assert not ap.kite_watch(False, True, t0)
    assert not ap.kite_watch(False, True, t0 + pd.Timedelta(minutes=10))
    assert ap.kite_watch(False, True, t0 + pd.Timedelta(minutes=31)) and len(sent) == 1
    assert not ap.kite_watch(True, True, t0 + pd.Timedelta(minutes=32))
