from swing import bot, chart_reader, tipcheck


def test_forwarded_picture_is_read_and_checked(monkeypatch, tmp_path):
    monkeypatch.setattr(tipcheck, "TIPS_F", tmp_path / "ft.csv")
    sent, seen = {}, {}

    def fake_api(token, method, **p):
        if method == "getFile":
            return {"result": {"file_path": "x.jpg"}}
        if method == "sendMessage":
            sent["t"] = p["text"]
        return {}

    class R:
        content = b"jpg"

        def raise_for_status(self):
            pass
    monkeypatch.setattr(bot, "_api", fake_api)
    monkeypatch.setattr(bot.requests, "get", lambda url, **k: R())
    monkeypatch.setattr(chart_reader, "read_image", lambda p: {"text": "Weakness Only Sustaining Below 24290",
                                                              "levels": [24296.0], "patterns": [], "axis": True,
                                                              "range": (23000, 25200)})
    monkeypatch.setattr(chart_reader, "guess_instrument", lambda rng: "Nifty")

    def fake_check(text, source="", capital=0, image=None):
        seen.update(text=text, image=image, source=source)
        return "checked"
    monkeypatch.setattr(tipcheck, "check_text", fake_check)
    msg = {"chat": {"id": 1, "type": "private"}, "message_id": 5, "photo": [{"file_id": "a"}],
           "forward_origin": {"type": "channel", "chat": {"title": "Dark Horse"}}}
    bot.handle("T", "1", msg, 45000)
    assert seen["text"].startswith("Nifty") and "24290" in seen["text"] and seen["source"] == "Dark Horse"
    assert seen["image"]["levels"] == [24296.0]
    assert sent["t"].startswith("🖼 Read your chart picture") and "looks like Nifty" in sent["t"]


def test_unreadable_picture_gets_a_clear_answer(monkeypatch):
    sent = {}
    monkeypatch.setattr(bot, "_api", lambda t, m, **p: sent.update(t=p.get("text")) or {"result": {"file_path": "x"}})
    monkeypatch.setattr(bot.requests, "get", lambda url, **k: (_ for _ in ()).throw(OSError("down")))
    bot.handle("T", "1", {"chat": {"id": 1, "type": "private"}, "message_id": 1, "photo": [{"file_id": "a"}]}, 45000)
    assert "couldn't read" in sent["t"]
