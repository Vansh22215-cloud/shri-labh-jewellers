import numpy as np
import pandas as pd
import pytest

from swing import feeds, profile


def _session(day, drift=0.0, seed=0):
    rng = np.random.default_rng(seed)
    ts = pd.date_range(f"{day} 09:15", f"{day} 15:25", freq="5min")
    px = 100 + np.cumsum(rng.normal(drift, 0.2, len(ts)))
    return pd.DataFrame({"ts": ts, "open": px, "high": px + 0.15, "low": px - 0.15, "close": px + 0.05,
                         "volume": rng.integers(1000, 5000, len(ts)).astype(float)})


def test_day_profile_value_area_contains_poc_and_70pct():
    r = profile.day_profile(_session("2026-11-03", seed=1))
    assert r["val"] <= r["poc"] <= r["vah"] and r["low"] <= r["val"] and r["vah"] <= r["high"]
    assert r["low"] <= r["vwap"] <= r["high"]


def test_open_drive_detected_on_a_trend_day():
    g = _session("2026-11-03", seed=2)
    g["close"] = np.linspace(100, 110, len(g)); g["open"] = g["close"] - 0.05
    g["high"], g["low"] = g["close"] + 0.05, g["open"] - 0.02
    assert profile.day_profile(g)["open_drive_up"] == 1.0


def test_implied_vol_round_trip():
    price = feeds._bs_price(100, 100, 30 / 365, 0.3, True)
    assert feeds.implied_vol(price, 100, 100, 30 / 365, True) == pytest.approx(0.3, abs=1e-4)
    price = feeds._bs_price(100, 95, 30 / 365, 0.4, False)
    assert feeds.implied_vol(price, 100, 95, 30 / 365, False) == pytest.approx(0.4, abs=1e-4)


def test_option_iv_fields_from_udiff_rows():
    rows = []
    for k in (90, 95, 100, 105, 110):
        for typ in ("CE", "PE"):
            rows.append({"XpryDt": pd.Timestamp("2026-11-24"), "StrkPric": k, "OptnTp": typ, "TtlTradgVol": 10,
                         "ClsPric": feeds._bs_price(100, k, 21 / 365, 0.25, typ == "CE")})
    out = feeds.option_iv_fields(pd.DataFrame(rows), 100.0, "2026-11-03")
    assert out["atm_iv"] == pytest.approx(0.25, abs=1e-3) and abs(out["skew_95_105"]) < 1e-3


def test_tick_metrics_sign_and_book():
    ts = pd.date_range("2026-11-03 09:15", periods=200, freq="10s")
    price = 100 + np.cumsum(np.r_[0, np.tile([0.05, 0.05, -0.05], 67)[:199]])
    t = pd.DataFrame({"ts": ts, "price": price, "qty": 10.0})
    b = pd.DataFrame({"ts": ts, "bid": price - 0.05, "ask": price + 0.05, "bid_qty": 300.0, "ask_qty": 100.0})
    m = feeds.tick_metrics(t, b, atr=2.0)
    assert m["volume_delta"] > 0 and m["order_book_imbalance"] == pytest.approx(0.5)
    assert m["quoted_spread_bps"] > 0 and m["spread_to_atr"] == pytest.approx(0.05)


def test_market_impact_square_root():
    assert feeds.market_impact_bps(100, 10000, 0.02) == pytest.approx(0.02 * 0.1 * 1e4)
