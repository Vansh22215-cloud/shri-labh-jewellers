"""F&O END-OF-DAY intelligence from the official NSE F&O bhavcopy (ROADMAP I2).

Per stock / index and day (near-month contracts):
  * futures close, open interest (OI) and OI change -> build-up classification:
      price up + OI up = LONG BUILD-UP (fresh buying)      price down + OI up = SHORT BUILD-UP (fresh selling)
      price up + OI down = SHORT COVERING                  price down + OI down = LONG UNWINDING
  * options: total call OI and put OI (near expiry), put-call ratio (PCR), max-pain strike, the strikes with
    the most call OI (resistance) and put OI (support), and the ACTUAL expiry date.
UDiFF format files are available from 2024-07-08. Cached in data/fno/YYYYMMDD.csv (compact summary).
"""
import io
import time
import zipfile

import numpy as np
import pandas as pd

from .config import DATA, get_logger
from .data_nse import _get

log = get_logger()
DIR = DATA / "fno"
DIR.mkdir(parents=True, exist_ok=True)


def summarise(df):
    df = df.copy()
    df["XpryDt"] = pd.to_datetime(df["XpryDt"])
    out = []
    for sym, g in df.groupby("TckrSymb"):
        fut = g[g["FinInstrmTp"].isin(["STF", "IDF"])].sort_values("XpryDt")
        opt = g[g["FinInstrmTp"].isin(["STO", "IDO"])]
        if fut.empty and opt.empty:
            continue
        r = {"symbol": sym}
        if not fut.empty:
            f0 = fut.iloc[0]
            r.update({"fut_close": f0["ClsPric"], "fut_prev": f0["PrvsClsgPric"], "fut_oi": fut["OpnIntrst"].sum(),
                      "fut_oi_chg": fut["ChngInOpnIntrst"].sum(), "spot": f0["UndrlygPric"],
                      "fut_expiry": str(f0["XpryDt"].date())})
        if not opt.empty:
            near = opt[opt["XpryDt"] == opt["XpryDt"].min()]
            ce, pe = near[near["OptnTp"] == "CE"], near[near["OptnTp"] == "PE"]
            r.update({"opt_expiry": str(near["XpryDt"].min().date()), "call_oi": ce["OpnIntrst"].sum(),
                      "put_oi": pe["OpnIntrst"].sum()})
            r["pcr"] = r["put_oi"] / r["call_oi"] if r["call_oi"] else np.nan
            if len(ce):
                r["max_call_oi_strike"] = float(ce.loc[ce["OpnIntrst"].idxmax(), "StrkPric"])
            if len(pe):
                r["max_put_oi_strike"] = float(pe.loc[pe["OpnIntrst"].idxmax(), "StrkPric"])
            strikes = np.sort(near["StrkPric"].unique())
            if len(strikes):
                cs = ce.set_index("StrkPric")["OpnIntrst"].groupby(level=0).sum()
                ps = pe.set_index("StrkPric")["OpnIntrst"].groupby(level=0).sum()
                pain = [((np.maximum(0, k - cs.index.values) * cs.values).sum() +
                         (np.maximum(0, ps.index.values - k) * ps.values).sum()) for k in strikes]
                r["max_pain"] = float(strikes[int(np.argmin(pain))])
        out.append(r)
    return pd.DataFrame(out)


def fetch(d):
    d = pd.Timestamp(d)
    f = DIR / f"{d:%Y%m%d}.csv"
    if f.exists():
        return f.stat().st_size > 0
    raw = _get(f"/content/fo/BhavCopy_NSE_FO_0_0_0_{d:%Y%m%d}_F_0000.csv.zip")
    if raw is None:
        if (pd.Timestamp.today() - d).days > 3:
            f.write_text("")
        return False
    z = zipfile.ZipFile(io.BytesIO(raw))
    summarise(pd.read_csv(z.open(z.namelist()[0]))).to_csv(f, index=False)
    time.sleep(0.3)
    return True


def download(dates):
    for d in dates:
        if pd.Timestamp(d) >= pd.Timestamp("2024-07-08"):
            fetch(d)


def latest(n=2):
    files = [f for f in sorted(DIR.glob("*.csv")) if f.stat().st_size > 0][-n:]
    return [(pd.Timestamp(f.stem), pd.read_csv(f).set_index("symbol")) for f in files]


def buildup(sym):
    """Today's build-up classification and options levels for one F&O stock (None if not in F&O)."""
    days = latest(1)
    if not days:
        return None
    d, t = days[-1]
    if sym not in t.index:
        return None
    r = t.loc[sym]
    out = {"date": str(d.date())}
    if pd.notna(r.get("fut_close")) and pd.notna(r.get("fut_prev")) and pd.notna(r.get("fut_oi_chg")):
        up, oi_up = r["fut_close"] > r["fut_prev"], r["fut_oi_chg"] > 0
        out["buildup"] = ("LONG BUILD-UP" if up and oi_up else "SHORT BUILD-UP" if (not up) and oi_up
                          else "SHORT COVERING" if up else "LONG UNWINDING")
        out["fut_oi_chg_pct"] = round(r["fut_oi_chg"] / max(1, r["fut_oi"] - r["fut_oi_chg"]) * 100, 1)
    for k in ("pcr", "max_pain", "max_call_oi_strike", "max_put_oi_strike", "opt_expiry"):
        if k in r and pd.notna(r[k]):
            out[k] = round(r[k], 2) if isinstance(r[k], float) else r[k]
    return out


def expiry_for(sym):
    b = buildup(sym)
    return pd.Timestamp(b["opt_expiry"]).date() if b and b.get("opt_expiry") else None


def line(sym):
    b = buildup(sym)
    if not b:
        return ""
    parts = []
    if b.get("buildup"):
        parts.append(f"{b['buildup']} (futures OI {b.get('fut_oi_chg_pct', 0):+.1f}%)")
    if b.get("pcr") is not None:
        parts.append(f"PCR {b['pcr']:.2f}")
    if b.get("max_put_oi_strike"):
        parts.append(f"support (put OI) {b['max_put_oi_strike']:g}")
    if b.get("max_call_oi_strike"):
        parts.append(f"resistance (call OI) {b['max_call_oi_strike']:g}")
    return "F&O: " + ", ".join(parts)
