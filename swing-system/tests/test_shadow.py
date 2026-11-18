"""Silent promoter-buying record (owner 18 Nov): recorded, settled from prices, never sent."""
import numpy as np
import pandas as pd

from swing import shadow


def test_records_promoter_purchases_only_and_settles_without_messages(monkeypatch, tmp_path):
    monkeypatch.setattr(shadow, "FILE", tmp_path / "s.csv")
    from swing import telegram
    monkeypatch.setattr(telegram, "send", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no messages")))
    rows = [{"symbol": "ABC", "role": "Promoters", "mode": "Market Purchase", "action": "Buy", "value_cr": 0.5,
             "date": "03-Nov-2026 20:15"},
            {"symbol": "ABC", "role": "Promoter Group", "mode": "Market Purchase", "action": "Buy", "value_cr": 0.2,
             "date": "03-Nov-2026 21:00"},                                     # same stock, same day: one event
            {"symbol": "XYZ", "role": "Employees/Designated Employees", "mode": "Market Purchase", "action": "Buy",
             "value_cr": 5, "date": "03-Nov-2026"},                            # not a promoter
            {"symbol": "SMALL", "role": "Promoters", "mode": "Market Purchase", "action": "Buy", "value_cr": 0.05,
             "date": "03-Nov-2026"},                                           # below Rs 10 lakh
            {"symbol": "PLG", "role": "Promoters", "mode": "Pledge Creation", "action": "Pledge", "value_cr": 9,
             "date": "03-Nov-2026"}]
    assert shadow.record(rows) == 1 and shadow.record(rows) == 0             # ABC twice on one day = one event
    t = shadow._load()
    assert set(t["symbol"]) == {"ABC"} and t.iloc[0]["value_cr"] == "0.7"
    idx = pd.bdate_range("2026-09-01", "2026-11-20")
    d = pd.DataFrame({"open": np.linspace(100, 110, len(idx)), "close": np.linspace(100, 110, len(idx)),
                      "volume": 1e6}, index=idx)
    assert shadow.settle(load=lambda s: d) >= 1
    t = shadow._load()
    r = t.iloc[0]
    assert r["status"] == "done" and r["entry_date"] == "2026-11-04" and r["exit_date"] == "2026-11-11"
    assert shadow.summary()["done"] >= 1
