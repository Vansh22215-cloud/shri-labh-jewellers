import importlib.util
import json
from pathlib import Path


def _mod():
    p = Path(__file__).resolve().parent.parent / "scripts" / "keep_alive.py"
    spec = importlib.util.spec_from_file_location("keep_alive", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_failure_alert_once_per_6h(tmp_path, monkeypatch):
    m = _mod()
    monkeypatch.setattr(m, "DATA", tmp_path)
    sent = []
    import swing.telegram as tg
    monkeypatch.setattr(tg, "send", lambda s, text, html=False, label="": sent.append((label, text)))
    assert m.alert_failure(["Install packages"]) is True
    assert m.alert_failure(["Install packages"]) is False          # not again within 6 hours
    assert m.alert_failure([]) is False
    assert sent[0][0] == "system problem" and "Install packages" in sent[0][1]
    assert json.loads((tmp_path / "failure_alert.json").read_text())["t"] > 0


def test_system_problem_label_allowed():
    from swing import telegram
    assert telegram.allowed({}, "system problem") and not telegram.allowed({}, "evening trades")
