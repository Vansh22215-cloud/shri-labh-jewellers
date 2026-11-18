"""Silent forward record (owner 18 Nov: 'Yes'): the promoter-buying trade from round 9 (#4, a near miss: +0.8% per
trade in both test periods, bar +1.0%). Nothing is sent to Telegram and no tip changes. Every weekday evening:
  1. new promoter market purchases >= Rs 10 lakh disclosed on NSE are recorded (one per stock per day);
  2. each recorded event gets its would-be trade once prices exist: buy at the open of the first trading day after
     the disclosure, sell at the open 5 trading days later, 0.35% costs, only stocks trading >= Rs 2 cr/day.
data/private/shadow_promoter.csv. vantage-ai/validation/IMPROVE9_RESULTS.md has the test."""
import pandas as pd

from .config import PRIVATE, get_logger

log = get_logger()
FILE = PRIVATE / "shadow_promoter.csv"
COLS = ["symbol", "day", "value_cr", "recorded", "entry_date", "entry", "exit_date", "exit", "net_pct", "status"]
HOLD, COST = 5, 0.0035


def _load():
    try:
        return pd.read_csv(FILE, dtype=str)
    except Exception:
        return pd.DataFrame(columns=COLS)


def _save(t):
    FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = FILE.with_suffix(".tmp")
    t.to_csv(tmp, index=False)
    tmp.replace(FILE)


def promoter_events(rows):
    """rows from nse_filings.insider() -> [(symbol, day, value_cr)] for promoter market purchases >= Rs 10 lakh."""
    out = {}
    for r in rows:
        role, mode, act = str(r.get("role") or ""), str(r.get("mode") or ""), str(r.get("action") or "")
        try:
            val = float(r.get("value_cr") or 0)
        except (TypeError, ValueError):
            val = 0.0
        if role in ("Promoters", "Promoter Group") and mode == "Market Purchase" and act == "Buy" and val >= 0.1:
            day = pd.to_datetime(str(r.get("date")), errors="coerce", dayfirst=True)
            if pd.notna(day) and r.get("symbol"):
                k = (str(r["symbol"]), str(day.date()))
                out[k] = out.get(k, 0.0) + val                # one event per stock per day (values added up)
    return sorted((s, d, round(v, 2)) for (s, d), v in out.items())


def record(rows=None, today=None):
    """Add new events (no messages). -> number added."""
    if rows is None:
        from . import nse_filings
        rows = nse_filings.insider(days=7)
    t = _load()
    seen = set(zip(t["symbol"], t["day"]))
    add = [{"symbol": s, "day": d, "value_cr": str(v), "recorded": str(today or pd.Timestamp.now().date()),
            "status": "waiting"} for s, d, v in promoter_events(rows) if (s, d) not in seen]
    if add:
        t = pd.concat([t, pd.DataFrame(add)], ignore_index=True).reindex(columns=COLS)
        _save(t.astype(str).replace("nan", ""))
    return len(add)


def settle(load=None):
    """Fill the would-be trade of every waiting event whose prices exist. -> number settled."""
    from . import data_prices
    load = load or data_prices.load
    t = _load()
    n = 0
    for i, r in t[t["status"] == "waiting"].iterrows():
        d = load(r["symbol"])
        if d is None or not len(d):
            continue
        day = pd.Timestamp(r["day"])
        idx = d.index
        k = idx.searchsorted(day, side="right")
        if k < 1 or k + HOLD >= len(idx):
            continue
        turn = float((d["close"] * d["volume"]).iloc[max(0, k - 20):k].mean())
        if turn < 2e7:
            t.loc[i, "status"] = "skipped (thin stock)"
            n += 1
            continue
        e, x = float(d["open"].iloc[k]), float(d["open"].iloc[k + HOLD])
        t.loc[i, ["entry_date", "entry", "exit_date", "exit", "net_pct", "status"]] = [
            str(idx[k].date()), f"{e:.2f}", str(idx[k + HOLD].date()), f"{x:.2f}", f"{(x / e - 1 - COST) * 100:.2f}", "done"]
        n += 1
    if n:
        _save(t)
    return n


def summary():
    t = _load()
    done = pd.to_numeric(t.loc[t["status"] == "done", "net_pct"], errors="coerce").dropna()
    return {"events": int(len(t)), "done": int(len(done)), "avg_pct": round(float(done.mean()), 2) if len(done) else None,
            "won_pct": round(float((done > 0).mean() * 100), 1) if len(done) else None}


def run():
    try:
        a = record()
        b = settle()
        log.info("Shadow record (promoter buying): %d new, %d settled, %s", a, b, summary())
    except Exception as e:
        log.warning("Shadow record failed: %s", type(e).__name__)
