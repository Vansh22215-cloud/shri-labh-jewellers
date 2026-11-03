import pandas as pd

from swing import intel_news


def test_matching_and_tone(tmp_path, monkeypatch):
    f = tmp_path / "news.csv"
    now = pd.Timestamp.now(tz="UTC")
    pd.DataFrame([
        {"source": "X", "title": "Tata Steel Q2 profit rises 20%", "link": "", "published": now},
        {"source": "X", "title": "SEBI order against Some Other Ltd promoters", "link": "", "published": now},
        {"source": "X", "title": "HDFCBANK shares in focus after forensic audit report", "link": "", "published": now},
    ]).to_csv(f, index=False)
    monkeypatch.setattr(intel_news, "STORE", f)
    t = intel_news.news_for("TATASTEEL", "Tata Steel Limited")
    assert len(t) == 1 and t[0]["tone"] == "positive"
    h = intel_news.news_for("HDFCBANK", "HDFC Bank Limited")
    assert h and h[0]["tone"] == "RED FLAG"
    assert intel_news.news_for("SBIN", "State Bank of India") == []
