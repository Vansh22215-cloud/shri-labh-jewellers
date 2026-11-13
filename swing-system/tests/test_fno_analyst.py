import numpy as np
import pandas as pd

from swing import fno_analyst as fa, options_check as oc

SAMPLE = "📈📉 VOLTAS\n\n🖲 NOV 1120 PE 25-26\n\n✅ Target-35-42-50-58+\n\n⛔️ Stoploss-1150 SPOT (75 Min CB)\n\n✨ Lot Size- 375"


def test_parse_owner_sample():
    o = oc.parse_option(SAMPLE)
    assert (o["symbol"], o["kind"], o["strike"], o["month"]) == ("VOLTAS", "PE", 1120.0, 11)
    assert (o["entry_low"], o["entry_high"], o["stop"], o["stop_on_spot"], o["stop_candle_min"], o["lot"]) == \
        (25.0, 26.0, 1150.0, True, 75, 375)
    assert o["targets"] == [35.0, 42.0, 50.0, 58.0]


def _daily(drift):
    idx = pd.bdate_range("2023-01-02", periods=600)
    c = 1130 * np.exp(np.cumsum(np.random.default_rng(2).normal(drift, 0.015, 600)))
    c = c / c[-1] * 1130
    return pd.DataFrame({"open": c, "high": c * 1.01, "low": c * 0.99, "close": c, "volume": 1e6}, index=idx)


def test_analyse_scores_and_explains(monkeypatch):
    o = oc.parse_option(SAMPLE)
    d = _daily(-0.001)
    monkeypatch.setattr(fa, "_spot_and_bars", lambda s: (1130.0, None, d))
    monkeypatch.setattr(fa, "_contract", lambda *a: (pd.Timestamp.now().normalize() + pd.Timedelta(days=20), None, 375))
    monkeypatch.setattr(fa, "_option_quote", lambda ts: None)
    a = fa.analyse(o, "")
    assert 1 <= a["score"] <= 10 and a["spot_sl"] == 1150.0 and a["spot_t1"] < 1130
    txt = fa.reply(o, a)
    for part in ("PROBABILITY - ", "/10", "Why it can", "Plan:", "stop 1,150 SPOT", "Research, not advice"):
        assert part in txt
    assert a["take"] is (a["score"] >= 7 and bool(a["loss_lot"] is None or a["loss_lot"] <= 45000 * 0.05))


def test_failed_call_and_notes(monkeypatch, tmp_path):
    o = dict(oc.parse_option(SAMPLE), stop=1100.0)          # PE with spot stop BELOW the price: already failed
    monkeypatch.setattr(fa, "_spot_and_bars", lambda s: (1130.0, None, _daily(0)))
    monkeypatch.setattr(fa, "_contract", lambda *a: (pd.Timestamp.now().normalize() + pd.Timedelta(days=20), None, 375))
    monkeypatch.setattr(fa, "_option_quote", lambda ts: None)
    assert fa.analyse(o)["score"] == 1
    monkeypatch.setattr("swing.config.PRIVATE", tmp_path)
    n = fa.note("Banks look strong, rally likely above 52000", "Ch")
    assert "bullish" in n and "52000" in n
