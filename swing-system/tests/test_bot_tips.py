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
    assert "OPEN TIPS (1)" in t and "POSITIONAL TRADE" in t and "#ABC" in t and "OLD" not in t and "SELL alert" in t
    assert "sent 16 Nov" in t


def test_resend_once(monkeypatch, tmp_path):
    import json
    from swing import live_engine as le, oneoff_resend as orr, telegram
    monkeypatch.setattr(le, "TIPS_F", tmp_path / "t.csv")
    monkeypatch.setattr(orr, "DONE_F", tmp_path / "done.json")
    req = tmp_path / "req.json"
    req.write_text(json.dumps({"id": "x", "day": "2026-11-16", "setup": "RCP"}))
    monkeypatch.setattr(orr, "REQ_F", req)
    pd.DataFrame([{"time": "2026-11-16 18:44", "type": "NORMAL", "symbol": f"S{i}", "side": "buy", "entry": 100,
                   "stop": 80, "qty": 2, "rank": 6, "status": "open", "setup": "RCP", "day": "2026-11-16"}
                  for i in range(4)]).to_csv(tmp_path / "t.csv", index=False)
    sent = []
    monkeypatch.setattr(telegram, "send", lambda s, text, html=False, label="": sent.append(text))
    orr.maybe_run()
    orr.maybe_run()
    assert len(sent) == 5 and "POSITIONAL TRADE" in sent[1] and "Stop-loss: 80.00" in sent[1]
