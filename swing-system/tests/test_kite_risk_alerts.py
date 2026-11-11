from datetime import datetime

import pandas as pd

from swing import alerts, kite, risk


class R:
    def __init__(self, code, body):
        self.status_code, self._b, self.text = code, body, ""

    def json(self):
        return self._b

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


def _keys(monkeypatch, tmp_path):
    monkeypatch.setenv("KITE_API_KEY", "abc123")
    monkeypatch.setenv("KITE_API_SECRET", "s3cr3t")
    monkeypatch.setattr(kite, "TOKEN_F", tmp_path / "kite_token.bin")


def test_kite_login_stores_encrypted_token_until_6am(monkeypatch, tmp_path):
    _keys(monkeypatch, tmp_path)
    sent = {}
    monkeypatch.setattr(kite.requests, "post", lambda url, data=None, headers=None, timeout=None:
                        sent.update(data) or R(200, {"status": "success", "data": {"access_token": "TOKEN42"}}))
    ok, msg = kite.exchange("reqtok99")
    assert ok and "connected" in msg
    import hashlib
    assert sent["checksum"] == hashlib.sha256(b"abc123reqtok99s3cr3t").hexdigest()
    assert b"TOKEN42" not in kite.TOKEN_F.read_bytes()                     # stored encrypted
    assert kite.token() == "TOKEN42"
    late = datetime(2100, 1, 1, tzinfo=kite.IST)
    assert kite.token(late) is None                                        # expired next morning
    assert kite.exchange("bad token!")[0] is False                         # never sent on
    monkeypatch.delenv("KITE_API_KEY")
    assert not kite.configured() and kite.token() is None


def test_kite_quotes_and_fallback(monkeypatch, tmp_path):
    _keys(monkeypatch, tmp_path)
    kite.save_token("T")
    body = {"data": {"NSE:INFY": {"last_price": 1500.5, "ohlc": {"open": 1490, "high": 1510, "low": 1480, "close": 1495}}}}
    monkeypatch.setattr(kite.requests, "get", lambda *a, **k: R(200, body))
    q = kite.quotes(["INFY"])
    assert q["INFY"]["last"] == 1500.5 and q["INFY"]["prev"] == 1495
    monkeypatch.setattr(kite.requests, "get", lambda *a, **k: R(403, {}))
    assert kite.quotes(["INFY"]) == {} and not kite.TOKEN_F.exists()       # rejected token is dropped


def test_risk_check_standard_limits():
    st = {"invested": 0.0, "realised_today": 0.0, "new_today": 0}
    s = {"capital": 45000}
    assert risk.check("buy", 5, 1425, 1340, state=st, settings=s)[0]
    ok, why, _ = risk.check("buy", 10, 1425, 1340, state=st, settings=s)
    assert not ok and any("over your limit ₹450" in w for w in why) and any("single-order" in w for w in why)
    assert not risk.check("buy", 5, 1425, None, state=st, settings=s)[0]
    assert not risk.check("buy", 1, 100, 95, state=dict(st, new_today=3), settings=s)[0]
    assert not risk.check("buy", 1, 100, 95, state=dict(st, realised_today=-950), settings=s)[0]
    assert risk.size(1425, 1340, state=st, settings=s) == 5               # 450/85 = 5.3 -> 5
    assert risk.size(100, 99, state=st, settings=s) == 112                # capped by 25% of capital


def test_ticket_buttons_record_the_trade(monkeypatch, tmp_path):
    from swing import journal
    monkeypatch.setattr(risk, "TICKETS_F", tmp_path / "t.csv")
    monkeypatch.setattr(journal, "MY_TRADES", tmp_path / "my.csv")
    monkeypatch.setattr(risk, "account_state", lambda today=None: {"invested": 0.0, "realised_today": 0.0, "new_today": 0})
    t = risk.new_ticket("ICICIBANK", "buy", 1425, 1340, 1594, "system tip", settings={"capital": 45000})
    assert t["status"] == "READY" and t["qty"] == 5 and "BUY 5 ICICIBANK" in risk.ticket_text(t)
    assert risk.buttons(t)["inline_keyboard"][0][0]["callback_data"] == f"placed:{t['id']}"
    r = risk.on_button(f"placed:{t['id']}")
    assert r.startswith("✅ Recorded") and "ICICIBANK" in pd.read_csv(journal.MY_TRADES)["symbol"].tolist()
    assert "already" in risk.on_button(f"placed:{t['id']}")
    b = risk.new_ticket("X", "buy", 100, 10, 200, "x", settings={"capital": 45000})
    assert b["status"] in ("READY", "BLOCKED") and b["qty"] <= 5


def test_alert_events_fire_once(monkeypatch, tmp_path):
    monkeypatch.setattr(alerts, "FIRED_F", tmp_path / "fired.json")
    it = {"key": "my|INFY|x", "name": "INFY", "label": "your trade", "side": "buy", "entry_lo": None, "entry_hi": None,
          "entry": 1500.0, "stop": 1450.0, "target": None, "qty": 3, "kind": "mine", "ticker": None, "offset": 0.0}
    monkeypatch.setattr(alerts, "items", lambda today: [it])
    q = lambda syms: ({"INFY": {"last": 1455.0, "high": 1501.0, "low": 1448.0, "prev": 1500.0}}, "test")
    now = pd.Timestamp("2026-11-11 11:03", tz="Asia/Kolkata")
    m = alerts.check(send=False, now=now, quote_fn=q)
    assert len(m) == 1 and "hit the stop 1,450" in m[0] and "₹-150 on 3" in m[0]
    assert alerts.check(send=False, now=now, quote_fn=q) == []                # once only
    pend = dict(it, key="sys|A|d", kind="pending", entry_lo=1400.0, entry_hi=1420.0, target=1600.0)
    assert alerts.events(pend, {"last": 1410.0, "high": 1415, "low": 1405})[0][0] == "entry"
    near = dict(it, key="k2", stop=1400.0)
    assert alerts.events(near, {"last": 1410.0, "high": 1412, "low": 1408})[0][0] == "near"
    tgt = dict(it, kind="open", target=1600.0, stop=1400.0)
    assert [c for c, _ in alerts.events(tgt, {"last": 1601.0, "high": 1605, "low": 1590})] == ["target"]
    assert alerts.market_open(pd.Timestamp("2026-11-11 09:20", tz="Asia/Kolkata"))
    assert not alerts.market_open(pd.Timestamp("2026-11-14 10:00", tz="Asia/Kolkata"))    # Saturday


def test_bot_login_and_button(monkeypatch, tmp_path):
    from swing import bot
    calls = []
    monkeypatch.setattr(bot, "_api", lambda tok, method, **p: calls.append((method, p)) or {"ok": True})
    monkeypatch.setattr(kite, "exchange", lambda rt: (True, f"✅ Kite connected ({rt})"))
    bot.handle("T", "1", {"chat": {"id": 1, "type": "private"}, "message_id": 3, "text": "/start kite_abc123"}, 45000)
    assert any("Kite connected (abc123)" in p.get("text", "") for m, p in calls)
    calls.clear()
    monkeypatch.setattr("swing.risk.on_button", lambda data: "✅ Recorded: " + data)
    bot.handle_button("T", "1", {"id": "q1", "data": "placed:1234", "message": {"chat": {"id": 1}}})
    assert calls[0][0] == "answerCallbackQuery" and "placed:1234" in calls[1][1]["text"]
    calls.clear()
    bot.handle_button("T", "1", {"id": "q2", "data": "placed:1234", "message": {"chat": {"id": 999}}})
    assert len(calls) == 1 and "Not your ticket" in calls[0][1]["text"]      # strangers can't press it
