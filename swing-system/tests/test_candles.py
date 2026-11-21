"""Kite candle library: every stock, every interval, backwards until Kite has nothing, guards. Kite is faked."""
import pandas as pd
import pytest

from swing import candles as cd, kite


@pytest.fixture
def lib(monkeypatch):
    monkeypatch.setattr(cd, "symbols", lambda interval="day": ["AAA"])
    monkeypatch.setattr(cd, "in_market_hours", lambda now=None: False)
    monkeypatch.setattr(cd, "data_size_gb", lambda: 0.1)
    monkeypatch.setattr(kite, "logged_in", lambda: True)
    calls = []

    def fetch(sym, interval, fr, to):             # Kite "has" candles from 2024-01-01 only
        calls.append((interval, fr, to))
        days = pd.bdate_range(max(fr, pd.Timestamp("2024-01-01")), to)
        if not len(days):
            return pd.DataFrame(columns=cd.COLS)
        idx = days if interval == "day" else [d + pd.Timedelta(hours=9, minutes=15) for d in days]
        return pd.DataFrame({"open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 10.0},
                            index=pd.DatetimeIndex(idx, name="date"))
    monkeypatch.setattr(cd, "_fetch", fetch)
    return calls


def test_everything_kite_has_every_interval(lib):
    r = cd.step(max_requests=100_000, today=pd.Timestamp("2026-11-20"))
    assert r["complete"]
    st = cd._state()
    for i in cd.ORDER:
        assert st[f"{i}|AAA"]["ended"] and st[f"{i}|AAA"]["first"] == "2024-01-01"
    assert cd.raw("AAA", "60minute").index.min() == pd.Timestamp("2024-01-01 09:15")
    assert [c[0] for c in lib][0] == "day"                   # daily first
    n = len(lib)
    cd.step(max_requests=100_000, today=pd.Timestamp("2026-11-20"))
    assert len(lib) == n                                     # complete and up to date: no more requests


def test_forward_top_up(lib):
    cd.step(max_requests=100_000, today=pd.Timestamp("2026-11-20"))
    lib.clear()
    cd.step(max_requests=100_000, today=pd.Timestamp("2026-11-25"))
    assert len(lib) == len(cd.ORDER) and all(to == pd.Timestamp("2026-11-25") for _, _, to in lib)


def test_budget_and_guards(lib, monkeypatch):
    r = cd.step(max_requests=3, today=pd.Timestamp("2026-11-20"))
    assert len(lib) == 3 and not r["complete"]
    lib.clear()
    monkeypatch.setattr(cd, "in_market_hours", lambda now=None: True)
    assert cd.step()["skipped"] == "market hours" and not lib
    monkeypatch.setattr(cd, "in_market_hours", lambda now=None: False)
    monkeypatch.setattr(kite, "logged_in", lambda: False)
    assert cd.step()["skipped"] == "not logged in"


def test_storage_limit_keeps_daily_only(lib, monkeypatch):
    monkeypatch.setattr(cd, "data_size_gb", lambda: 99)
    r = cd.step(max_requests=100_000, today=pd.Timestamp("2026-11-20"))
    assert {c[0] for c in lib} == {"day"} and r["storage_full"]
    assert "storage limit reached" in "\n".join(cd.report())


def test_market_hours():
    ist = "Asia/Kolkata"
    assert cd.in_market_hours(pd.Timestamp("2026-11-20 09:30", tz=ist))
    assert cd.in_market_hours(pd.Timestamp("2026-11-20 15:45", tz=ist))
    assert not cd.in_market_hours(pd.Timestamp("2026-11-20 19:00", tz=ist))
    assert not cd.in_market_hours(pd.Timestamp("2026-11-21 11:00", tz=ist))


def test_derived_candles_exact():
    idx = pd.date_range("2026-11-20 09:15", periods=6, freq="5min")
    df = pd.DataFrame({"open": [1, 2, 3, 4, 5, 6], "high": [2, 9, 4, 5, 6, 7], "low": [0.5, 1, 2, 3, 0.1, 5],
                       "close": [1.5, 2.5, 3.5, 4.5, 5.5, 6.5], "volume": [1, 2, 3, 4, 5, 6]}, index=idx)
    cd.store("5minute", "BBB", df)
    t = cd.load("BBB", "10minute", adjusted=False)
    assert list(t.index.strftime("%H:%M")) == ["09:15", "09:25", "09:35"]
    assert t.iloc[0].tolist() == [1, 9, 0.5, 2.5, 3]


def test_split_found_in_kite_daily_and_adjusted():
    idx = pd.bdate_range("2025-01-01", periods=6)
    c = [100, 102, 101, 51, 52, 53]                  # 1:2 split on day 4
    d = pd.DataFrame({"open": [100, 101, 102, 50.5, 51, 52], "high": c, "low": c, "close": c, "volume": 1000.0}, index=idx)
    cd.store("day", "SPL", d)
    assert cd.split_factors("SPL") == {idx[3]: 2.0}
    a = cd.load("SPL", "day")
    assert a["close"].iloc[0] == 50 and a["volume"].iloc[0] == 2000 and a["close"].iloc[-1] == 53
    assert a.attrs["source"] == "Kite"


def test_complete_needs_every_stock_up_to_date(lib):
    assert not cd.complete("day")
    cd.step(max_requests=100_000, today=pd.Timestamp.now().normalize())
    assert cd.complete("day")


def test_three_at_once_keeps_the_kite_speed_limit(lib, monkeypatch):
    import time as _t
    stamps = []
    real = cd._fetch

    def timed(sym, interval, fr, to):
        cd._throttle()
        stamps.append(_t.time())
        return real(sym, interval, fr, to)
    monkeypatch.setattr(cd, "symbols", lambda interval="day": ["AAA", "BBB", "CCC", "DDD"])
    monkeypatch.setattr(cd, "_fetch", timed)
    monkeypatch.setattr(cd, "GAP", 0.02)
    cd.step(max_requests=100_000, today=pd.Timestamp("2026-11-20"), intervals=["day"])
    gaps = [b - a for a, b in zip(sorted(stamps), sorted(stamps)[1:])]
    assert len(stamps) > 4 and min(gaps) >= 0.019              # never two requests closer than the limit
    assert all(cd._state()[f"day|{s}"]["ended"] for s in ["AAA", "BBB", "CCC", "DDD"])


def test_one_bad_stock_never_blocks_the_rest(lib, monkeypatch):
    good = cd._fetch

    def fetch(sym, interval, fr, to):
        if sym == "BAD":
            raise ValueError("Kite refused this one")
        return good(sym, interval, fr, to)
    monkeypatch.setattr(cd, "symbols", lambda interval="day": ["BAD", "AAA"])
    monkeypatch.setattr(cd, "_fetch", fetch)
    for _ in range(3):
        cd.step(max_requests=100_000, today=pd.Timestamp("2026-11-20"), intervals=["day"])
    st = cd._state()
    assert st["day|AAA"]["ended"] and st["day|BAD"]["ended"] and st["day|BAD"]["missing"]
    assert cd.complete.__call__ is not None
