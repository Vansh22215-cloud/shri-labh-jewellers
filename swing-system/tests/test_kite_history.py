import pandas as pd

from swing import kite_history as kh


def _bars(day="2026-11-18", step=15):
    t = pd.date_range(f"{day} 09:15", f"{day} 15:15", freq=f"{step}min")
    n = len(t)
    c = pd.Series(range(100, 100 + n), dtype=float)
    return pd.DataFrame({"date": t, "open": c - 0.5, "high": c + 1, "low": c - 1, "close": c, "volume": 1000.0})


def test_summary_has_execution_prices():
    S = kh.summarise(_bars())
    r = S.iloc[0]
    assert r["open"] == 99.5 and r["close"] == 124.0
    assert r["p1515"] == 123.5                                  # open of the 15:15 bar
    assert r["first30_pct"] > 0 and r["last_hour_pct"] > 0 and r["vwap"] > 0


def test_windows_keep_only_open_and_close_half_hours():
    W = kh.windows(_bars(step=5))
    hm = W["date"].dt.hour * 60 + W["date"].dt.minute
    assert ((hm < 585) | (hm >= 900)).all() and len(W) == 6 + 4  # 9:15-9:40 and 15:00-15:15 in this sample


def test_step_backfills_within_budget(tmp_path, monkeypatch):
    from swing import kite
    monkeypatch.setattr(kh, "BASE", tmp_path)
    monkeypatch.setattr(kh, "STATE_F", tmp_path / "state.json")
    monkeypatch.setattr(kh, "symbols", lambda: ["AAA"])
    monkeypatch.setattr(kite, "logged_in", lambda: True)
    calls = []
    monkeypatch.setattr(kh, "_candles", lambda sym, iv, fr, to: calls.append((iv, fr, to)) or _bars(step=15 if iv == "15minute" else 5))
    r = kh.step(max_requests=10, today=pd.Timestamp("2026-11-19"))
    assert r["requests"] == 10 and len(calls) == 10
    assert (tmp_path / "summary" / "AAA.csv.gz").exists()
    r2 = kh.step(max_requests=10, today=pd.Timestamp("2026-11-19"))   # continues where it stopped
    assert kh._state()["AAA|15minute"] > "2019-12-01"


def test_skips_without_login(monkeypatch):
    from swing import kite
    monkeypatch.setattr(kite, "logged_in", lambda: False)
    assert kh.step() == {"skipped": "not logged in"}


def test_permission_refusal_does_not_log_out(tmp_path, monkeypatch):
    import pytest
    from swing import kite

    class R:
        status_code = 403
        def json(self):
            return {"error_type": "PermissionException"}
    tok = tmp_path / "tok"
    tok.write_text("x")
    monkeypatch.setattr(kite, "TOKEN_F", tok)
    monkeypatch.setattr(kite, "keys", lambda: ("k", "s"))
    monkeypatch.setattr(kite, "token", lambda: "t")
    monkeypatch.setattr(kite.requests, "get", lambda *a, **k: R())
    with pytest.raises(PermissionError):
        kite._get("/instruments/historical/1/day")
    assert tok.exists()                                      # still logged in
