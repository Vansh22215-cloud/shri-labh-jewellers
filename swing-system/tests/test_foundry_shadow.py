import json

import numpy as np
import pandas as pd

from swing import foundry_shadow as fs


class FakeFoundry:
    FRESH = pd.Timestamp("2026-11-20")
    EXITS = {"x": {"k": 2, "T": 20, "R": 3}}

    def __init__(self):
        idx = pd.bdate_range("2026-11-02", periods=20)
        self.P = {"idx": idx, "syms": ["AAA", "BBB"]}
        n = len(idx)
        C = np.full((n, 2), 100.0)
        self.P.update(O_a=C.copy(), H_a=C + 1, L_a=C - 1, C_a=C.copy(), atr_a=np.full((n, 2), 2.0))
        sig = pd.DataFrame(False, index=idx, columns=self.P["syms"])
        sig.iloc[-1, 0] = True                                   # AAA signals today
        self._sig = sig

    def trades(self, sig, ex):
        return pd.DataFrame(columns=["exit", "entry", "signal"])

    def period(self, T, per):
        return T


def _rules(tmp_path, monkeypatch, kind="foundry-tips"):
    (tmp_path / "strategies").mkdir()
    (tmp_path / "strategies" / "lab_rules.json").write_text(json.dumps({"rules": [
        {"id": "FTP-AB12", "kind": kind, "status": "approved", "name": "test strategy", "entry": "e", "filter": "f", "exit": "x"}]}))
    monkeypatch.setattr(fs, "ROOT", tmp_path)
    monkeypatch.setattr(fs, "REPORT", tmp_path / "shadow.md")
    monkeypatch.setattr(fs, "TIPS_F", tmp_path / "tips.csv")
    fo = FakeFoundry()
    monkeypatch.setattr(fs, "_foundry", lambda: fo)
    monkeypatch.setattr(fs, "_signal", lambda f, r: f._sig)
    return fo


def test_tips_only_after_second_approval_and_once(tmp_path, monkeypatch):
    from swing import telegram, config, registry
    _rules(tmp_path, monkeypatch)
    monkeypatch.setattr(registry, "open_stocks", lambda: {})
    monkeypatch.setattr(config, "load_settings", lambda: {"capital": 51000, "risk_limits": {"risk_per_trade_pct": 1, "max_order_pct": 25}})
    out = []
    monkeypatch.setattr(telegram, "send_reliable", lambda s, text, label="": out.append((label, text)))
    assert fs.run() == 1
    assert out and out[0][0] == "trade tip" and "#AAA" in out[0][1] and "tomorrow's open" in out[0][1]
    fs.run()
    assert len([o for o in out if o[0] == "trade tip"]) == 1              # never twice
    assert (tmp_path / "shadow.md").exists()


def test_shadow_sends_nothing(tmp_path, monkeypatch):
    from swing import telegram
    _rules(tmp_path, monkeypatch, kind="foundry-shadow")
    out = []
    monkeypatch.setattr(telegram, "send_reliable", lambda s, text, label="": out.append(text))
    assert fs.run() == 1 and out == [] and not (tmp_path / "tips.csv").exists()


def test_exit_check_stop_and_time():
    fo = FakeFoundry()
    row = {"sym": "AAA", "signal": str(fo.P["idx"][2].date()), "atr": "2.0"}
    fo.P["L_a"][-1, 0] = 90.0                                            # today's low under the stop (100 - 2x2)
    assert fs.exit_check(fo, row, {"k": 2, "T": 30})[0] == "stop"
    fo.P["L_a"][-1, 0] = 99.0
    assert fs.exit_check(fo, row, {"k": 2, "T": 10})[0] == "time"
    assert fs.exit_check(fo, row, {"k": 2, "T": 30}) is None
