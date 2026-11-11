from swing import telegram


class R:
    def __init__(self, code, body=None):
        self.status_code, self._b, self.text = code, body or {}, ""

    def json(self):
        return self._b


def test_long_html_is_split_on_lines_with_balanced_tags():
    text = "<b>head</b>\n<pre>" + "\n".join("row %d" % i for i in range(2000)) + "</pre>\nend"
    parts = telegram._split(text)
    assert len(parts) > 1 and all(len(p) <= 3800 for p in parts)
    for p in parts:
        b = telegram._balanced(p)
        assert b.count("<pre>") == b.count("</pre>")
    assert "\n".join(parts) == text


def test_plain_fallback_and_retry(monkeypatch):
    calls = []
    seq = [R(500), R(400), R(200)]          # server error -> retried; HTML rejected -> plain text; ok

    def fake_post(url, data=None, timeout=None):
        calls.append(data)
        return seq.pop(0)
    monkeypatch.setattr(telegram.requests, "post", fake_post)
    monkeypatch.setattr("time.sleep", lambda s: None)
    res = telegram.send({"telegram_bot_token": "x", "telegram_chat_id": "1"}, "<b>A &amp; B</b>", html=True, label="trade tip")
    assert res == "Telegram message sent"
    assert calls[-1]["text"] == "A & B" and "parse_mode" not in calls[-1]


def test_failure_is_reported_not_raised(monkeypatch):
    monkeypatch.setattr(telegram.requests, "post", lambda *a, **k: R(403))
    monkeypatch.setattr("time.sleep", lambda s: None)
    assert telegram.send({"telegram_bot_token": "x", "telegram_chat_id": "1"}, "hi", label="exit alert").startswith("Telegram failed")
    assert telegram.send({}, "hi", label="trade tip") == "Telegram not set up"


def test_only_owner_chosen_messages_go_out(monkeypatch):
    monkeypatch.setattr(telegram.requests, "post", lambda *a, **k: (_ for _ in ()).throw(AssertionError("sent")))
    s = {"telegram_bot_token": "x", "telegram_chat_id": "1"}
    for label in ("hourly tips update", "weekly summary", "system notice", "research upgrade", "message"):
        assert telegram.send(s, "x", label=label) == "muted"
    assert telegram.send_document(s, "f.html") == "muted"
