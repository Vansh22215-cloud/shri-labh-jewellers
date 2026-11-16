import pandas as pd


def test_open_tips_command(monkeypatch, tmp_path):
    from swing import bot
    from swing import live_engine as le
    monkeypatch.setattr(le, "TIPS_F", tmp_path / "t.csv")
    pd.DataFrame([{"time": "2026-11-16 18:44", "type": "NORMAL", "symbol": "ABC", "side": "buy", "entry": 100,
                   "stop": 80, "status": "open", "setup": "RCP", "day": "2026-11-16"},
                  {"time": "2026-11-10 18:40", "type": "NORMAL", "symbol": "OLD", "side": "buy", "entry": 50,
                   "stop": 45, "status": "done", "setup": "HP", "day": "2026-11-10"}]).to_csv(tmp_path / "t.csv", index=False)
    t = bot.open_tips_text()
    assert "OPEN TIPS (1)" in t and "Positional · #ABC" in t and "OLD" not in t and "SELL alert" in t
