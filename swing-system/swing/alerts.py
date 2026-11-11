"""Instant price alerts (adapted from 'trader-alerts'): checked every minute 09:15-15:30 IST on market days.

Followed: the owner's recorded trades, open/pending system tips, today's scan signals, and every forwarded call that
is still open or waiting for its entry (stocks via Kite/Yahoo live prices; index/forex/gold/crypto calls via their
own data). Each event fires ONCE per item and day:
  ▶️ entry reached (price inside the buy zone / at the entry)      ⚠️ within 1.5% of the stop
  ❌ stop hit                                                       🎯 target hit
  📉📈 a recorded trade moves 4% or more in a day (first time)
Events are kept in data/alerts_fired.json so a restart never repeats them.
"""
import html
import json

import pandas as pd

from .config import DATA, get_logger, load_settings

log = get_logger()
E = html.escape
FIRED_F = DATA / "alerts_fired.json"
NEAR_STOP = 1.5
BIG_MOVE = 4.0


def _fired():
    try:
        return json.loads(FIRED_F.read_text())
    except Exception:
        return {}


def _f(x):
    x = float(x)
    return f"{x:,.5f}".rstrip("0").rstrip(".") if abs(x) < 10 else f"{x:,.2f}" if abs(x) < 10000 else f"{x:,.0f}"


def items(today):
    """Everything with levels to watch: dicts with key, name, label, side, entry_lo/hi, stop, target, qty, kind."""
    from . import journal
    from .tip_status import SIGNALS_F
    from .tipcheck import TIPS_F
    out = []
    try:
        my = journal.load_my_trades()
        for _, r in my.iterrows():
            mis = str(r.get("product", "")) == "MIS"
            out.append({"key": f"my|{r['symbol']}|{r['buy_date']}", "name": r["symbol"],
                        "label": "your intraday trade" if mis else "your trade",
                        "side": "sell" if str(r.get("side", "buy")) == "sell" else "buy", "entry_lo": None, "entry_hi": None,
                        "entry": float(r["buy_price"]), "stop": float(r["stop"]) if pd.notna(r.get("stop")) else None,
                        "target": float(r["target"]) if pd.notna(r.get("target")) else None,
                        "qty": int(r["qty"]), "kind": "mine", "ticker": None, "offset": 0.0, "mis": mis,
                        "day": str(r["buy_date"])})
    except Exception as e:
        log.warning("alerts: my trades: %s", e)
    try:
        t = journal.load_tips()
        t = t[(t["kind"] == "tip") & t["status"].isin(["pending", "open"])]
        for _, r in t.iterrows():
            out.append({"key": f"sys|{r['symbol']}|{r['date']}", "name": r["symbol"],
                        "label": f"system tip {pd.Timestamp(r['date']):%d %b}", "side": "buy",
                        "entry_lo": float(r["entry_low"]), "entry_hi": float(r["entry_high"]),
                        "entry": float(r["entry_price"]) if pd.notna(r.get("entry_price")) else None,
                        "stop": float(r["stop"]), "target": float(r["target1"]), "qty": r.get("qty"),
                        "kind": "pending" if r["status"] == "pending" else "open", "ticker": None, "offset": 0.0})
    except Exception as e:
        log.warning("alerts: system tips: %s", e)
    try:   # today's intraday tips that were sent
        from .intraday_paper import load as load_intraday
        it = load_intraday()
        if "tipped" in it:
            it = it[(it["date"] == str(today)) & (it["status"] == "open") & it["tipped"].fillna(False).astype(bool)]
            for _, r in it.iterrows():
                out.append({"key": f"itd|{r['symbol']}|{r['setup']}|{today}", "name": r["symbol"],
                            "label": f"intraday tip ({r['setup']})", "side": r["side"], "entry_lo": None,
                            "entry_hi": None, "entry": float(r["entry"]), "stop": float(r["stop"]),
                            "target": float(r["target"]), "qty": r.get("qty"), "kind": "open", "ticker": None,
                            "offset": 0.0})
    except Exception as e:
        log.warning("alerts: intraday tips: %s", e)
    if SIGNALS_F.exists():
        sg = pd.read_csv(SIGNALS_F)
        for _, r in sg[sg["date"].astype(str) == str(today)].iterrows():
            out.append({"key": f"sig|{r['symbol']}|{r['date']}", "name": r["symbol"], "label": "today's scan signal",
                        "side": "buy", "entry_lo": float(r["entry_low"]), "entry_hi": float(r["entry_high"]),
                        "entry": None, "stop": float(r["stop"]), "target": float(r["target1"]), "qty": r.get("qty"),
                        "kind": "pending", "ticker": None, "offset": 0.0})
    if TIPS_F.exists():
        fw = pd.read_csv(TIPS_F)
        fw = fw[fw["outcome"].isin(["open", "waiting entry"])]
        for _, r in fw.iterrows():
            if any(pd.isna(r.get(k)) for k in ("entry", "stop", "target")) or pd.isna(r.get("symbol")):
                continue
            side = "sell" if str(r.get("side")) == "sell" else "buy"
            tk = r.get("ticker") if isinstance(r.get("ticker"), str) and r.get("ticker") else None
            e = float(r["entry"])
            out.append({"key": f"fw|{r['symbol']}|{r['checked']}", "name": str(r["symbol"]),
                        "label": f"forwarded from {r.get('source') or 'a channel'}", "side": side,
                        "entry_lo": e if r["outcome"] == "waiting entry" else None,
                        "entry_hi": e if r["outcome"] == "waiting entry" else None, "entry": e,
                        "stop": float(r["stop"]), "target": float(r["target"]), "qty": None,
                        "kind": "pending" if r["outcome"] == "waiting entry" else "open", "ticker": tk,
                        "offset": float(r.get("offset") or 0) if pd.notna(r.get("offset")) else 0.0})
    return out


def events(it, q):
    """-> list of (event code, message) for one item given its live quote {'last','high','low'}."""
    px, hi, lo = q["last"], q.get("high", q["last"]), q.get("low", q["last"])
    buy = it["side"] != "sell"
    nm, lab = f"<b>{E(it['name'])}</b>", E(it["label"])
    out = []
    if it["kind"] == "pending" and it.get("entry_lo") is not None:
        lo_z, hi_z = it["entry_lo"], it["entry_hi"]
        if (lo <= hi_z and hi >= lo_z) or lo_z <= px <= hi_z:
            out.append(("entry", f"▶️ {nm} ({lab}) reached its buy zone {_f(lo_z)}-{_f(hi_z)} - now {_f(px)}.\n"
                                 f"If you take it: exit-if-wrong {_f(it['stop'])}, target {_f(it['target'])}."))
        return out
    if it.get("stop"):
        hit_s = (lo <= it["stop"]) if buy else (hi >= it["stop"])
        if hit_s:
            loss = f" (about ₹{(it['stop'] - it['entry']) * it['qty'] * (1 if buy else -1):+,.0f} on {it['qty']})" \
                if it.get("qty") and it.get("entry") and it["kind"] == "mine" else ""
            out.append(("stop", f"❌ {nm} ({lab}) hit the stop {_f(it['stop'])}{loss} - now {_f(px)}.\n"
                                "Exit if you hold it and your stop order did not trigger. This is the planned, limited loss."))
            return out
        dist = abs(px / it["stop"] - 1) * 100
        if dist < NEAR_STOP:
            out.append(("near", f"⚠️ {nm} ({lab}) is {dist:.1f}% from its stop {_f(it['stop'])} - now {_f(px)}.\n"
                                "Be ready to exit at the stop. No averaging down."))
    if it.get("target"):
        hit_t = (hi >= it["target"]) if buy else (lo <= it["target"])
        if hit_t:
            out.append(("target", f"🎯 {nm} ({lab}) hit the target {_f(it['target'])} - now {_f(px)}.\n"
                                  "Book profit (at least part), or move your stop up to protect it."))
    if it.get("mis") and it.get("now") is not None and it.get("day") == str(it["now"].date()) \
            and it["now"].hour * 60 + it["now"].minute >= 15 * 60 + 10:
        out.append(("squareoff", f"⏰ {nm} (your intraday trade) - square off NOW: Zerodha closes intraday (MIS) "
                                 f"positions at 3:20 pm automatically (with a charge). Price now {_f(px)}."))
    if it["kind"] == "mine" and q.get("prev"):
        mv = (px / q["prev"] - 1) * 100
        if abs(mv) >= BIG_MOVE:
            out.append(("move", f"{'📈' if mv > 0 else '📉'} {nm} (your trade) is {mv:+.1f}% today - now {_f(px)}."))
    return out


def check(send=True, now=None, quote_fn=None):
    """One pass: fetch prices, send every new event in one message. Returns the messages sent."""
    from . import kite
    now = now or pd.Timestamp.now(tz="Asia/Kolkata")
    today = str(now.date())
    its = items(today)
    if not its:
        return []
    stocks = sorted({i["name"] for i in its if not i["ticker"]})
    q, src = (quote_fn(stocks) if quote_fn else kite.live_prices(stocks))
    for tk in sorted({i["ticker"] for i in its if i["ticker"]}):
        try:
            if quote_fn:
                q.update(quote_fn([tk])[0])
                continue
            from .market_views import hourly
            h = hourly(tk, period="1d", interval="1m")
            if h is not None and len(h):
                q[tk] = {"last": float(h["close"].iloc[-1]), "high": float(h["high"].max()), "low": float(h["low"].min())}
        except Exception:
            continue
    try:   # for /status: when the last pass ran, on which prices, how many items
        (DATA / "alerts_last.json").write_text(json.dumps({"at": str(now)[:16], "source": src, "items": len(its),
                                                          "priced": sum(1 for i in its if (i["ticker"] or i["name"]) in q)}))
    except Exception:
        pass
    fired = _fired()
    msgs = []
    for it in its:
        k = it["ticker"] or it["name"]
        if k not in q:
            continue
        qq = dict(q[k])
        if it["offset"]:
            qq = {kk: (v + it["offset"] if isinstance(v, float) else v) for kk, v in qq.items()}
        it["now"] = now
        for code, text in events(it, qq):
            fk = f"{it['key']}|{code}|{today}"
            if fk in fired:
                continue
            fired[fk] = str(now)[:16]
            msgs.append(text)
    if msgs:
        fired = {k: v for k, v in fired.items() if v[:10] >= str((now - pd.Timedelta(days=10)).date())}
        FIRED_F.write_text(json.dumps(fired, indent=1))
        if send:
            from . import telegram
            telegram.send(load_settings(), "🔔 <b>ALERT</b> · " + f"{now:%I:%M %p}" + f" · prices: {E(src)}\n\n" +
                          "\n\n".join(msgs) + "\n\n<i>Research, not advice.</i>", html=True, label="instant alert")
    return msgs


def market_open(now=None):
    now = now or pd.Timestamp.now(tz="Asia/Kolkata")
    if now.weekday() >= 5:
        return False
    m = now.hour * 60 + now.minute
    return 9 * 60 + 15 <= m <= 15 * 60 + 31
