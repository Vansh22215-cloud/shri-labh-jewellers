import pandas as pd

from swing import nse_filings as nf


class S:
    def __init__(self, data):
        self.data = data

    def get(self, url, headers=None, timeout=None):
        body = next(v for k, v in self.data.items() if k in url)

        class R:
            def raise_for_status(self):
                pass

            def json(self):
                return body
        return R()


ANN = [{"symbol": "ICICIBANK", "desc": "Bagging/Receiving of orders/contracts", "sort_date": "2026-11-10 15:05:59",
        "attchmntText": "ICICI Bank Limited has informed the Exchange about a big order", "attchmntFile": "x.pdf"},
       {"symbol": "ICICIBANK", "desc": "Copy of Newspaper Publication", "sort_date": "2026-11-10 10:00:00",
        "attchmntText": "noise", "attchmntFile": ""},
       {"symbol": "TATASTEEL", "desc": "Disclosure under SEBI Takeover Regulations", "sort_date": "2026-11-09 12:00:00",
        "attchmntText": "Tata Steel Limited has informed the Exchange about promoter stake", "attchmntFile": ""}]


def test_brief_keeps_only_important_filings_for_followed_stocks(monkeypatch, tmp_path):
    monkeypatch.setattr(nf, "CACHE", tmp_path)
    s = S({"corporate-announcements": ANN, "event-calendar": [{"symbol": "ICICIBANK", "date": "12-Nov-2026",
                                                              "purpose": "Financial Results"}],
           "corporates-pit": {"data": []}})
    monkeypatch.setattr(nf, "_session", lambda: s)
    monkeypatch.setattr(nf, "results_summary", lambda sym: None)
    monkeypatch.setattr("swing.archive.write_day", lambda *a, **k: 0)
    t = nf.morning_brief(today="2026-11-11", syms=["ICICIBANK", "TATASTEEL"])
    assert "won an order" in t and "noise" not in t and "Results coming" in t and "Thu 12 Nov" in t
    assert "large shareholder" in t                                  # takeover fallback for insider trades
    assert nf.morning_brief(today="2026-11-11", syms=["INFY"]) is None
    lines, seen = nf.new_filings(set(), syms=["ICICIBANK"])
    assert len(lines) == 1 and nf.new_filings(seen, syms=["ICICIBANK"])[0] == []


def test_insider_feed_rows(monkeypatch, tmp_path):
    monkeypatch.setattr(nf, "CACHE", tmp_path)
    monkeypatch.setattr("swing.archive.write_day", lambda *a, **k: 0)
    s = S({"corporates-pit": {"data": [{"symbol": "INFY", "acqName": "A Promoter", "personCategory": "Promoters",
                                         "tdpTransactionType": "Buy", "secAcq": "1000", "secVal": "15000000",
                                         "date": "10-Nov-2026"}]}, "corporate-announcements": []})
    r = nf.insider(s=s)
    assert r[0]["symbol"] == "INFY" and r[0]["action"] == "Buy" and abs(r[0]["value_cr"] - 1.5) < 1e-9
