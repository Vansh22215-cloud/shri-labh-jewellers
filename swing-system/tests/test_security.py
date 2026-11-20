"""Security tests (audit 17 Nov): credential scrubbing, read-only Kite, no order execution anywhere."""
import logging
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_redact_removes_tokens():
    from swing.config import redact
    s = ("HTTPSConnectionPool(host='api.telegram.org'): url: /bot1234567890:AAF0zABCDEFGHIJKLMNOPQRSTUVWXYZ0123456/getUpdates "
         "access_token=abcdef1234567890 api_secret: 'zyxwvutsrq9876543210' Authorization: token abc123:def456ghi789")
    out = redact(s)
    assert "AAF0z" not in out and "abcdef1234567890" not in out and "zyxwvutsrq" not in out and "def456ghi789" not in out


def test_logger_scrubs_before_writing(tmp_path, caplog):
    from swing.config import get_logger
    log = get_logger()
    with caplog.at_level(logging.INFO, logger="swing"):
        log.warning("bot error: /bot9022079525:AAF0z-TRra5tCxxxxxxxxxxxxxxxxxxxxxxxxx/getUpd")
    assert "AAF0z" not in caplog.text and "<REDACTED>" in caplog.text


def test_no_order_placing_code_anywhere():
    """The system is a manual trade-finder: no Kite order / GTT / margin / position-changing endpoint may exist."""
    bad = re.compile(r"(/orders|/gtt|place_order|modify_order|cancel_order|/portfolio/positions\b.*(put|post)|"
                     r"requests\.(post|put|delete)\([^)]*kite)", re.I)
    hits = []
    for f in list((ROOT / "swing").glob("*.py")) + list((ROOT / "scripts").glob("*.py")):
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            line = line.replace('"/margins/orders"', "")  # Kite's margin CALCULATOR only - allowed by the owner 21 Nov 2026
            if bad.search(line) and "test" not in f.name:
                hits.append(f"{f.name}:{i}: {line.strip()[:100]}")
    assert not hits, hits


def test_kite_client_is_read_only(monkeypatch):
    from swing import kite
    calls = []
    monkeypatch.setattr(kite, "token", lambda now=None: "x")
    monkeypatch.setattr(kite, "keys", lambda: ("k", "s"))

    class R:
        status_code = 200
        def raise_for_status(self):
            pass
        def json(self):
            return {"data": {}}
    monkeypatch.setattr(kite.requests, "get", lambda *a, **k: (calls.append(a[0]), R())[1])
    for bad in ("/orders", "/orders/regular", "/gtt/triggers", "/user/margins", "/portfolio/holdings"):
        try:
            kite._get(bad)
            raise AssertionError(f"{bad} was allowed")
        except PermissionError:
            pass
    assert not calls
    kite._get("/quote", params=[("i", "NSE:INFY")])
    assert calls and calls[0].endswith("/quote")


def test_bot_key_paste_mistakes_are_repaired_and_never_logged():
    from swing.config import clean_bot_token, token_shape
    k = "1234567890:AAF0zABCDEFGHIJKLMNOPQRSTUVWXYZ0123"
    for pasted in (k, f" {k}\n", f'"{k}"', f"bot{k}", f"https://api.telegram.org/bot{k}/getMe", f"1234567890: AAF0z{k[16:]}"):
        assert clean_bot_token(pasted) == k
    assert "looks right" in token_shape(k) and k not in token_shape(k)
    assert "35" in token_shape(k[:-3]) and k[:-3] not in token_shape(k[:-3])
    assert "missing" in token_shape("")
