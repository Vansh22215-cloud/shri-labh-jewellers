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
