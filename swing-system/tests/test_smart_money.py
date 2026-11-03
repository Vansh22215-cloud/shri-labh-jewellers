import pandas as pd

from swing import smart_money as sm


def test_who_classification():
    assert sm.who("GRAVITON RESEARCH CAPITAL LLP") is None          # HFT ignored
    assert sm.who("SBI MUTUAL FUND") == "well-known investor/fund"
    assert sm.who("XYZ ASSET MANAGEMENT LTD") == "institution"
    assert sm.who("RAMESH KUMAR") is None


def test_netting_and_threshold(monkeypatch, tmp_path):
    monkeypatch.setattr(sm, "LOG", tmp_path / "s.csv")
    idx = pd.bdate_range("2025-01-01", periods=260)
    px = pd.DataFrame({"close": pd.Series(range(100, 360), index=idx, dtype=float)})
    monkeypatch.setattr(sm.data_prices, "load", lambda s: px)
    deals = pd.DataFrame([
        {"Date": "02-NOV-2026", "Symbol": "AAA", "Client Name": "ABC MUTUAL FUND", "Buy/Sell": "BUY", "Quantity Traded": 200000, "Trade Price / Wght. Avg. Price": 500},
        {"Date": "02-NOV-2026", "Symbol": "AAA", "Client Name": "ABC MUTUAL FUND", "Buy/Sell": "SELL", "Quantity Traded": 50000, "Trade Price / Wght. Avg. Price": 500},
        {"Date": "02-NOV-2026", "Symbol": "BBB", "Client Name": "ABC MUTUAL FUND", "Buy/Sell": "BUY", "Quantity Traded": 100, "Trade Price / Wght. Avg. Price": 500},
    ])
    r = sm.todays_buys(deals, {"AAA", "BBB"})
    assert list(r["symbol"]) == ["AAA"] and r.iloc[0]["net_buy_cr"] == 7.5 and bool(r.iloc[0]["trend_ok"])
