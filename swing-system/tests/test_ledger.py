"""ATLAS immutable memory: append-only, only changes are written, tampering is detected."""
import pandas as pd

from swing import ledger


def test_append_only_and_tamper_evident(monkeypatch, tmp_path):
    monkeypatch.setattr(ledger, "LEDGER", tmp_path / "l.jsonl")
    R = pd.DataFrame([{"source": "VANTAGE", "type": "RCP", "date": "2026-11-17", "symbol": "A", "status": "open", "result_pct": 1.0}])
    assert ledger.append(R, "2026-11-18") == 1
    assert ledger.append(R, "2026-11-19") == 0                       # nothing changed -> nothing written
    R.loc[0, "result_pct"] = 3.0
    assert ledger.append(R, "2026-11-20") == 1
    assert ledger.verify() == (True, 2)
    text = (tmp_path / "l.jsonl").read_text().replace('"result_pct": 1.0', '"result_pct": 9.0')
    (tmp_path / "l.jsonl").write_text(text)                           # someone rewrites the past
    assert ledger.verify()[0] is False
