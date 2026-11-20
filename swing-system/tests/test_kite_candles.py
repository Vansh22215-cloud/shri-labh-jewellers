"""Kite candle library (owner 20 Nov): backwards download until Kite has no more, derived candles, market-hours
and storage guards. No network: Kite calls are faked."""
import pandas as pd
import pytest

from swing import kite, kite_candles as kc, kite_daily as kd


@pytest.fixture
def lib(tmp_path, monkeypatch):
    monkeypatch.setattr(kc, "BASE", tmp_path / "kc")
    monkeypatch.setattr(kc, "STATE_F", tmp_path / "kc" / "state.json")
    monkeypatch.setattr(kc, "REPORT", tmp_path / "kite_candles.md")
    monkeypatch.setattr(kc, "top300", lambda: ["AAA"])
    monkeypatch.setattr(kc, "_in_market_hours", lambda now=None: False)
    monkeypatch.setattr(kc, "data_size_gb", lambda: 0.1)
    monkeypatch.setattr(kite, "logged_in", lambda: True)
    calls = []

    def fetch(sym, interval, fr, to):              # Kite "has" candles from 2024-01-01 only
        calls.append((interval, fr, to))
        days = pd.bdate_range(max(fr, pd.Timestamp("2024-01-01")), to)
        if not len(days):
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        idx = [d + pd.Timedelta(hours=9, minutes=15) for d in days]
        return pd.DataFrame({"open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 10.0},
                            index=pd.DatetimeIndex(idx, name="date"))
    monkeypatch.setattr(kc, "_fetch", fetch)
    return calls


def test_backwards_until_kite_has_nothing(lib):
    r = kc.step(max_requests=10_000, today=pd.Timestamp("2026-11-20"))
    assert r["complete"]
    st = kc._state()
    for i in kc.ORDER:
        assert st[f"{i}|AAA"]["ended"]
        assert st[f"{i}|AAA"]["first"] == ("2024-11-20" if i == "minute" else "2024-01-01")   # 1-minute: 2 years
    d = kc.load("AAA", "60minute")
    assert d.index.min() == pd.Timestamp("2024-01-01 09:15") and d.index.max().date() == pd.Timestamp("2026-11-20").date()
    n = len(lib)
    kc.step(max_requests=10_000, today=pd.Timestamp("2026-11-20"))
    assert len(lib) == n                              # complete and up to date -> no more requests


def test_minute_only_two_years(lib):
    kc.step(max_requests=10_000, today=pd.Timestamp("2026-11-20"))
    assert min(fr for i, fr, to in lib if i == "minute") >= pd.Timestamp("2024-11-20")


def test_forward_top_up(lib):
    kc.step(max_requests=10_000, today=pd.Timestamp("2026-11-20"))
    lib.clear()
    kc.step(max_requests=10_000, today=pd.Timestamp("2026-11-25"))
    assert len(lib) == len(kc.ORDER) and all(to == pd.Timestamp("2026-11-25") for _, _, to in lib)
    assert kc.load("AAA", "15minute").index.max().date() == pd.Timestamp("2026-11-25").date()


def test_budget_respected(lib):
    r = kc.step(max_requests=3, today=pd.Timestamp("2026-11-20"))
    assert len(lib) == 3 and not r["complete"]


def test_guards(lib, monkeypatch):
    monkeypatch.setattr(kc, "_in_market_hours", lambda now=None: True)
    assert kc.step()["skipped"] == "market hours" and not lib
    monkeypatch.setattr(kc, "_in_market_hours", lambda now=None: False)
    monkeypatch.setattr(kc, "data_size_gb", lambda: 99)
    assert kc.step()["skipped"] == "storage limit" and not lib
    monkeypatch.setattr(kite, "logged_in", lambda: False)
    assert kc.step()["skipped"] == "not logged in"


def test_market_hours_window():
    ist = "Asia/Kolkata"
    assert kc._in_market_hours(pd.Timestamp("2026-11-20 15:20", tz=ist))       # Friday buy window
    assert kc._in_market_hours(pd.Timestamp("2026-11-20 09:30", tz=ist))
    assert not kc._in_market_hours(pd.Timestamp("2026-11-20 19:00", tz=ist))
    assert not kc._in_market_hours(pd.Timestamp("2026-11-21 11:00", tz=ist))   # Saturday


def test_derived_candles_exact(lib, tmp_path):
    idx = pd.date_range("2026-11-20 09:15", periods=6, freq="5min")
    df = pd.DataFrame({"open": [1, 2, 3, 4, 5, 6], "high": [2, 9, 4, 5, 6, 7], "low": [0.5, 1, 2, 3, 0.1, 5],
                       "close": [1.5, 2.5, 3.5, 4.5, 5.5, 6.5], "volume": [1, 2, 3, 4, 5, 6]}, index=idx)
    kc._store("5minute", "BBB", df)
    t = kc.load("BBB", "10minute")
    assert list(t.index.strftime("%H:%M")) == ["09:15", "09:25", "09:35"]
    assert t.iloc[0].tolist() == [1, 9, 0.5, 2.5, 3]
    assert t.iloc[2].tolist() == [5, 7, 0.1, 6.5, 11]


def test_report(lib):
    kc.step(max_requests=10_000, today=pd.Timestamp("2026-11-20"))
    txt = "\n".join(kc.report())
    assert "Kite Connect historical API only" in txt and "| 60minute | 1/1 | 2024-01-01" in txt


def test_daily_backfill_to_2000(tmp_path, monkeypatch):
    monkeypatch.setattr(kd, "BASE", tmp_path / "kd")
    monkeypatch.setattr(kd, "STATE_F", tmp_path / "kd" / "state.json")
    kd._store("AAA", pd.DataFrame({"open": [1.0], "high": [1.0], "low": [1.0], "close": [1.0], "volume": [1.0]},
                                  index=pd.DatetimeIndex([pd.Timestamp("2011-01-03")], name="date")))
    asked = []

    def day(sym, fr, to):
        asked.append(fr)
        days = pd.bdate_range(max(fr, pd.Timestamp("2005-06-01")), to)
        return pd.DataFrame({"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1.0},
                            index=pd.DatetimeIndex(days, name="date"))
    monkeypatch.setattr(kd, "_day_candles", day)
    st = {"AAA": "2026-11-20"}
    kd.backfill(st, ["AAA"], 50)
    assert st["back|AAA"] and kd._raw("AAA").index.min() == pd.Timestamp("2005-06-01")
    assert min(asked) >= kd.START
    assert "BANKNIFTY" in kd.all_symbols() and "INDIAVIX" in kd.all_symbols()


def test_daemon_never_downloads_in_market_hours():
    from swing import daemon
    ist = "Asia/Kolkata"
    assert daemon.key("kite_download", pd.Timestamp("2026-11-20 10:00", tz=ist)) is None
    assert daemon.key("kite_download", pd.Timestamp("2026-11-20 15:30", tz=ist)) is None
    assert daemon.key("kite_download", pd.Timestamp("2026-11-20 19:00", tz=ist))
    assert daemon.key("kite_download", pd.Timestamp("2026-11-21 11:00", tz=ist))     # Saturday: fine
