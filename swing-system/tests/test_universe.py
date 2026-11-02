import pandas as pd

from swing.universe import universe_at


def test_universe_point_in_time_and_new_listing_rule():
    rows = []
    for d in pd.bdate_range("2023-01-02", "2024-06-28")[::5]:
        rows.append({"symbol": "OLD", "close": 100, "value": 1e9, "date": d, "series": "EQ"})
        if d >= pd.Timestamp("2024-03-01"):
            rows.append({"symbol": "NEW", "close": 100, "value": 9e9, "date": d, "series": "EQ"})
        rows.append({"symbol": "PENNY", "close": 10, "value": 5e9, "date": d, "series": "EQ"})
    s = pd.DataFrame(rows)
    u = universe_at(s, "2024-07-01", n=10)
    assert list(u["symbol"]) == ["OLD"]          # NEW too young, PENNY too cheap
    # a stock that only appears AFTER the date must not be included
    future = pd.DataFrame([{"symbol": "FUT", "close": 100, "value": 9e12, "date": pd.Timestamp("2024-08-01"), "series": "EQ"}])
    u2 = universe_at(pd.concat([s, future]), "2024-07-01", n=10)
    assert "FUT" not in set(u2["symbol"])
