import numpy as np
import pandas as pd

from swing import watchlist as wl

EQ = pd.DataFrame({"SYMBOL": ["INFY", "HDFCBANK", "LT", "TITAN", "TRENT", "BUY"],
                   "NAME OF COMPANY": ["Infosys Limited", "HDFC Bank Limited", "Larsen & Toubro Limited",
                                       "Titan Company Limited", "Trent Limited", "Buy Ltd"]})


def test_extract_symbols_and_names():
    txt = "STOCKS TO WATCH: INFY, HDFC Bank, Larsen & Toubro, #TITAN and Trent - BUY on dips"
    got = wl.extract_symbols(txt, EQ)
    assert set(got) == {"INFY", "HDFCBANK", "LT", "TITAN", "TRENT"} and "BUY" not in got
    assert wl.looks_like_watchlist(txt, EQ) and not wl.looks_like_watchlist("BUY INFY 1500 SL 1450", EQ)


def test_handle_rates_and_keeps_watching(monkeypatch, tmp_path):
    monkeypatch.setattr(wl, "WL_F", tmp_path / "wl.csv")
    monkeypatch.setattr(wl, "extract_symbols", lambda text, eq=None: ["INFY", "TITAN", "LT"])
    monkeypatch.setattr(wl, "assess", lambda s, top=None: {"symbol": s, "price": 100.0, "score": {"INFY": 3, "TITAN": 8, "LT": 6}[s],
                                                           "reasons": ["strong uptrend"], "signal": None})
    monkeypatch.setattr("swing.high_prob.universe", lambda: ["INFY"])
    t = wl.handle("x", "Firm")
    assert t.index("#TITAN") < t.index("#LT") < t.index("#INFY")          # best first
    assert "8/10" in t and "No trade right now" in t
    assert set(wl.watched()) == {"INFY", "TITAN", "LT"}


# ---- D102: watchlist PICTURES read line by line ---------------------------------------------------------------
EQ2 = pd.DataFrame({"SYMBOL": ["POWERINDIA", "TDPOWERSYS", "MANAPPURAM", "IDEA", "ZEEL", "GODREJPROP", "OIL", "NMDC",
                               "VIPIND", "TARC", "STARHEALTH", "CONSOFINVT", "NDTV", "STAR"],
                    "NAME OF COMPANY": ["Hitachi Energy India Limited", "TD Power Systems Limited",
                                        "Manappuram Finance Limited", "Vodafone Idea Limited",
                                        "Zee Entertainment Enterprises Limited", "Godrej Properties Limited",
                                        "Oil India Limited", "NMDC Limited", "VIP Industries Limited", "TARC Limited",
                                        "Star Health and Allied Insurance Company Limited",
                                        "Consolidated Finvest & Holdings Limited", "New Delhi Television Limited",
                                        "Strides Pharma Science Limited"]})


def test_match_name_spellings_seen_on_real_pictures():
    m = lambda t: wl.match_name(t, EQ2)
    assert m("Hitachi Energy") == m("HITACHIENERGY") == "POWERINDIA"
    assert m("TDPower Systems") == m("TD POWER") == "TDPOWERSYS"
    assert m("Mannapuram Finance") == m("MANAPPURAMFIN") == "MANAPPURAM"      # misspelt + shortened
    assert m("Vodafone ldea") == m("VODAIDEA") == "IDEA"                      # OCR small l for capital I
    assert m("ZEE ENT") == m("Zee") == "ZEEL" and m("GODREJPROPS") == "GODREJPROP" and m("OILINDIA") == "OIL"
    for junk in ("NDTV", "STAR", "Consolidated", "Strong execution", "Block deal today", "Promoter buying"):
        assert m(junk) is None, junk


def _box(x, y, text, arrow=None, h=40):
    return {"x0": x, "y0": y, "x1": x + 300, "y1": y + h, "h": h, "text": text, "conf": 0.9, "arrow": arrow}


def test_read_entries_red_green_columns():
    boxes = [_box(200, 340, "RED"), _box(1200, 340, "RED"), _box(10, 430, "OILINDIA"), _box(920, 430, "NMDC"),
             _box(5, 480, "EBITDA Down 31%, Margin"), _box(926, 490, "Q 2 EBITDA Do Wn 3%"),
             _box(4, 650, "VODAIDEA"), _box(9, 700, "Mixed Q 2, Revenue In-Line,"), _box(930, 760, "Down 23%, Consolidated")]
    e = wl.read_entries(boxes, EQ2)
    assert [x["symbol"] for x in e] == ["OIL", "NMDC", "IDEA"] and all(x["dir"] == "down" for x in e)
    assert e[0]["note"].startswith("EBITDA Down 31%") and e[1]["note"].startswith("Q2 EBITDA")


def test_read_entries_arrows_and_two_names_on_a_line():
    boxes = [_box(200, 330, "Hitachi Energy", "up", 60), _box(206, 400, "Strong positive management commentary"),
             _box(208, 470, "VIPIndustries,TARC", "up", 50), _box(206, 530, "Turnaround quarter"),
             _box(210, 600, "Vodafone ldea", "down", 50), _box(206, 660, "EBITDA misses estimates", "down")]
    e = {x["symbol"]: x for x in wl.read_entries(boxes, EQ2)}
    assert list(e) == ["POWERINDIA", "VIPIND", "TARC", "IDEA"]
    assert e["POWERINDIA"]["dir"] == "up" and e["IDEA"]["dir"] == "down" and e["TARC"]["note"] == "Turnaround quarter"


def test_handle_entries_one_combined_list(monkeypatch, tmp_path):
    monkeypatch.setattr(wl, "WL_F", tmp_path / "wl.csv")
    monkeypatch.setattr(wl, "assess", lambda s, top=None: {"symbol": s, "price": 10.0, "score": 7 if s == "TDPOWERSYS" else 2,
                                                           "reasons": ["strong uptrend" if s == "TDPOWERSYS" else
                                                                       "below its 200-day average (downtrend)"],
                                                           "signal": None})
    monkeypatch.setattr("swing.high_prob.universe", lambda: [])
    ents = [{"symbol": "TDPOWERSYS", "dir": "up", "note": "guidance upgraded"},
            {"symbol": "IDEA", "dir": "down", "note": "EBITDA misses"},
            {"symbol": "TDPOWERSYS", "dir": "up", "note": "Raises FY27 revenue guidance"},
            {"symbol": "ZEEL", "dir": "up", "note": "buyback"}]
    t = wl.handle_entries(ents, "NDTV", 2)
    assert "2 picture(s) → 3 stocks" in t and t.count("#TDPOWERSYS") >= 1 and "#TDPOWERSYS ×2 · 7/10" in t
    assert t.index("BULLISH") < t.index("#ZEEL") < t.index("BEARISH") < t.index("#IDEA")
    assert set(wl.watched()) == {"TDPOWERSYS", "ZEEL"}                    # bearish names are not watched for buys


def test_long_replies_are_split():
    from swing.bot import _chunks
    t = "\n\n".join(["line " * 30] * 60)
    parts = _chunks(t)
    assert len(parts) > 1 and all(len(p) <= 3900 for p in parts)
