"""TIP CHECK (owner 21 Nov: "I get tips, I will send you ... analyse those and understand first").

Each tip in tips/inbox.json is replayed minute by minute on Kite's own 1-minute candles of that contract (read-only
historical API; a contract still trading keeps its history on Kite):
  - entry: "above" = buy when the price trades at/above the price after the tip time (a breakout entry);
           "at" = a limit order: a buy fills when the price comes down to it, a sell when it comes up to it;
  - stop-loss: touched (or, for "30min_close", a 30-minute candle CLOSES beyond it), checked before targets in
    the same minute (the cautious reading);
  - targets: the time each is reached before the stop; the rest is closed at 3:15 pm (intraday).
Result for one lot: (a) all sold at target 1, (b) a third at each target, stop moved to cost after target 1.
Also: the best and worst move after entry, the money one lot needs, and what NIFTY did. Kite candles are NOT
saved in the repo; only the summary (results/tip_check.md)."""
import json
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from .config import DATA, RESULTS, get_logger

log = get_logger()
INBOX = Path(__file__).resolve().parent.parent / "tips" / "inbox.json"
DONE_F = DATA / "tips_done.json"
REPORT = RESULTS / "tip_check.md"
NIFTY_LOT = 65


def inbox():
    return json.loads(INBOX.read_text()) if INBOX.exists() else []


def done():
    return json.loads(DONE_F.read_text()) if DONE_F.exists() else {}


def pending():
    d = done()
    return [t for t in inbox() if t["id"] not in d]


def nfo_table():
    from . import kite
    f = DATA / "kite_instruments_nfo_all.csv"
    if f.exists() and datetime.now().timestamp() - f.stat().st_mtime < 20 * 3600:
        return pd.read_csv(f, parse_dates=["expiry"])
    import io
    r = kite._get("/instruments/NFO", timeout=90)
    df = pd.read_csv(io.StringIO(r.text))[["instrument_token", "tradingsymbol", "name", "expiry", "strike",
                                            "instrument_type", "lot_size"]]
    df["expiry"] = pd.to_datetime(df["expiry"])
    df.to_csv(f, index=False)
    return df


def contract(tip, T):
    """The contract of a tip: the nearest expiry on/after the tip day (options: that strike and CE/PE)."""
    day = pd.Timestamp(tip["day"])
    X = T[(T["name"] == tip["underlying"]) & (T["instrument_type"] == tip["kind"]) & (T["expiry"] >= day)]
    if tip["kind"] in ("CE", "PE"):
        X = X[X["strike"] == float(tip["strike"])]
    if not len(X):
        return None
    return X.sort_values("expiry").iloc[0]


def minutes(token, day):
    from . import kite
    d = pd.Timestamp(day)
    r = kite._get(f"/instruments/historical/{int(token)}/minute",
                  params={"from": f"{d:%Y-%m-%d} 09:15:00", "to": f"{d:%Y-%m-%d} 15:30:00"}, timeout=60)
    c = r.json()["data"]["candles"]
    df = pd.DataFrame([x[:6] for x in c], columns=["date", "open", "high", "low", "close", "volume"])
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
    return df.set_index("date")


def _block_end(ts):
    """Last minute of the 30-minute candle (9:15-9:44, 9:45-10:14, ...) that holds minute ts."""
    mins = ts.hour * 60 + ts.minute - 555
    return ts.normalize() + pd.Timedelta(minutes=555 + (mins // 30) * 30 + 29)


def evaluate(tip, m):
    """Replay one tip on its 1-minute candles. -> dict (pure: no Kite calls, so it is tested)."""
    day = pd.Timestamp(tip["day"])
    t0 = day + pd.Timedelta(tip["time"] + ":00") + pd.Timedelta(minutes=1)
    m = m[(m.index >= t0) & (m.index < day + pd.Timedelta("15:16:00"))]
    sell = tip["side"] == "SELL"
    sgn = -1 if sell else 1
    p, sl, tg = float(tip["price"]), float(tip["sl"]), [float(x) for x in tip["targets"]]
    out = {"id": tip["id"], "entered": None, "entry_px": None, "hits": [], "stop": None, "exit_close": None}
    if not len(m):
        out["note"] = "no candles after the tip time"
        return out
    i0 = None
    for i, (ts, r) in enumerate(m.iterrows()):
        breakout = tip["entry"] == "above"
        ok = (r["low"] <= p if sell else r["high"] >= p) if breakout else (r["high"] >= p if sell else r["low"] <= p)
        if ok:
            o = float(r["open"])
            if breakout:
                px = min(p, o) if sell else max(p, o)       # gapped through the trigger: filled at the open
            else:
                px = max(p, o) if sell else min(p, o)
            i0, out["entered"], out["entry_px"] = i, ts.strftime("%H:%M"), round(px, 2)
            break
    if i0 is None:
        out["note"] = "entry price never reached - no trade"
        out["best_after_tip"] = round(float(m["low"].min() if sell else m["high"].max()), 2)
        return out
    after = m.iloc[i0:]
    e, stop, k, booked = out["entry_px"], sl, 0, []
    close_rule = tip.get("sl_rule") == "30min_close"
    for ts, r in after.iterrows():
        if close_rule and k == 0:                          # stop on a 30-minute candle CLOSE beyond it
            hit, spx = ts == _block_end(ts) and (r["close"] > stop if sell else r["close"] < stop), float(r["close"])
        else:
            hit, spx = (r["high"] >= stop if sell else r["low"] <= stop), stop
        if hit:
            out["stop"] = ts.strftime("%H:%M")
            booked += [spx] * (3 - len(booked))
            break
        while k < len(tg) and (r["low"] <= tg[k] if sell else r["high"] >= tg[k]):
            out["hits"].append((tg[k], ts.strftime("%H:%M")))
            booked.append(tg[k])
            k += 1
            stop = e                                       # after target 1: stop to cost
        if k >= len(tg):
            break
    if len(booked) < 3:
        out["exit_close"] = round(float(after["close"].iloc[-1]), 2)
        booked += [out["exit_close"]] * (3 - len(booked))
    out["best"] = round(float(after["low"].min() if sell else after["high"].max()), 2)
    out["worst"] = round(float(after["high"].max() if sell else after["low"].min()), 2)
    out["pts_thirds"] = round(sum(sgn * (b - e) for b in booked) / 3, 2)
    out["pts_t1"] = round(sgn * (booked[0] - e), 2)
    return out


RES_F = DATA / "tips_results.json"


def run(send=True):
    T = nfo_table()
    allres = json.loads(RES_F.read_text()) if RES_F.exists() else []
    d = done()
    for tip in pending():
        row = {"tip": tip}
        try:
            c = contract(tip, T)
            if c is None:
                row["error"] = "contract not found on Kite (expired contracts have no history)"
            else:
                lot = int(tip.get("lot") or c["lot_size"])
                r = evaluate(tip, minutes(c["instrument_token"], tip["day"]))
                r.update(symbol=c["tradingsymbol"], expiry=str(pd.Timestamp(c["expiry"]).date()), lot=lot,
                         rs_t1=round(r.get("pts_t1", 0) * lot), rs_thirds=round(r.get("pts_thirds", 0) * lot),
                         risk_lot=round(abs(float(tip["price"]) - float(tip["sl"])) * lot),
                         money_lot=round(float(tip["price"]) * lot) if tip["kind"] in ("CE", "PE") else None)
                row["r"] = r
        except Exception as e:
            row["error"] = f"{type(e).__name__}: {str(e)[:150]}"
        allres.append(row)
        d[tip["id"]] = str(datetime.now())[:19]
    RES_F.write_text(json.dumps(allres, default=str))
    DONE_F.write_text(json.dumps(d))
    write(allres)
    if send and allres:
        from . import telegram
        from .config import load_settings
        telegram.send(load_settings(), REPORT.read_text()[:3500], label="test result")
    return allres


def write(res):
    L = [f"# Tip check ({pd.Timestamp.now(tz='Asia/Kolkata'):%d %b %Y %H:%M} IST)", "",
         "**Data: Kite 1-minute candles of each contract (Kite historical API). Entry, stop and targets exactly as "
         "the tip says; stop checked before targets in the same minute; the rest closed at 3:15 pm.**", ""]
    for row in res:
        t, r = row["tip"], row.get("r")
        L += [f"## {t['day']} {t['time']} - {t['text']}", ""]
        if row.get("error"):
            L += [f"Could not check: {row['error']}", ""]
            continue
        if not r.get("entered"):
            L += [f"Contract {r['symbol']} (expiry {r['expiry']}): **{r.get('note')}**."
                  + (f" Best price after the tip: {r['best_after_tip']}." if r.get("best_after_tip") else ""), ""]
            continue
        hits = ", ".join(f"{x:g} at {tm}" for x, tm in r["hits"]) or "none"
        L += ["| | |", "|---|---|",
              f"| Contract | {r['symbol']} (expiry {r['expiry']}, lot {r['lot']}) |",
              f"| Entered | {r['entered']} at {r['entry_px']} |",
              f"| Targets reached | {hits} |",
              f"| Stop-loss hit | {r['stop'] or 'no'} |",
              f"| Best / worst after entry | {r['best']} / {r['worst']} |",
              f"| 1 lot, all sold at target 1 | ₹{r['rs_t1']:+,} |",
              f"| 1 lot, a third at each target (stop to cost after T1) | ₹{r['rs_thirds']:+,} |",
              f"| Risk on 1 lot (entry to stop) | ₹{r['risk_lot']:,} |"]
        if r.get("money_lot"):
            L.append(f"| Money for 1 lot (premium) | ₹{r['money_lot']:,} |")
        L.append("")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(L) + "\n")
