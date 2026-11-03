"""FII / DII / Pro / Client positioning in index & stock derivatives (NSE participant-wise open interest).

Daily official NSE file (public archive). Key feature: FII index-futures LONG share =
long / (long + short) contracts. FIIs are the largest informed players in Indian index futures; a low long share
means they are heavily hedged / bearish. Known after the close (published the same evening) -> usable for
next-day decisions without look-ahead. ROADMAP I1.
"""
import io
import time
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from .config import DATA, get_logger
from .data_nse import _get

log = get_logger()
DIR = DATA / "participant_oi"
DIR.mkdir(parents=True, exist_ok=True)
PANEL = DATA / "participant_oi.csv"


def fetch(d):
    d = pd.Timestamp(d)
    f = DIR / f"{d:%Y%m%d}.csv"
    if f.exists():
        return
    raw = _get(f"/content/nsccl/fao_participant_oi_{d:%d%m%Y}.csv")
    if raw is None:
        if (pd.Timestamp.today() - d).days > 3:
            f.write_text("")
        return
    try:
        df = pd.read_csv(io.BytesIO(raw), skiprows=1)
        df.columns = [c.strip() for c in df.columns]
        df = df[df["Client Type"].astype(str).str.strip().isin(["Client", "DII", "FII", "Pro"])]
        df.to_csv(f, index=False)
    except Exception as e:
        log.warning("participant OI parse failed %s: %s", d.date(), e)
    time.sleep(0.3)


def download(dates, workers=2):
    todo = [d for d in dates if not (DIR / f"{pd.Timestamp(d):%Y%m%d}.csv").exists()]
    with ThreadPoolExecutor(workers) as ex:
        list(ex.map(fetch, todo))


def build_panel():
    rows = []
    for f in sorted(DIR.glob("*.csv")):
        if f.stat().st_size == 0:
            continue
        df = pd.read_csv(f)
        df.columns = [c.strip() for c in df.columns]
        g = df.set_index(df["Client Type"].str.strip())
        num = lambda who, col: float(str(g.at[who, col]).replace(",", ""))
        r = {"date": pd.Timestamp(f.stem)}
        for who in ("FII", "DII", "Pro", "Client"):
            il, ish = num(who, "Future Index Long"), num(who, "Future Index Short")
            r[f"{who.lower()}_idx_fut_long_pct"] = il / (il + ish) * 100 if il + ish else None
            r[f"{who.lower()}_idx_fut_net"] = il - ish
        r["fii_put_call_long"] = num("FII", "Option Index Put Long") / max(1.0, num("FII", "Option Index Call Long"))
        rows.append(r)
    p = pd.DataFrame(rows).set_index("date").sort_index()
    p.to_csv(PANEL)
    log.info("Participant positioning panel: %d days", len(p))
    return p


def load_panel():
    return pd.read_csv(PANEL, index_col=0, parse_dates=True) if PANEL.exists() else None


def today_line():
    p = load_panel()
    if p is None or p.empty:
        return ""
    last = p.iloc[-1]
    chg = last["fii_idx_fut_long_pct"] - p["fii_idx_fut_long_pct"].iloc[-6] if len(p) > 6 else 0
    pct = (p["fii_idx_fut_long_pct"].tail(750) < last["fii_idx_fut_long_pct"]).mean() * 100
    mood = "very bearish" if last["fii_idx_fut_long_pct"] < 25 else "bearish" if last["fii_idx_fut_long_pct"] < 40 \
        else "neutral" if last["fii_idx_fut_long_pct"] < 60 else "bullish"
    return (f"FII index futures: {last['fii_idx_fut_long_pct']:.0f}% long ({mood}; {chg:+.0f} pts in a week; "
            f"higher than {pct:.0f}% of the last 3 years). DII {last['dii_idx_fut_long_pct']:.0f}% long, "
            f"retail (Client) {last['client_idx_fut_long_pct']:.0f}% long.")
