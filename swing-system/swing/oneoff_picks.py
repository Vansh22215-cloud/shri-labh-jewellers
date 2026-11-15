"""ONE-OFF request (owner, 2026-11-15): 5 NSE stocks for a 15-day hold, overall stop-loss 10%, using Kite data.
Not part of the regular system. Runs once inside the daemon (the only place the Kite keys exist):
  1. not logged in to Kite -> sends the Kite login link once (Telegram), waits for the login
  2. logged in -> Kite DAILY history (~2 years) + Kite live/last quotes for the 300 most-traded stocks,
     picks 5 and sends ONE table to Telegram; marks itself done (data/oneoff_done.json)
Selection: Rolling Candle Profile (D104) in BUY state, uptrend (price > 50-day > 200-day avg), within 10% of the
52-week high, Rs 20 cr+ traded a day, 2-day RSI < 90 (not stretched), annual volatility < 55%, no Squeeze ON,
price <= the per-stock budget; best score = 1-month strength - 0.3 x volatility + closeness to the high - signal age;
at most one stock per sector. The amount, quantities and table go only to Telegram (logs: symbols + prices only).
"""
import json

import numpy as np
import pandas as pd

from .config import DATA, ROOT, get_logger, load_settings

log = get_logger()
REQ_F = ROOT / "oneoff" / "picks_request.json"
DONE_F = DATA / "oneoff_done.json"


def _done():
    try:
        return json.loads(DONE_F.read_text())
    except Exception:
        return {}


def _mark(key, val):
    d = _done()
    d[key] = val
    DONE_F.write_text(json.dumps(d))


def _features(sym, d, q):
    from .confirmations import squeeze_on
    from .rolling_profile import signals
    c = d["close"]
    sig = signals(d[["open", "high", "low", "close", "volume"]].tail(400), "price")
    st = 0
    for b, s_ in zip(sig["buy"].values, sig["sell"].values):
        st = 1 if b else -1 if s_ else st
    since = int(len(sig) - 1 - np.where(sig["buy"].values)[0][-1]) if sig["buy"].any() else 999
    delta = c.diff()
    up = delta.clip(lower=0).ewm(alpha=0.5, adjust=False).mean()
    dn = (-delta.clip(upper=0)).ewm(alpha=0.5, adjust=False).mean()
    last = float(q["last"]) if q and q.get("last") else float(c.iloc[-1])
    return {"sym": sym, "last": last, "rcp": st, "since": since,
            "up": bool(c.iloc[-1] > c.rolling(50).mean().iloc[-1] > c.rolling(200).mean().iloc[-1]),
            "from_hi": float((c.iloc[-1] / c.tail(250).max() - 1) * 100),
            "val": float((d["close"] * d["volume"]).tail(20).median() / 1e7),
            "r20": float((c.iloc[-1] / c.iloc[-21] - 1) * 100),
            "vol": float(c.pct_change().tail(60).std() * np.sqrt(252) * 100),
            "rsi2": float((100 - 100 / (1 + up / dn)).iloc[-1]),
            "sqz": bool(squeeze_on(d["high"].values, d["low"].values, c.values)[-1]),
            "bar": str(d.index[-1].date())}


def pick(req):
    from . import kite
    from .high_prob import universe
    from .orderflow import sectors
    from .tipcheck import equity_list
    eq = set(equity_list()["SYMBOL"].astype(str))
    U = [s for s in universe() if s in eq]
    quotes = kite.quotes(U)
    rows = []
    for s in U:
        d = kite.historical(s, "day", days=730)
        if d is None or len(d) < 260:
            continue
        try:
            rows.append(_features(s, d, quotes.get(s)))
        except Exception:
            continue
    df = pd.DataFrame(rows)
    cap, n = float(req.get("capital", 15000)), int(req.get("n", 5))
    per = cap / n
    c = df[(df.rcp == 1) & df.up & (df.from_hi >= -10) & (df.val >= 20) & (df["last"] <= per * 1.25)
           & (df.rsi2 < 90) & (df.vol < 55) & ~df.sqz].copy()
    c["score"] = c.r20 - 0.3 * c.vol + 0.5 * c.from_hi - 0.2 * c.since
    c = c.sort_values("score", ascending=False)
    sec = sectors(list(c.sym))
    out, used = [], set()
    for _, r in c.iterrows():
        g = sec.get(r.sym, "Other")
        if g in used and g != "Other":
            continue
        used.add(g)
        out.append(dict(r, sector=g))
        if len(out) == n:
            break
    # quantities: equal budget, then spend what is left on the cheapest picks without going over the capital
    for o in out:
        o["qty"] = max(1, int(per // o["last"]))
    spent = sum(o["qty"] * o["last"] for o in out)
    for o in sorted(out, key=lambda x: x["last"]):
        while spent + o["last"] <= cap and (o["qty"] + 1) * o["last"] <= per * 1.4:
            o["qty"] += 1
            spent += o["last"]
    return out, len(df), (df["bar"].max() if len(df) else "")


def table(out, req, n_scanned, bar):
    sl = float(req.get("sl_pct", 10))
    tot = sum(o["qty"] * o["last"] for o in out)
    L = [f"📋 5 STOCKS · 15-day hold · Kite data (last bar {bar}, {n_scanned} stocks scanned)", "",
         "# | Stock | Buy ≈ | Qty | Amount | SL (-%g%%)" % sl]
    for i, o in enumerate(out, 1):
        L.append(f"{i} | #{o['sym']} | {o['last']:,.2f} | {o['qty']} | ₹{o['qty'] * o['last']:,.0f} | "
                 f"{o['last'] * (1 - sl / 100):,.2f}")
    L += ["", f"Total ₹{tot:,.0f} · cash left ₹{float(req.get('capital', 15000)) - tot:,.0f} · "
              f"max loss at the stops ≈ ₹{tot * sl / 100:,.0f}", "",
          "Why: " + " · ".join(f"#{o['sym']} {o['sector']}, {o['from_hi']:+.1f}% from 52w high, "
                                  f"{o['r20']:+.0f}% in 1 month" for o in out), "",
          "Exit: stop-loss or day 15, whichever first. Research, not advice."]
    return "\n".join(L)


def maybe_run(now=None):
    """Called every minute by the daemon; does nothing once the request is done."""
    try:
        req = json.loads(REQ_F.read_text())
    except Exception:
        return
    rid = str(req.get("id"))
    st = _done()
    if st.get(rid) == "done":
        return
    from . import kite, telegram
    s = load_settings()
    if not kite.configured():
        return
    if not kite.logged_in():
        if st.get(rid) != "asked":
            import html as _h
            telegram.send(s, f"🔑 <b>Log in to Kite</b> so I can pick your 5 stocks with Kite data: "
                             f"<a href=\"{_h.escape(kite.login_url())}\">Tap here to log in</a>", html=True,
                          label="kite login")
            _mark(rid, "asked")
        return
    try:
        out, n_scanned, bar = pick(req)
    except Exception as e:
        log.warning("one-off picks failed: %s", type(e).__name__)
        return
    if len(out) < 1:
        log.info("One-off picks: no stock passed the filters (%d scanned)", n_scanned)
        return
    telegram.send(s, table(out, req, n_scanned, bar), label="trade tip")
    log.info("One-off picks sent (%d scanned, last bar %s): %s", n_scanned, bar,
             ", ".join(f"{o['sym']} {o['last']:.2f}" for o in out))     # market data only - no amounts
    _mark(rid, "done")
