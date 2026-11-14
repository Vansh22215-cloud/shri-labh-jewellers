import numpy as np
import pandas as pd

from swing import orderflow as of


def _bars(closes, opens=None):
    c = np.array(closes, float)
    o = np.array(opens, float) if opens is not None else c - 0.2
    h, l = np.maximum(o, c) + 0.3, np.minimum(o, c) - 0.3
    return pd.DataFrame({"open": o, "high": h, "low": l, "close": c, "volume": 1000.0},
                        index=pd.bdate_range("2025-01-01", periods=len(c)))


def test_order_block_found_and_first_touch():
    base = [100.0] * 20
    # day 20: down candle (open 101, close 99.5); then a strong up move breaking the 10-day high; later a pull-back
    closes = base + [99.5, 103, 106, 108, 107, 105, 103, 101.2, 104, 106]
    opens = [c - 0.2 for c in base] + [101, 99.6, 103, 106, 108, 107, 105, 103, 101.3, 104]
    d = _bars(closes, opens)
    obs = of.find_order_blocks(d)
    assert any(i == 20 for i, lo, hi in obs)
    touch, zl, zh = of.order_block_touches(d)
    t = np.where(touch)[0]
    assert len(t) == 1 and t[0] == 27 and zl[27] < 100 < zh[27]          # first return into the zone only


def test_pressure_and_labels():
    assert of.pressure({"buy_qty": 300, "sell_qty": 100, "bid5": 50, "ask5": 50}) == 0.25
    assert of.pressure({}) is None
    assert of.label(0.6) == "strong buying" and of.label(-0.2) == "sellers ahead" and of.label(0) == "balanced"


def test_pulse_breadth_and_sector_flow():
    q = {"A": {"last": 105, "prev": 100, "value_cr": 50, "buy_qty": 10, "sell_qty": 5},
         "B": {"last": 98, "prev": 100, "value_cr": 20, "buy_qty": 1, "sell_qty": 5},
         "C": {"last": 101, "prev": 100, "value_cr": 10}}
    p = of.pulse(q, vix=14, sector_map={"A": "Banks", "B": "IT", "C": "Banks"})
    assert p["adv"] == 2 and p["dec"] == 1 and p["mood"] == "RISK-ON"
    assert p["sectors"][0][0] == "Banks" and p["sectors"][0][1] == 60.0 and p["sectors"][-1][0] == "IT"


def test_shadow_record_and_evaluate(tmp_path, monkeypatch):
    monkeypatch.setattr(of, "SHADOW_F", tmp_path / "s.csv")
    t0 = pd.Timestamp("2026-11-10 10:00")
    for k in range(4):
        q = {f"S{i}": {"last": 100 + (k if i % 2 else -k), "value_cr": 50,
                       "buy_qty": 90 if i % 2 else 10, "sell_qty": 10 if i % 2 else 90} for i in range(10)}
        of.record(q, t0 + pd.Timedelta(minutes=30 * k))
    r = of.evaluate(min_rows=10)
    assert r["ready"] and r["edge_up_share"] == 1.0                       # buyers' stocks rose, sellers' fell
