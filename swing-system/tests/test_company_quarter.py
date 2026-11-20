"""Company of the Quarter: score, red flags, one pick a quarter, no repeats."""
import json

import pandas as pd
import pytest

from swing import company_quarter as cq


def year(rev, ni, eq=500, debt=100, ocf=None, shares=10e6):
    return {"revenue": rev, "net_income": ni, "ebit": ni * 1.4, "total_assets": 1000, "current_liabilities": 200,
            "current_assets": 400, "equity": eq, "debt": debt, "ocf": ocf if ocf is not None else ni * 1.2,
            "capex": -ni * 0.3, "interest": ni * 0.05, "shares": shares}


def rec(sym, growth=1.2, loss=False):
    ys = {f"{2022 + i}-03-31": year(1000 * growth ** i, (100 if not loss or i < 3 else -10) * growth ** i) for i in range(4)}
    return {"symbol": sym, "years": ys, "promoter_pct": 0.55}


def test_score_and_red_flags():
    good = cq.score(rec("GOOD"), price=100)
    assert good["score"] > 50 and not good["flags"] and good["rev_growth"] == pytest.approx(20, abs=0.1)
    assert "loss in the latest year" in cq.score(rec("BAD", loss=True), 100)["flags"]
    assert cq.score({"symbol": "NEW", "years": {"2026-03-31": year(1, 1)}}, 100) is None     # < 3 years


def test_one_pick_a_quarter_no_repeats(tmp_path, monkeypatch):
    monkeypatch.setattr(cq, "COMPANY", tmp_path)
    monkeypatch.setattr(cq, "PICKS", tmp_path / "picks.csv")
    for s, g in (("AAA", 1.3), ("BBB", 1.1)):
        (tmp_path / f"{s}.json").write_text(json.dumps(rec(s, g)))
    monkeypatch.setattr(cq, "eligible", lambda: {"AAA": 100.0, "BBB": 100.0})
    monkeypatch.setattr(cq, "refresh", lambda syms, n=150: 0)
    monkeypatch.setattr(cq, "message", lambda r, p, q: f"pick {r['symbol']}")
    t = pd.Timestamp("2026-11-20 18:40")
    assert cq.run(send=False, t=t) == "sent AAA"                 # first ever pick: as soon as data is ready
    assert cq.run(send=False, t=t) == "filings read for 2/2; not due"      # one per quarter
    assert not cq.due(pd.Timestamp("2026-12-31 19:00"))
    assert cq.due(pd.Timestamp("2027-01-01 18:31"))              # first weekday of the next quarter, 6:30 pm
    assert cq.run(send=False, t=pd.Timestamp("2027-01-01 18:31")) == "sent BBB"     # AAA not repeated within 4 quarters
