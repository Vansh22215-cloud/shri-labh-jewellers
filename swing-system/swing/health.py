"""Data-quality checks and quarantine.

Suspicious data is QUARANTINED (excluded) rather than used. Reasons are saved to
data/quarantine.json and summarised in the daily report.
"""
import json

import numpy as np
import pandas as pd

from . import data_prices
from .config import BHAV, QUARANTINE, get_logger

log = get_logger()


def raw_unadjusted_close(df):
    """Undo Yahoo's split/bonus adjustment to get the price that actually traded that day."""
    s = df["splits"].replace(0, np.nan).fillna(1.0)
    # factor for day d = product of split ratios on dates AFTER d
    after = s[::-1].cumprod()[::-1].shift(-1).fillna(1.0)
    return df["close"] * after


def load_bhav_closes(dates=None):
    frames = []
    for f in sorted(BHAV.glob("*.csv")):
        if f.stat().st_size == 0:
            continue
        if dates is not None and f.stem not in dates:
            continue
        x = pd.read_csv(f, usecols=["symbol", "series", "close", "date"], parse_dates=["date"])
        frames.append(x[x["series"] == "EQ"])
    if not frames:
        return pd.DataFrame(columns=["symbol", "close", "date"])
    return pd.concat(frames)


def check_symbol(sym, df, bhav_by_sym):
    """Return a list of problems for one symbol's price history (empty list = clean)."""
    probs = []
    if df is None or len(df) < 50:
        return ["too little price history"]
    if df.index.duplicated().any():
        probs.append("duplicate dates")
    if (df[["open", "high", "low", "close"]] <= 0).any().any():
        probs.append("zero/negative prices")
    if ((df["high"] + 1e-6) < df["low"]).any():
        probs.append("high below low")
    r = df["adj_close"].pct_change()
    if ((r > 0.8) | (r < -0.45)).any():
        bad = df.index[(r > 0.8) | (r < -0.45)][0].date()
        probs.append(f"price jump >45% on {bad} (likely unadjusted split/bonus/demerger)")
    b = bhav_by_sym.get(sym)
    if b is not None and len(b) >= 5:
        # Yahoo back-adjusts old prices for splits, bonuses AND demergers (not always recorded),
        # so the ratio Yahoo/NSE is legitimately a step function: constant, with a few steps at
        # corporate actions. Bad data shows up as a ratio that keeps jumping around.
        k = (raw_unadjusted_close(df).reindex(b.index) / b).dropna()
        if len(k) >= 5:
            steps = (k / k.shift(1) - 1).abs().dropna()
            n_steps = int((steps > 0.02).sum())
            if n_steps > 6 or (n_steps > 2 and n_steps / len(steps) > 0.05):
                probs.append(f"Yahoo vs NSE official prices disagree erratically ({n_steps} unexplained jumps)")
            recent = (k.sort_index().tail(3) - 1).abs()
            if len(recent) and (recent > 0.01).any():
                probs.append("latest Yahoo close differs from NSE official close by >1%")
    return probs


def build_quarantine(symbols):
    bh = load_bhav_closes()
    bhav_by_sym = {s: g.set_index("date")["close"] for s, g in bh.groupby("symbol")}
    q = {}
    for s in symbols:
        probs = check_symbol(s, data_prices.load(s), bhav_by_sym)
        if probs:
            q[s] = probs
    QUARANTINE.write_text(json.dumps(q, indent=1))
    log.info("Quarantine: %d of %d symbols excluded", len(q), len(symbols))
    return q


def load_quarantine():
    try:
        return json.loads(QUARANTINE.read_text())
    except Exception:
        return {}


def freshness(last_date, expected_date):
    """Data is fresh if the latest bar is the latest NSE trading day."""
    return pd.Timestamp(last_date).normalize() >= pd.Timestamp(expected_date).normalize()


def sanity_check_plans(plans, capital):
    """Reject impossible outputs. Returns list of problems (empty = OK)."""
    probs = []
    for pl in plans:
        s = pl["symbol"]
        if not (pl["stop"] < pl["entry_low"] <= pl["entry_high"] < pl["target1"] < pl["target2"]):
            probs.append(f"{s}: levels out of order (stop/entry/targets)")
        if pl["stop"] <= 0 or pl["entry_high"] <= 0:
            probs.append(f"{s}: non-positive price")
        if pl["qty"] < 1:
            probs.append(f"{s}: quantity below 1")
        if pl["qty"] * pl["entry_high"] > capital * 0.26:
            probs.append(f"{s}: position above 25% cap")
        if pl["risk_rupees"] > capital * 0.0105:
            probs.append(f"{s}: risk above 1% of capital")
        if pl["entry_high"] > 1.5 * pl["last_close"] or pl["entry_low"] < 0.5 * pl["last_close"]:
            probs.append(f"{s}: entry zone far from last price")
    return probs
