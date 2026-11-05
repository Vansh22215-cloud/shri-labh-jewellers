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
    res = telegram.send({"telegram_bot_token": "x", "telegram_chat_id": "1"}, "<b>A &amp; B</b>", html=True)
    assert res == "Telegram message sent"
    assert calls[-1]["text"] == "A & B" and "parse_mode" not in calls[-1]


def test_failure_is_reported_not_raised(monkeypatch):
    monkeypatch.setattr(telegram.requests, "post", lambda *a, **k: R(403))
    monkeypatch.setattr("time.sleep", lambda s: None)
    assert telegram.send({"telegram_bot_token": "x", "telegram_chat_id": "1"}, "hi").startswith("Telegram failed")
    assert telegram.send({}, "hi") == "Telegram not set up"
