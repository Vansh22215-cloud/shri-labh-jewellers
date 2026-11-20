"""Long test: fast exit maths = the step-by-step rules; the whole run on a small hand-made library."""
import numpy as np
import pandas as pd
import pytest

from swing import candles, longtest as lt


def test_fast_trade_matches_step_by_step():
    rng = np.random.default_rng(3)
    for _ in range(300):
        n = 60
        c = 100 * np.exp(np.cumsum(rng.normal(0, 0.004, n)))
        o = np.r_[100, c[:-1]]
        h = np.maximum(o, c) * (1 + np.abs(rng.normal(0, 0.002, n)))
        l = np.minimum(o, c) * (1 - np.abs(rng.normal(0, 0.002, n)))
        end_m = 575 + 5 * np.arange(n)
        ends = np.array([f"{m // 60:02d}:{m % 60:02d}" for m in end_m])
        lng = bool(rng.integers(0, 2))
        a, _, ja = lt._simulate(o, h, l, c, ends, 1, o[1], "LONG" if lng else "SHORT", 0.01, 0.02)
        b, jb = lt.fast_trade(o, h, l, c, end_m, 1, o[1], lng, 0.01, 0.02)
        assert a == pytest.approx(b) and ja == jb


def test_run_on_small_library(monkeypatch):
    days = pd.bdate_range("2023-06-01", periods=20).append(pd.bdate_range("2024-06-03", periods=20))
    rng = np.random.default_rng(1)
    for k, sym in enumerate(["AAA", "BBB", "NIFTY50"]):
        rows = []
        for d in days:
            idx = pd.date_range(d + pd.Timedelta(hours=9, minutes=15), periods=75, freq="5min")
            c = 100 * np.exp(np.cumsum(rng.normal(0.0005, 0.004, 75)))
            o = np.r_[c[0], c[:-1]]
            rows.append(pd.DataFrame({"open": o, "high": np.maximum(o, c) * 1.002, "low": np.minimum(o, c) * 0.998,
                                      "close": c, "volume": rng.integers(1e3, 5e4, 75).astype(float)}, index=idx))
        candles.store("5minute", sym, pd.concat(rows))
    monkeypatch.setattr(candles, "symbols", lambda iv="day": ["NIFTY50", "AAA", "BBB"])
    monkeypatch.setattr(lt, "REPORT", lt.RESULTS / "_t.md")
    monkeypatch.setattr(lt, "DATA", candles.BASE)
    rows, orow, data = lt.run(send=False, workers=1)
    assert len(rows) == len(lt.SIG) * len(lt.EXI) and len(orow) == 18 * len(lt.NMASKS) + len(lt.OPT_SCALE) and data["stocks"] == 2
    assert any(r["dev"] for r in rows) and "Kite 5-minute candles only" in lt.REPORT.read_text()
    lt.REPORT.unlink()


def _s(avg, fall=-5000):
    return {"avg_day": avg, "max_fall": fall, "days": 100, "trade_days": 90, "win_days_pct": 55, "days_10k_pct": 2,
            "worst_day": -3000, "best_day": 9000, "total": avg * 100}


def test_switch_only_when_better_in_both_periods(tmp_path, monkeypatch):
    monkeypatch.setattr(lt, "DATA", tmp_path)
    live = dict(lt.LIVE_STK, dev=_s(500), recent=_s(300))
    better_dev_only = dict(lt.LIVE_STK, vol=2.0, dev=_s(900), recent=_s(100))
    rec = lt.recommend([live, better_dev_only], [], [])
    assert rec["changes"] == [] and not (tmp_path / "practice_params.json").exists()
    both = dict(lt.LIVE_STK, vol=2.0, dev=_s(900), recent=_s(700))
    rec = lt.recommend([live, both], [], [])
    assert rec["changes"] == ["stocks"] and rec["params"]["stk_vol_mult"] == 2.0
    assert (tmp_path / "practice_params.json").exists() and rec["stocks_scale_for_10k"] == round(10000 / 700, 1)


def test_live_trader_uses_switched_on_settings(tmp_path, monkeypatch):
    import json
    from swing import practice_live, autotrader, paper
    (tmp_path / "practice_params.json").write_text(json.dumps({"stk_sides": "long", "stk_factors": 2}))
    monkeypatch.setattr(practice_live, "DATA", tmp_path)
    p = practice_live.practice_params()
    e = autotrader.Engine(paper.Broker(None), None, params=p)
    assert e.p["stk_sides"] == "long" and e.p["stk_factors"] == 2 and e.p["opt_stop"] == autotrader.P["opt_stop"]


def test_scale_trade_books_part_at_1r_and_runs_rest_at_cost():
    end_m = 575 + 5 * np.arange(10)
    o = np.array([100, 100, 100.5, 101, 101.5, 102, 102.5, 103, 103, 103.0])
    h = o + 0.6
    l = o - 0.2
    c = o + 0.3
    e1, e2, fb, j = lt.scale_trade(o, h, l, c, end_m, 1, 100.0, True, 0.01, 0.5, 3.0)
    assert e1 == 101.0 and fb == 0.5 and e2 == 103.0                 # 1R booked, runner reached 3R
    l2 = l.copy()
    l2[4] = 99.5                                                      # after 1R the price falls back below cost
    e1, e2, fb, j = lt.scale_trade(o, h, l2, c, end_m, 1, 100.0, True, 0.01, 0.5, 3.0)
    assert e1 == 101.0 and e2 == 100.0                                # rest out at cost, not at the 1% stop
    l3 = l.copy()
    l3[1] = 98.9                                                      # stop before 1R: everything out at the stop
    e1, e2, fb, j = lt.scale_trade(o, h, l3, c, end_m, 1, 100.0, True, 0.01, 0.5, 3.0)
    assert e1 == e2 == 99.0 and fb == 0.0


def test_live_trader_scales_out_and_dashboard_shows_one_line():
    from datetime import timedelta
    from swing import autotrader, paper, dashboard
    b = paper.Broker(None, start=50800)
    p = b.open_position("k", "NIFTY X CALL", "NFO:X", "OPT", "LONG", 195, 100, 70, 190, "NIFTY options",
                        pd.Timestamp("2026-11-23 10:00"), lots=3)
    p.t1, p.book_frac = 130.0, 2 / 3

    class M:
        def __init__(self, bars):
            self.bars = bars

        def bar(self, sym, t):
            return self.bars.pop(0) if self.bars else None
    e = autotrader.Engine(b, M([(110, 131, 109, 129), (128, 129, 100.0, 101)]))
    e.on_minute(pd.Timestamp("2026-11-23 10:06"))
    assert len(b.acc.closed) == 1 and b.acc.closed[0]["qty"] == 130 and b.acc.open["k"].stop == p.avg
    e.on_minute(pd.Timestamp("2026-11-23 10:07"))                     # rest stopped at cost
    assert not b.acc.open and b.acc.closed[1]["why"] == "stop at entry"
    rows = dashboard.combine(b.acc.closed)
    assert len(rows) == 1 and rows[0]["qty"] == 195
