"""Read a chart IMAGE forwarded to the bot (free, runs on GitHub's computer, no paid AI).

1. Text on the picture (free OCR, rapidocr): symbol / title, timeframe, written levels ("weakness below 24290"),
   pattern names ("double bottom", "H&S", "breakout", "order block" ...), entry / SL / TP boxes.
2. The price scale: numbers on the right edge are fitted to their height on the picture (robust line fit), so
   any long horizontal line drawn on the chart (support, resistance, entry, stop) is turned into a PRICE.
3. Everything found is added to the message text and checked like a typed tip (market_views / tipcheck), and the
   system's OWN pattern detectors run on the real prices of that instrument (own_patterns) - the picture is only
   used to know WHAT to check; the verdict always comes from real data.
Limits (said in the reply): OCR can misread blurry screenshots; lines are found only if long and clearly drawn.
"""
import re

import numpy as np

from .config import get_logger

log = get_logger()
_OCR = None

PATTERN_WORDS = {   # name on a chart -> direction it usually implies (None = depends on breakout side)
    r"INV(?:ERSE|\.)? ?(?:H ?& ?S|HEAD (?:AND|&) SHOULDERS?)": ("inverse head and shoulders", "buy"),
    r"H ?& ?S|HEAD (?:AND|&) SHOULDERS?": ("head and shoulders", "sell"),
    r"DOUBLE ?BOTTOM|W ?PATTERN": ("double bottom", "buy"),
    r"DOUBLE ?TOP|M ?PATTERN": ("double top", "sell"),
    r"TRIPLE ?BOTTOM": ("triple bottom", "buy"),
    r"TRIPLE ?TOP": ("triple top", "sell"),
    r"CUP (?:AND|&|N) ?HANDLE": ("cup and handle", "buy"),
    r"ASC(?:ENDING)? ?TRIANGLE": ("ascending triangle", "buy"),
    r"DESC(?:ENDING)? ?TRIANGLE": ("descending triangle", "sell"),
    r"SYM(?:METRICAL)? ?TRIANGLE|TRIANGLE": ("triangle", None),
    r"BULL(?:ISH)? ?FLAG": ("bull flag", "buy"),
    r"BEAR(?:ISH)? ?FLAG": ("bear flag", "sell"),
    r"FLAG|PENNANT": ("flag / pennant", None),
    r"FALLING ?WEDGE": ("falling wedge", "buy"),
    r"RISING ?WEDGE": ("rising wedge", "sell"),
    r"CHANNEL": ("channel", None),
    r"BREAK ?OUT": ("breakout", "buy"),
    r"BREAK ?DOWN": ("breakdown", "sell"),
    r"DEMAND ?ZONE|BULLISH ?(?:OB|ORDER ?BLOCK)": ("demand zone / bullish order block", "buy"),
    r"SUPPLY ?ZONE|BEARISH ?(?:OB|ORDER ?BLOCK)": ("supply zone / bearish order block", "sell"),
    r"ORDER ?BLOCK|\bOB\b": ("order block", None),
    r"\bFVG\b|FAIR ?VALUE ?GAP|IMBALANCE": ("fair value gap", None),
    r"LIQUIDITY ?(?:SWEEP|GRAB)|STOP ?HUNT": ("liquidity sweep", None),
    r"\bBOS\b|BREAK OF STRUCTURE": ("break of structure", None),
    r"CHO?CH|CHANGE OF CHARACTER": ("change of character", None),
    r"TREND ?LINE": ("trendline", None),
    r"ROUNDING ?BOTTOM|SAUCER": ("rounding bottom", "buy"),
    r"SUPPORT": ("support", "buy"),
    r"RESISTANCE": ("resistance", "sell"),
}


CANDLE_NAMES = {"DOJI": "doji", "SPINNINGTOP": "spinning top", "HIGHWAVE": "high-wave", "LONGLEGGEDDOJI":
                "long-legged doji", "RICKSHAWMAN": "rickshaw man", "LONGLINE": "long candle", "SHORTLINE": "short candle",
                "MARUBOZU": "marubozu", "CLOSINGMARUBOZU": "closing marubozu", "ENGULFING": "engulfing",
                "HAMMER": "hammer", "INVERTEDHAMMER": "inverted hammer", "SHOOTINGSTAR": "shooting star",
                "HANGINGMAN": "hanging man", "HARAMI": "harami", "HARAMICROSS": "harami cross",
                "MORNINGSTAR": "morning star", "EVENINGSTAR": "evening star", "PIERCING": "piercing line",
                "DARKCLOUDCOVER": "dark cloud cover", "3WHITESOLDIERS": "three white soldiers",
                "3BLACKCROWS": "three black crows", "DRAGONFLYDOJI": "dragonfly doji",
                "GRAVESTONEDOJI": "gravestone doji", "BELTHOLD": "belt hold", "HIKKAKE": "hikkake",
                "XSIDEGAP3METHODS": "side-gap three methods", "TAKURI": "takuri", "KICKING": "kicking",
                "3INSIDE": "three inside", "3OUTSIDE": "three outside", "TASUKIGAP": "tasuki gap"}


def _ocr():
    global _OCR
    if _OCR is None:
        from rapidocr_onnxruntime import RapidOCR
        _OCR = RapidOCR()
    return _OCR


def _spaced(s):
    """'WeaknessOnlySustainingBelow24290' -> 'Weakness Only Sustaining Below 24290'."""
    s = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", s)
    s = re.sub(r"(?<=[A-Za-z])(?=\d)|(?<=\d)(?=[A-Za-z])", " ", s)
    return s


def _price_token(s):
    """OCR text of an axis label -> number, or None. Handles 24,800.00 / 24.800.00 / 25,200.0o."""
    s = s.strip().replace("o", "0").replace("O", "0").replace(" ", "")
    if not re.fullmatch(r"[\d.,]+", s) or not re.search(r"\d", s):
        return None
    m = re.fullmatch(r"(.*?)[.,](\d{1,2})", s)            # decimals (1-2 digits) at the end
    whole, dec = (m.group(1), m.group(2)) if m and len(m.group(1).replace(",", "").replace(".", "")) >= 2 else (s, "")
    groups = re.split(r"[.,]", whole)
    if len(groups) > 1 and not all(len(g) == 3 for g in groups[1:]):
        if len(groups) == 2 and len(groups[1]) <= 6 and not dec:     # plain decimal like 1.08520
            try:
                return float(whole.replace(",", ""))
            except ValueError:
                return None
        return None                                                     # garbled (e.g. 24,30.00)
    try:
        return float("".join(groups) + ("." + dec if dec else ""))
    except ValueError:
        return None


def fit_axis(tokens, width):
    """tokens: [(x, y_center, value)]. Robust fit value = a + b*y from right-edge numbers. Returns (a, b, n) or None."""
    pts = [(y, v) for x, y, v in tokens if v is not None and x > 0.8 * width]
    if len(pts) < 3:
        return None
    best = None
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            (y1, v1), (y2, v2) = pts[i], pts[j]
            if abs(y2 - y1) < 5:
                continue
            b = (v2 - v1) / (y2 - y1)
            if b >= 0:                       # prices must fall as we go down the picture
                continue
            a = v1 - b * y1
            tol = 0.004 * abs(np.median([v for _, v in pts]))
            inl = [(y, v) for y, v in pts if abs(a + b * y - v) <= tol]
            if best is None or len(inl) > len(best):
                best = inl
    if not best or len(best) < 3:
        return None
    Y, V = np.array([p[0] for p in best]), np.array([p[1] for p in best])
    b, a = np.polyfit(Y, V, 1)
    return float(a), float(b), len(best)


def horizontal_lines(img, min_frac=0.3):
    """y positions (centre) of long straight horizontal lines that stand out from the background."""
    a = np.asarray(img.convert("RGB")).astype(int)
    H, W, _ = a.shape
    bg = np.median(a.reshape(-1, 3), axis=0)
    diff = np.abs(a - bg).sum(axis=2) > 90
    ys = []
    for y in range(int(0.06 * H), int(0.92 * H)):
        row = diff[y, : int(0.9 * W)]
        if row.sum() < min_frac * W:
            continue
        runs = np.diff(np.flatnonzero(np.diff(np.r_[0, row.astype(int), 0])))[::2]   # lengths of True runs
        if len(runs) and runs.max() >= min_frac * W:
            ys.append(y)
    groups, cur = [], []
    for y in ys:
        if cur and y - cur[-1] > 2:
            groups.append(cur); cur = []
        cur.append(y)
    if cur:
        groups.append(cur)
    return [float(np.mean(g)) for g in groups]


EXCHANGES = r"OANDA|FXCM|FX_IDC|FX|NSE|BSE|TVC|FOREXCOM|FOREX\.COM|CAPITALCOM|PEPPERSTONE|BINANCE|COINBASE|BITSTAMP|" \
            r"SAXO|ICMARKETS|COMEX|NYMEX|MCX|BLACKBULL|EIGHTCAP|FUSIONMARKETS|VANTAGE|EXNESS|BYBIT|KRAKEN"


def header_info(text):
    """TradingView-style title line: 'Gold Spot / U.S. Dollar · 15 · OANDA  O4,050.13 H4,052.06 L4,044.88 C4,046.51'
    -> {'timeframe_min': 15, 'chart_price': 4046.51}. Missing parts are left out."""
    out = {}
    up = text.upper()
    m = re.search(r"(?:^|[\s·•.\-])(\d{1,3}|\d{1,2}[HDWM])\s*[·•.\-]?\s*(?:" + EXCHANGES + r")\b", up)
    if m:
        tf = m.group(1)
        mult = {"H": 60, "D": 1440, "W": 10080, "M": 43200}
        out["timeframe_min"] = int(tf[:-1]) * mult[tf[-1]] if tf[-1] in mult else int(tf)
    m = re.search(r"\bC\s*([\d,]+\.\d+)", up)
    if m and re.search(r"\bH\s*[\d,]+\.\d+", up) and re.search(r"\bL\s*[\d,]+\.\d+", up):
        try:
            out["chart_price"] = float(m.group(1).replace(",", ""))
        except ValueError:
            pass
    return out


def _longest_run(r, gap=25):
    """Longest stretch of True, bridging gaps up to `gap` px (candles drawn on top of a box)."""
    xs = np.flatnonzero(r)
    if not len(xs):
        return 0
    breaks = np.flatnonzero(np.diff(xs) > gap)
    starts = np.r_[xs[0], xs[breaks + 1]]
    ends = np.r_[xs[breaks], xs[-1]]
    return int((ends - starts).max()) + 1


def _zone_rows(mask, W, min_frac=0.12):
    rows = []
    for y in range(mask.shape[0]):
        r = mask[y]
        if r.sum() < 0.6 * min_frac * W:
            continue
        if _longest_run(r) >= min_frac * W:
            rows.append(y)
    groups, cur = [], []
    for y in rows:
        if cur and y - cur[-1] > 3:
            groups.append(cur); cur = []
        cur.append(y)
    if cur:
        groups.append(cur)
    return max(groups, key=len) if groups else None


def position_tool(img, axis):
    """TradingView long/short position tool: a green (target) box touching a red (stop) box.
    -> {'side', 'entry', 'stop', 'target'} as prices, or None."""
    if not axis:
        return None
    a, b, _ = axis
    A = np.asarray(img.convert("RGB")).astype(int)
    H, W, _ = A.shape
    top, bot = int(0.06 * H), int(0.92 * H)
    R, G, Bc = A[top:bot, : int(0.9 * W), 0], A[top:bot, : int(0.9 * W), 1], A[top:bot, : int(0.9 * W), 2]
    spread = np.maximum(np.maximum(R, G), Bc) - np.minimum(np.minimum(R, G), Bc)
    pale = (spread >= 12) & (spread <= 90)          # see-through boxes, not solid candles
    green = ((G - R) > 15) & ((G - Bc) > -25) & pale
    red = ((R - G) > 15) & ((R - Bc) > 8) & pale
    g, r = _zone_rows(green, W), _zone_rows(red, W)
    if not g or not r or len(g) < 8 or len(r) < 8:
        return None
    g0, g1, r0, r1 = g[0] + top, g[-1] + top, r[0] + top, r[-1] + top
    price = lambda y: a + b * y
    if 0 <= r0 - g1 <= 0.03 * H:          # green above red: long
        return {"side": "buy", "target": price(g0), "entry": price((g1 + r0) / 2), "stop": price(r1)}
    if 0 <= g0 - r1 <= 0.03 * H:          # red above green: short
        return {"side": "sell", "stop": price(r0), "entry": price((r1 + g0) / 2), "target": price(g1)}
    return None


def read_image(path):
    """-> {'text': all words read, 'levels': prices of drawn lines, 'patterns': [(name, side)], 'axis': bool}"""
    from PIL import Image
    img = Image.open(path)
    scale = 1.0
    if img.width < 1600:                     # small pictures read much better when enlarged
        scale = 1600 / img.width
        img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
    res, _ = _ocr()(np.asarray(img.convert("RGB")))
    res = res or []
    words, tokens = [], []
    for box, txt, conf in res:
        xs, ys = [p[0] for p in box], [p[1] for p in box]
        tokens.append((min(xs), (min(ys) + max(ys)) / 2, _price_token(txt)))
        if float(conf) >= 0.5:
            words.append(_spaced(txt))
    text = " ".join(words)
    axis = fit_axis(tokens, img.width)
    levels, rng = [], None
    if axis:
        a, b, _ = axis
        rng = sorted((a + b * 0.06 * img.height, a + b * 0.92 * img.height))
        for y in horizontal_lines(img):
            p = a + b * y
            if p > 0:
                levels.append(round(p, 5 if abs(p) < 10 else 2))
    up = text.upper()
    pats = []
    for pat, (name, side) in PATTERN_WORDS.items():
        if re.search(pat, up) and name not in [p[0] for p in pats]:
            if name in ("head and shoulders",) and "inverse head and shoulders" in [p[0] for p in pats]:
                continue
            pats.append((name, side))
    out = {"text": text, "levels": sorted(set(levels)), "patterns": pats, "axis": bool(axis), "range": rng}
    out.update(header_info(text))
    try:
        pos = position_tool(img, axis)
        if pos:
            out["position"] = {k: (round(v, 5 if abs(v) < 10 else 2) if isinstance(v, float) else v) for k, v in pos.items()}
    except Exception as e:
        log.warning("position tool reading failed: %s", type(e).__name__)
    return out


def guess_instrument(rng, prices=None):
    """No name readable on the picture: which index / commodity / crypto / major pair trades inside the price
    scale shown? Returns its message name (e.g. 'Nifty') only if exactly one fits, else None."""
    if not rng:
        return None
    if prices is None:
        import yfinance as yf
        names = {"^NSEI": "Nifty", "^NSEBANK": "Bank Nifty", "^BSESN": "Sensex", "NIFTY_FIN_SERVICE.NS": "Fin Nifty",
                 "GC=F": "XAUUSD", "SI=F": "XAGUSD", "CL=F": "crude", "BTC-USD": "BTCUSD", "ETH-USD": "ETHUSD",
                 "EURUSD=X": "EURUSD", "GBPUSD=X": "GBPUSD", "USDJPY=X": "USDJPY", "USDINR=X": "USDINR",
                 "AUDUSD=X": "AUDUSD", "USDCAD=X": "USDCAD", "USDCHF=X": "USDCHF", "GBPJPY=X": "GBPJPY"}
        prices = {}
        try:
            df = yf.download(list(names), period="5d", interval="1d", progress=False, auto_adjust=False)["Close"]
            for tk, nm in names.items():
                if tk in df and df[tk].notna().any():
                    prices[nm] = float(df[tk].dropna().iloc[-1])
        except Exception:
            return None
    lo, hi = rng
    fits = [nm for nm, px in prices.items() if lo <= px <= hi]
    return fits[0] if len(fits) == 1 else None


# ----------------------------------------------------------------------------- the system's own read
def own_patterns(df, lookback=3):
    """Run the system's pattern library (chart patterns, market structure, candles) on one instrument's daily
    bars; return names of the BULLISH entry patterns that fired in the last `lookback` bars, and candle patterns
    (bullish and bearish) on the last bar."""
    import pandas as pd
    from . import catalog
    from .config import load_strategy
    from .families import base_indicators
    if df is None or len(df) < 260:
        return [], []
    sym = "X"
    P = {k: df[[k]].rename(columns={k: sym}).astype(float) for k in ("open", "high", "low", "close")}
    P["volume"] = (df[["volume"]].rename(columns={"volume": sym}).astype(float) if "volume" in df
                   else pd.DataFrame(0.0, index=df.index, columns=[sym]))
    if float(P["volume"][sym].sum()) == 0:
        P["volume"][:] = 1.0                 # indices / forex have no volume: neutral constant
    P["raw_close"] = P["close"]
    member = pd.DataFrame(True, index=df.index, columns=[sym])
    p = load_strategy("v1")
    try:
        B = base_indicators(P, P["close"][sym], member, {}, p)
    except Exception as e:
        log.warning("own pattern check: indicators failed: %s %s", type(e).__name__, e)
        return None, None
    fired = []
    for pid in catalog.CHART_DETECTORS:
        try:
            s = catalog.chart_signal(pid, B, p)
            if s is not None and bool(s.iloc[-lookback:][sym].any()):
                fired.append(pid.replace("_", " "))
        except Exception:
            continue
    for mid in catalog.MS_DETECTORS:
        try:
            s = catalog.ms_signal(mid, B, p)
            if s is not None and bool(s.iloc[-lookback:][sym].any()):
                fired.append(mid.replace("_", " "))
        except Exception:
            continue
    candles = []
    try:
        import talib
        o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
        neutral = {"DOJI", "SPINNINGTOP", "HIGHWAVE", "LONGLEGGEDDOJI", "RICKSHAWMAN", "LONGLINE", "SHORTLINE",
                   "MARUBOZU", "CLOSINGMARUBOZU", "HIKKAKE", "HIKKAKEMOD"}
        for fn in talib.get_function_groups()["Pattern Recognition"]:
            v = getattr(talib, fn)(o, h, l, c)[-1]
            if v:
                name = CANDLE_NAMES.get(fn[3:], fn[3:].lower())
                candles.append(name if fn[3:] in neutral and fn[3:] not in ("MARUBOZU", "CLOSINGMARUBOZU")
                               else ("bullish " if v > 0 else "bearish ") + name)
    except Exception:
        pass
    return fired, candles[:6]


def own_patterns_for(ticker_or_symbol, nse_stock=False):
    """(fired, candles) from the system's own detectors on real daily prices, or None if no data."""
    try:
        import yfinance as yf
        tk = f"{ticker_or_symbol}.NS" if nse_stock else ticker_or_symbol
        df = yf.download(tk, period="3y", interval="1d", progress=False, auto_adjust=False)
        if df is None or not len(df):
            return None
        if hasattr(df.columns, "levels"):
            df.columns = df.columns.get_level_values(0)
        df = df.rename(columns=str.lower).dropna(subset=["close"])
        fired, candles = own_patterns(df)
        return None if fired is None else (fired, candles)
    except Exception as e:
        log.warning("own patterns failed: %s", type(e).__name__)
        return None


def own_patterns_line(ticker_or_symbol, nse_stock=False):
    """One reply line with the system's own pattern check on daily bars."""
    try:
        import yfinance as yf
        tk = f"{ticker_or_symbol}.NS" if nse_stock else ticker_or_symbol
        df = yf.download(tk, period="3y", interval="1d", progress=False, auto_adjust=False)
        if df is None or not len(df):
            return None
        if hasattr(df.columns, "levels"):
            df.columns = df.columns.get_level_values(0)
        df = df.rename(columns=str.lower).dropna(subset=["close"])
        fired, candles = own_patterns(df)
        if fired is None:
            return None
    except Exception as e:
        log.warning("own pattern line failed: %s", type(e).__name__)
        return None
    parts = []
    if fired:
        parts.append("bullish setups firing (last 3 days): " + ", ".join(fired[:6]))
    if candles:
        parts.append("today's candle: " + ", ".join(candles[:4]))
    return ("System's own pattern check (daily): " + ("; ".join(parts) if parts else
            "none of the library's entry patterns fired in the last 3 days") +
            ". (Single patterns are clues, not tested edges - only the system's own strategy passed its tests.)")


def apply_image(v, info, price):
    """Use what the picture showed when the text alone did not give it: pattern direction, and the nearest drawn
    line on the other side of the price as the 'wrong if' level. Returns notes for the reply."""
    notes = []
    if info.get("patterns"):
        notes.append("Read on the chart: " + ", ".join(n for n, _ in info["patterns"][:5]) + ".")
        sides = {s for _, s in info["patterns"] if s}
        if v.get("side") in (None, "trend") and len(sides) == 1:
            v["side"] = sides.pop()
    lv = [x for x in info.get("levels", []) if price and abs(x / price - 1) < 0.15]
    if lv:
        notes.append("Lines drawn on the chart at about " + ", ".join(f"{x:,.2f}" if x < 1000 else f"{x:,.0f}"
                                                                       for x in lv[:6]) + " (read from the picture).")
        if not v.get("stop") and not v.get("wrong_if") and v.get("side") in ("buy", "sell"):
            below = [x for x in lv if x < price]
            above = [x for x in lv if x > price]
            if v["side"] == "buy" and below:
                v["wrong_if"] = ("below", max(below))
                notes.append(f"No stop was written, so I used the nearest drawn line below the price ({max(below):,.2f}) "
                             "as the 'wrong if' level.")
            elif v["side"] == "sell" and above:
                v["wrong_if"] = ("above", min(above))
                notes.append(f"No stop was written, so I used the nearest drawn line above the price ({min(above):,.2f}) "
                             "as the 'wrong if' level.")
    return notes
