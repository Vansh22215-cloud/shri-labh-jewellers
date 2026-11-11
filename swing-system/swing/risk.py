"""Risk check + order TICKETS (adapted from the 'trader-risk' / 'trader-budget' / 'trader-broker' ideas).

The system never places orders (owner's choice: tickets only, no static IP). Each tip gets a ticket the owner can
copy into the Kite app; "✅ I placed it" records the trade (same as /bought). Every ticket and every recorded trade
is checked against the owner's limits first: PASS, or BLOCK with the reason in plain words.

Standard limits (owner's choice, settings.yaml -> risk_limits):
  max loss per trade 1% of capital, daily loss stop 2%, at most 3 new trades a day, no order above 25% of capital,
  a stop-loss is always required, and the order must fit the cash not already in open trades.
Tickets live in data/private/tickets.csv (personal). Paper tracking: every ticket is followed like a tip, and after
14 days the owner gets one review of how the tickets would have done.
"""
import random

import pandas as pd

from .config import PRIVATE, get_logger, load_settings

log = get_logger()
TICKETS_F = PRIVATE / "tickets.csv"
DEFAULT = {"risk_per_trade_pct": 1.0, "daily_loss_pct": 2.0, "max_trades_per_day": 3, "max_order_pct": 25.0}


def limits(settings=None):
    s = settings or load_settings()
    return dict(DEFAULT, **(s.get("risk_limits") or {}))


def _today():
    return str(pd.Timestamp.now(tz="Asia/Kolkata").date())


def account_state(today=None):
    """Open positions value, today's realised loss and today's new trades, from the owner's own records."""
    from . import journal
    today = today or _today()
    my = journal.load_my_trades()
    invested = float((my["qty"].astype(float) * my["buy_price"].astype(float)).sum()) if len(my) else 0.0
    new_today = int((my["buy_date"].astype(str) == today).sum()) if len(my) else 0
    f = PRIVATE / "closed_trades.csv"
    realised = 0.0
    if f.exists():
        c = pd.read_csv(f)
        if len(c) and "exit_date" in c:
            c = c[c["exit_date"].astype(str) == today]
            if len(c) and c["exit_price"].notna().any():
                realised = float(((c["exit_price"] - c["buy_price"]) * c["qty"]).sum())
                new_today += int((c["buy_date"].astype(str) == today).sum())
    return {"invested": invested, "realised_today": realised, "new_today": new_today}


def check(side, qty, entry, stop, capital=None, state=None, settings=None):
    """-> (ok, reasons list, numbers dict). Plain-words reasons for every limit that fails."""
    s = settings or load_settings()
    cap = float(capital or s.get("capital", 45000))
    L = limits(s)
    st = state or account_state()
    why, n = [], {}
    if not stop:
        return False, ["No stop-loss - every order must have one."], n
    per_share = abs(entry - stop)
    if per_share <= 0 or (side == "buy" and stop >= entry) or (side == "sell" and stop <= entry):
        return False, ["The stop-loss is on the wrong side of the entry price."], n
    loss = per_share * qty
    value = entry * qty
    n.update(loss=loss, value=value, max_loss=cap * L["risk_per_trade_pct"] / 100,
             max_value=cap * L["max_order_pct"] / 100, cash=cap - st["invested"])
    if loss > n["max_loss"] * 1.001:
        why.append(f"Loss at the stop ₹{loss:,.0f} is over your limit ₹{n['max_loss']:,.0f} "
                   f"({L['risk_per_trade_pct']:g}% of capital) - use at most {int(n['max_loss'] // per_share)} shares.")
    if value > n["max_value"] * 1.001:
        why.append(f"Order value ₹{value:,.0f} is over your single-order limit ₹{n['max_value']:,.0f} "
                   f"({L['max_order_pct']:g}% of capital).")
    if value > n["cash"] + 1:
        why.append(f"Not enough free cash: ₹{n['cash']:,.0f} left after your open trades, order needs ₹{value:,.0f}.")
    if st["new_today"] >= L["max_trades_per_day"]:
        why.append(f"You already took {st['new_today']} new trade(s) today (limit {L['max_trades_per_day']}).")
    if st["realised_today"] <= -cap * L["daily_loss_pct"] / 100:
        why.append(f"Daily loss stop reached: ₹{-st['realised_today']:,.0f} lost today (limit "
                   f"₹{cap * L['daily_loss_pct'] / 100:,.0f}). No new trades until tomorrow.")
    return not why, why, n


def size(entry, stop, capital=None, state=None, settings=None):
    """Largest quantity that passes every limit (0 if none)."""
    s = settings or load_settings()
    cap = float(capital or s.get("capital", 45000))
    L = limits(s)
    st = state or account_state()
    per = abs(entry - stop)
    if per <= 0 or entry <= 0:
        return 0
    q = min(cap * L["risk_per_trade_pct"] / 100 / per, cap * L["max_order_pct"] / 100 / entry,
            max(0.0, cap - st["invested"]) / entry)
    return max(0, int(q))


def new_ticket(symbol, side, entry, stop, target, origin, qty=None, product="CNC", settings=None):
    """Create, risk-check and save a ticket. Returns the ticket dict (status READY or BLOCKED)."""
    st = account_state()
    qty = int(qty) if qty else size(entry, stop, state=st, settings=settings)
    ok, why, n = check(side, max(qty, 1), entry, stop, state=st, settings=settings) if qty else \
        (False, ["Even 1 share would break your limits (stop too far away or no free cash)."], {})
    t = {"id": f"{random.randint(1000, 9999)}", "created": str(pd.Timestamp.now(tz='Asia/Kolkata').round('s')),
         "symbol": symbol, "side": side, "qty": qty, "entry": round(float(entry), 2), "stop": round(float(stop), 2),
         "target": round(float(target), 2) if target else None, "product": product, "origin": origin,
         "status": "READY" if ok else "BLOCKED", "why": " | ".join(why),
         "loss_at_stop": round(n.get("loss", 0), 0), "value": round(n.get("value", 0), 0)}
    old = pd.read_csv(TICKETS_F, dtype={"id": str}) if TICKETS_F.exists() else pd.DataFrame()
    while len(old) and t["id"] in set(old["id"].astype(str)):
        t["id"] = f"{random.randint(1000, 9999)}"
    pd.concat([old, pd.DataFrame([t])], ignore_index=True).to_csv(TICKETS_F, index=False)
    return t


def ticket_text(t):
    """The ticket as it is shown on Telegram (HTML)."""
    import html
    E = html.escape
    if t["status"] != "READY":
        return (f"🛡 <b>Risk check: BLOCK</b> - {E(t['why'])}\n"
                f"<i>No ticket. The tip is still tracked so you can see how it goes.</i>")
    act = "BUY" if t["side"] == "buy" else "SELL"
    return (f"🛡 <b>Risk check: PASS</b> - loss at the stop ₹{t['loss_at_stop']:,.0f}, order ₹{t['value']:,.0f}\n"
            f"🎫 <b>Order ticket #{t['id']}</b> (place it in the Kite app)\n"
            f"<code>{act} {t['qty']} {E(t['symbol'])} · LIMIT {t['entry']:,.2f} · {t['product']}\n"
            f"Stop-loss {t['stop']:,.2f}" + (f" · Target {t['target']:,.2f}" if t.get("target") else "") + "</code>\n"
            "<i>After buying, set the stop-loss as a GTT in Kite. Tap ✅ when placed.</i>")


def buttons(t):
    if t["status"] != "READY":
        return None
    return {"inline_keyboard": [[{"text": "✅ I placed it", "callback_data": f"placed:{t['id']}"},
                                 {"text": "⏭ Skip", "callback_data": f"skip:{t['id']}"}]]}


def on_button(data):
    """Telegram button tap -> reply text. 'placed:ID' records the trade (like /bought), 'skip:ID' marks it."""
    from . import journal
    try:
        action, tid = data.split(":", 1)
    except ValueError:
        return "Unknown button."
    if not TICKETS_F.exists():
        return "That ticket is no longer stored."
    df = pd.read_csv(TICKETS_F, dtype={"id": str})
    m = df["id"].astype(str) == tid
    if not m.any():
        return "That ticket is no longer stored."
    t = df[m].iloc[0]
    if t["status"] in ("PLACED", "SKIPPED"):
        return f"Ticket #{tid} was already marked {t['status'].lower()}."
    if action == "skip":
        df.loc[m, "status"] = "SKIPPED"
        df.to_csv(TICKETS_F, index=False)
        return f"⏭ Skipped {t['symbol']} (ticket #{tid}). It stays in the tips update so you can see how it goes."
    if action == "placed":
        ok, why, _ = check(t["side"], int(t["qty"]), float(t["entry"]), float(t["stop"]))
        my = journal.load_my_trades()
        row = pd.DataFrame([{"symbol": t["symbol"], "buy_date": _today(), "buy_price": float(t["entry"]),
                             "qty": int(t["qty"]), "stop": float(t["stop"]), "side": t["side"],
                             "product": t.get("product", "CNC"),
                             "target": float(t["target"]) if pd.notna(t.get("target")) else None}])
        pd.concat([my[my["symbol"] != t["symbol"]], row], ignore_index=True).to_csv(journal.MY_TRADES, index=False)
        df.loc[m, "status"] = "PLACED"
        df.to_csv(TICKETS_F, index=False)
        warn = ("\n⚠️ Note: " + " ".join(why)) if not ok else ""
        verb = "sold short" if t["side"] == "sell" else "bought"
        return (f"✅ Recorded: {verb} {int(t['qty'])} {t['symbol']} @ {float(t['entry']):,.2f}, stop "
                f"{float(t['stop']):,.2f}. I'll alert you the minute it hits the stop or target.{warn}")
    return "Unknown button."


def paper_review(since):
    """How every ticket since `since` would have done if placed (for the 2-week paper review)."""
    from . import data_prices
    if not TICKETS_F.exists():
        return None
    df = pd.read_csv(TICKETS_F, dtype={"id": str})
    df = df[(pd.to_datetime(df["created"].astype(str).str[:19]) >= pd.Timestamp(since)) & (df["status"] != "BLOCKED")]
    if not len(df):
        return "No tickets were made in the paper period."
    res = []
    for _, t in df.iterrows():
        h = data_prices.load(t["symbol"])
        if h is None:
            continue
        h = h[h.index >= pd.Timestamp(str(t["created"])[:10])]
        out, pnl = "open", None
        for _, b in h.iterrows():
            if b["low"] <= t["stop"]:
                out, pnl = "stop", (t["stop"] - t["entry"]) * t["qty"]; break
            if pd.notna(t["target"]) and b["high"] >= t["target"]:
                out, pnl = "target", (t["target"] - t["entry"]) * t["qty"]; break
        if out == "open" and len(h):
            pnl = (float(h["close"].iloc[-1]) - t["entry"]) * t["qty"]
        res.append((t["symbol"], out, pnl or 0.0, t["status"]))
    won = sum(1 for r in res if r[1] == "target")
    lost = sum(1 for r in res if r[1] == "stop")
    total = sum(r[2] for r in res)
    lines = [f"{'✅' if o == 'target' else '❌' if o == 'stop' else '🟢' if p >= 0 else '🔴'} {s}: {o}, ₹{p:+,.0f}"
             + (" (you placed it)" if st == "PLACED" else "") for s, o, p, st in res]
    return (f"📋 <b>2-week paper review of the order tickets</b>\n{len(res)} tickets: {won} hit target, {lost} hit "
            f"stop, {len(res) - won - lost} still open. If you had placed all of them: ₹{total:+,.0f} "
            "(before charges).\n" + "\n".join(lines[:25]))
