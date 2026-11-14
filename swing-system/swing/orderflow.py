"""ORDER FLOW (D103) - the 'Market Pulse' ideas, built from the owner's own Kite data.

  * pressure(q)       - live buy vs sell pressure of one stock from Kite's full quote: total pending buy quantity vs
                        sell quantity (and the top-5 bid/ask book) -> -1 (all sellers) .. +1 (all buyers)
  * pulse(quotes)     - market mood: advancing vs declining stocks, VIX, risk-on / risk-off, and SECTOR money flow
                        (traded value of rising minus falling stocks, per sector)
  * order blocks      - the last down candle before a strong up move that breaks the recent high = a 'demand zone';
                        the first return of price into the zone is the classic order-block 'call'
  * cmf(d)            - Chaikin money flow: buy/sell pressure estimated from daily bars (where the close sits in the
                        day's range x volume) - the only kind of 'pressure' that has 13 years of history to test

What is USED in tips is decided only by tests (validation/orderflow_research.py, DECISIONS D103). Live bid/ask
pressure has no history anywhere, so it is recorded every 30 minutes (shadow) and judged on its own live record
(evaluate()) before it may count.
"""
import numpy as np
import pandas as pd

from .config import DATA, get_logger

log = get_logger()
SHADOW_F = DATA / "orderflow_shadow.csv"


# ---- history-based (testable) ------------------------------------------------------------------------------------
def cmf(d, n=20):
    rng = (d["high"] - d["low"]).replace(0, np.nan)
    mfm = ((d["close"] - d["low"]) - (d["high"] - d["close"])) / rng
    mfv = mfm.fillna(0) * d["volume"]
    return mfv.rolling(n).sum() / d["volume"].rolling(n).sum().replace(0, np.nan)


def _atr(d, n=14):
    tr = pd.concat([d["high"] - d["low"], (d["high"] - d["close"].shift()).abs(),
                    (d["low"] - d["close"].shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean().values


def find_order_blocks(d, impulse_atr=1.5, swing=10):
    """[(i, zone_low, zone_high)] - bullish order blocks: a down candle i followed within 3 days by a close at least
    impulse_atr x ATR above its high that also breaks the previous `swing`-day high. Known only after day i+3."""
    o, h, l, c = (d[k].values for k in ("open", "high", "low", "close"))
    atr = _atr(d)
    out = []
    for i in range(swing, len(d) - 3):
        if not c[i] < o[i] or not np.isfinite(atr[i]):
            continue
        best = c[i + 1:i + 4].max()
        if best - h[i] >= impulse_atr * atr[i] and best > h[i - swing:i].max():
            out.append((i, float(l[i]), float(h[i])))
    return out


def order_block_touches(d, look=60, **kw):
    """Per day: (touch bool array, zone_low array, zone_high array). A touch = the FIRST day price comes back into a
    fresh zone (low <= zone top) and still closes above the zone bottom. Zones expire after `look` days or when a
    close breaks below them."""
    n = len(d)
    touch, zl, zh = np.zeros(n, bool), np.full(n, np.nan), np.full(n, np.nan)
    l, c = d["low"].values, d["close"].values
    for i, lo, hi in find_order_blocks(d, **kw):
        for t in range(i + 4, min(n, i + 4 + look)):
            if l[t] <= hi:
                if c[t] >= lo and not (touch[t] and zl[t] >= lo):
                    touch[t], zl[t], zh[t] = True, lo, hi
                break
    return touch, zl, zh


def active_zones(d, look=60, **kw):
    """Fresh (untouched, unbroken) demand zones right now -> [(zone_low, zone_high, age_days)]."""
    l = d["low"].values
    out = []
    for i, lo, hi in find_order_blocks(d, **kw):
        if len(d) - i > look + 4:
            continue
        touched = bool((l[i + 4:] <= hi).any()) if i + 4 < len(d) else False
        if not touched:
            out.append((round(lo, 2), round(hi, 2), len(d) - 1 - i))
    return out


# ---- live (Kite) -------------------------------------------------------------------------------------------------
def pressure(q):
    """Kite full quote dict -> imbalance -1..+1 (None without order-book data). Uses the whole pending book and the
    top-5 levels equally."""
    b, s = q.get("buy_qty") or 0, q.get("sell_qty") or 0
    b5, a5 = q.get("bid5") or 0, q.get("ask5") or 0
    parts = [(x - y) / (x + y) for x, y in ((b, s), (b5, a5)) if x + y > 0]
    return round(float(np.mean(parts)), 3) if parts else None


def label(p):
    if p is None:
        return "no order-book data"
    return ("strong buying" if p > 0.4 else "buyers ahead" if p > 0.15 else "strong selling" if p < -0.4 else
            "sellers ahead" if p < -0.15 else "balanced")


def sectors(symbols):
    import json
    out = {}
    for s in symbols:
        try:
            out[s] = json.load(open(DATA / "fundamentals" / f"{s}.json")).get("sector") or "Other"
        except Exception:
            out[s] = "Other"
    return out


def pulse(quotes, vix=None, sector_map=None):
    """quotes {sym: kite quote} -> dict: advancers, decliners, mood, sectors [(name, flow_cr, avg_pressure, n)]."""
    rows = []
    for s, q in quotes.items():
        if not q.get("prev"):
            continue
        rows.append({"sym": s, "chg": q["last"] / q["prev"] - 1, "val": q.get("value_cr") or 0.0,
                     "p": pressure(q)})
    if not rows:
        return None
    df = pd.DataFrame(rows)
    sm = sector_map or sectors(df["sym"])
    df["sector"] = df["sym"].map(sm).fillna("Other")
    adv, dec = int((df.chg > 0).sum()), int((df.chg < 0).sum())
    df["flow"] = np.sign(df.chg) * df.val
    sec = (df.groupby("sector").agg(flow=("flow", "sum"), p=("p", "mean"), n=("sym", "size"))
           .sort_values("flow", ascending=False))
    ratio = adv / max(1, adv + dec)
    mood = "RISK-ON" if ratio > 0.6 and (vix is None or vix < 18) else \
        "RISK-OFF" if ratio < 0.4 or (vix is not None and vix > 22) else "MIXED"
    return {"adv": adv, "dec": dec, "ratio": round(ratio, 2), "vix": vix, "mood": mood,
            "sectors": [(k, round(r.flow, 1), None if pd.isna(r.p) else round(r.p, 2), int(r.n))
                        for k, r in sec.iterrows() if k != "Other"]}


def record(quotes, now=None):
    """Shadow record (every 30 min while the market is open): price + order-book pressure of each stock. Market data
    only (nothing personal). evaluate() later checks whether pressure predicted the next move."""
    now = now or pd.Timestamp.now(tz="Asia/Kolkata").tz_localize(None)
    rows = [{"time": str(now)[:16], "symbol": s, "last": q["last"], "p": pressure(q)}
            for s, q in quotes.items() if pressure(q) is not None and (q.get("value_cr") or 0) >= 10]   # liquid only
    if not rows:
        return 0
    df = pd.DataFrame(rows)
    df.to_csv(SHADOW_F, mode="a", header=not SHADOW_F.exists(), index=False)
    try:   # keep the file small: last ~60 trading days
        if SHADOW_F.stat().st_size > 25e6:
            old = pd.read_csv(SHADOW_F)
            old[old["time"] >= sorted(old["time"].str[:10].unique())[-60]].to_csv(SHADOW_F, index=False)
    except Exception:
        pass
    return len(df)


def evaluate(min_rows=3000):
    """Did live order-book pressure predict the move to the NEXT snapshot (~30 min) and to the next day's last
    snapshot? -> dict per pressure bucket, or None until enough data."""
    if not SHADOW_F.exists():
        return None
    df = pd.read_csv(SHADOW_F)
    if len(df) < min_rows:
        return {"rows": len(df), "ready": False}
    df["time"] = pd.to_datetime(df["time"])
    df = df.sort_values(["symbol", "time"])
    df["next"] = df.groupby("symbol")["last"].shift(-1)
    df["same_day"] = df.groupby("symbol")["time"].shift(-1).dt.date == df["time"].dt.date
    df = df[df["same_day"] & df["next"].notna()]
    df["ret"] = df["next"] / df["last"] - 1
    df["bucket"] = pd.cut(df["p"], [-1.01, -0.4, -0.15, 0.15, 0.4, 1.01],
                          labels=["strong selling", "sellers ahead", "balanced", "buyers ahead", "strong buying"])
    g = df.groupby("bucket", observed=True)["ret"].agg(["size", "mean", lambda r: (r > 0).mean()])
    g.columns = ["n", "avg", "up_share"]
    edge = (g.loc["strong buying", "up_share"] - g.loc["strong selling", "up_share"]) \
        if {"strong buying", "strong selling"} <= set(g.index) else None
    return {"rows": len(df), "ready": True, "table": g.round(4).reset_index().to_dict("records"),
            "edge_up_share": None if edge is None else round(float(edge), 3)}
