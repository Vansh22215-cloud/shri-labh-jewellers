import numpy as np
import pandas as pd
from PIL import Image, ImageDraw

from swing import chart_reader as cr


def test_price_tokens_from_ocr_text():
    assert cr._price_token("24,800.00") == 24800
    assert cr._price_token("24.800.00") == 24800
    assert cr._price_token("25,200.0o") == 25200
    assert cr._price_token("1.08520") == 1.0852
    assert cr._price_token("24,30.00") is None          # garbled: ignored, not misread
    assert cr._price_token("How") is None


def test_axis_fit_ignores_misreads():
    toks = [(950, 100, 25200.0), (950, 300, 24800.0), (950, 500, 24400.0), (950, 700, 24000.0),
            (950, 400, 34700.0), (100, 300, 13.0)]                          # 34700: OCR error; 13: date label
    a, b, n = cr.fit_axis(toks, 1000)
    assert n == 4 and abs(a + b * 600 - 24200) < 1


def test_drawn_lines_found_and_priced():
    img = Image.new("RGB", (1000, 800), "white")
    d = ImageDraw.Draw(img)
    for x in range(50, 850, 20):                                            # candles: short marks, not lines
        d.rectangle([x, 300 + x % 97, x + 8, 340 + x % 97], fill="green")
    d.line([0, 250, 880, 250], fill="blue", width=2)
    d.line([0, 610, 880, 610], fill="black", width=1)
    ys = cr.horizontal_lines(img)
    assert len(ys) == 2 and abs(ys[0] - 250) < 2 and abs(ys[1] - 610) < 2


def test_guess_instrument_from_price_scale():
    prices = {"Nifty": 24600, "Bank Nifty": 52000, "Sensex": 80500, "XAUUSD": 2700, "EURUSD": 1.12}
    assert cr.guess_instrument((23000, 25200), prices) == "Nifty"
    assert cr.guess_instrument((1000, 90000), prices) is None             # several fit: no guess
    assert cr.guess_instrument(None, prices) is None


def test_apply_image_uses_nearest_line_and_pattern_side():
    v = {"side": None, "stop": None, "wrong_if": None}
    notes = cr.apply_image(v, {"levels": [23950, 24296, 24442, 30000], "patterns": [("double bottom", "buy")]}, 24610)
    assert v["side"] == "buy" and v["wrong_if"] == ("below", 24442)
    assert any("double bottom" in n for n in notes) and not any("30,000" in n for n in notes)


def test_own_patterns_runs_on_one_instrument():
    rng = np.random.default_rng(3)
    idx = pd.bdate_range("2023-01-02", periods=400)
    c = 100 * np.exp(np.cumsum(rng.normal(0.001, 0.012, 400)))
    df = pd.DataFrame({"open": c * 0.998, "high": c * 1.01, "low": c * 0.99, "close": c,
                       "volume": rng.integers(1e5, 3e5, 400).astype(float)}, index=idx)
    fired, candles = cr.own_patterns(df)
    assert isinstance(fired, list) and isinstance(candles, list)
    assert cr.own_patterns(df.iloc[:100]) == ([], [])                    # too little history


def test_title_line_gives_timeframe_and_price():
    h = cr.header_info("Gold Spot / U.S. Dollar · 15 · OANDA O 4,050.13 H 4,052.06 L 4,044.88 C 4,046.51")
    assert h == {"timeframe_min": 15, "chart_price": 4046.51}
    assert cr.header_info("Nifty 50 Index . 1H . NSE")["timeframe_min"] == 60
    assert "chart_price" not in cr.header_info("C 100.5 only")


def test_position_tool_long_and_short_light_and_dark():
    for bg, gz, rz in (("white", (206, 235, 230), (252, 215, 218)), ((19, 23, 34), (17, 49, 53), (54, 29, 40))):
        for short in (False, True):
            img = Image.new("RGB", (1200, 800), bg)
            d = ImageDraw.Draw(img)
            a, b = (rz, gz) if short else (gz, rz)
            d.rectangle([500, 330, 900, 440], fill=a)
            d.rectangle([500, 440, 900, 555], fill=b)
            for x in range(100, 1000, 12):                                  # solid candles on top
                d.rectangle([x, 400 + x % 50, x + 6, 460 + x % 50], fill=(8, 153, 129) if x % 24 else (242, 54, 69))
            p = cr.position_tool(img, (4090.0, -0.1, 5))
            assert p["side"] == ("sell" if short else "buy")
            assert abs(p["entry"] - 4046) < 0.5 and {round(p["stop"]), round(p["target"])} == {4057, 4034}
        plain = Image.new("RGB", (1200, 800), bg)
        assert cr.position_tool(plain, (4090.0, -0.1, 5)) is None


def test_gold_chart_title_is_not_read_as_dollar_stock(monkeypatch):
    from swing import market_views, tipcheck
    eq = pd.DataFrame({"SYMBOL": ["DOLLAR", "GOLDBEES"], "NAME OF COMPANY": ["Dollar Industries Ltd", "Gold ETF"],
                       " SERIES": ["EQ", "EQ"]})
    monkeypatch.setattr(tipcheck, "equity_list", lambda: eq)
    seen = {}
    monkeypatch.setattr(market_views, "check", lambda text, source="", image=None: seen.setdefault("ok", text) or "market")
    monkeypatch.setattr(tipcheck, "save", lambda *a, **k: None)
    tipcheck.check_text("Gold Spot / U.S. Dollar · 15 · OANDA", source="x")
    assert "ok" in seen                                                     # went to the gold check, not DOLLAR
    seen.clear()
    monkeypatch.setattr(tipcheck, "evaluate", lambda tip, capital: ("RISKY", [], {"ltp": 265.0}))
    monkeypatch.setattr("swing.chart_reader.own_patterns_for", lambda *a, **k: None)
    r = tipcheck.check_text("BUY DOLLAR 265 SL 250", source="x", image={"chart_price": 4046.5})
    assert "CAN'T JUDGE" in r and "wrong instrument" in r                   # price mismatch: refuses to guess
