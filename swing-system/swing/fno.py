"""NIFTY weekly options from Kite's NFO instrument list (read-only): the nearest weekly expiry, the at-the-money
strike, the contract's Kite symbol, lot size, and the name shown on the dashboard ("NIFTY 24 NOV 26200 CALL")."""
import io
from datetime import datetime, time as dtime

import pandas as pd

from .config import DATA, get_logger

log = get_logger()
NFO_F = DATA / "kite_instruments_nfo.csv"
STEP = 50


def nfo():
    """NIFTY option contracts (refreshed once a day)."""
    from . import kite
    if NFO_F.exists() and (datetime.now().timestamp() - NFO_F.stat().st_mtime) < 20 * 3600:
        return pd.read_csv(NFO_F, parse_dates=["expiry"])
    r = kite._get("/instruments/NFO", timeout=90)
    df = pd.read_csv(io.StringIO(r.text))
    df = df[(df["name"] == "NIFTY") & (df["segment"] == "NFO-OPT")][
        ["instrument_token", "tradingsymbol", "expiry", "strike", "instrument_type", "lot_size"]]
    df["expiry"] = pd.to_datetime(df["expiry"])
    df.to_csv(NFO_F, index=False)
    return df


def display_name(row):
    return f"NIFTY {pd.Timestamp(row['expiry']):%d %b}".upper() + \
        f" {int(row['strike'])} {'CALL' if row['instrument_type'] == 'CE' else 'PUT'}"


def pick(spot, side, when, table=None):
    """At-the-money contract of the nearest weekly expiry. side: 'CE' or 'PE'. On expiry day after 1:30 pm the
    next expiry is used (the expiring contract loses its value too fast). -> dict or None."""
    T = table if table is not None else nfo()
    when = pd.Timestamp(when)
    exps = sorted(e for e in T["expiry"].unique() if pd.Timestamp(e).normalize() >= when.normalize())
    if not exps:
        return None
    exp = pd.Timestamp(exps[0])
    if exp.normalize() == when.normalize() and when.time() >= dtime(13, 30) and len(exps) > 1:
        exp = pd.Timestamp(exps[1])
    strike = int(round(spot / STEP) * STEP)
    rows = T[(T["expiry"] == exp) & (T["instrument_type"] == side)]
    if not len(rows):
        return None
    r = rows.iloc[(rows["strike"] - strike).abs().argsort().iloc[0]]
    return {"symbol": f"NFO:{r['tradingsymbol']}", "token": int(r["instrument_token"]), "lot": int(r["lot_size"]),
            "expiry": str(pd.Timestamp(r["expiry"]).date()), "strike": int(r["strike"]), "side": side,
            "name": display_name(r)}
