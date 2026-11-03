import pandas as pd

from swing import bot, journal


def test_bought_and_sold(tmp_path, monkeypatch):
    monkeypatch.setattr(journal, "MY_TRADES", tmp_path / "my.csv")
    monkeypatch.setattr("swing.config.DATA", tmp_path)
    r = bot.trade_command("/bought ICICIBANK 5 1425 1340")
    assert "Recorded" in r and "1340" in r
    my = journal.load_my_trades()
    assert list(my["symbol"]) == ["ICICIBANK"] and float(my.iloc[0]["stop"]) == 1340
    r2 = bot.trade_command("/sold ICICIBANK 1500")
    assert "P&L Rs 375" in r2
    assert journal.load_my_trades().empty
