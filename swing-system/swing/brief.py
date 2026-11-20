"""THE ATLAS DAILY BRIEF (owner 19 Nov: "You open ATLAS and it tells you: today's strongest opportunities, the reasons,
entry / stop-loss / target, quantity and capital, the historical evidence and expected risk, ranked against each
other, the trades to avoid - and sometimes: No trade today.").

One message a market day at about 3:22 pm (inside the 3:15-3:29 buy window), built only from what the system
already decided with tested rules - the brief never invents a new rule:
  - opportunities = today's VANTAGE buy-now calls (+ today's live-engine tips), each with entry, stop, exit plan,
    quantity and money (1% risk sizing), the type's 13-year record, max loss;
  - ranking = each type's tested average result per ₹1 risked (13-year test, after 0.35% costs). Honest note: the
    tests found NO ordering that reliably adds profit (rounds 28-29), so this ranking only says which to take first
    if money is short;
  - avoid = today's signals the rules rejected (outside top-300, thin, already held, research rule, safety stop);
  - "No trade today" when nothing qualified, or the safety stop / kill switch is on.
Market data + the owner's own capital setting only; the brief is sent on Telegram, never written to git."""
import pandas as pd

from .config import PRIVATE, get_logger

log = get_logger()
SENT_F = PRIVATE / "brief_sent.txt"
BRIEF_AT = 15 * 60 + 22
EXIT_PLAN = {"RCP": "hold until the VANTAGE SELL alert (or 60 days)",
             "Breakout": "sell at the targets, else on the SELL alert",
             "Dip-buy": "sell when it closes above its 5-day average (or 10 days)"}


def _sent_today(d):
    try:
        return SENT_F.read_text().strip() == d
    except Exception:
        return False


def _mark(d):
    SENT_F.parent.mkdir(parents=True, exist_ok=True)
    SENT_F.write_text(d)


def evidence(cal, b):
    from .vantage import _cal_key
    k = _cal_key(b["setup"], b.get("tier", ""), float(b.get("score") or 0))
    v = cal.get(k) or cal.get(b["setup"]) or {}
    return k, v


def item(sym, b, price, cal, s):
    from . import safety
    k, v = evidence(cal, b)
    stop = float(b["stop"])
    risk_pct = (price - stop) / price * 100 if price > stop else None
    q = safety.size(price, stop, s) if risk_pct else 0
    per_r = (float(v["avg_pct"]) / risk_pct) if v.get("avg_pct") is not None and risk_pct else None
    tgt = ""
    if b["setup"] == "Breakout" and b.get("t1") == b.get("t1") and b.get("t1"):
        tgt = f" (targets ₹{float(b['t1']):,.2f} / ₹{float(b['t2']):,.2f})"
    return {"sym": sym, "type": k, "price": price, "stop": stop, "risk_pct": risk_pct, "qty": q, "money": q * price,
            "max_loss": q * (price - stop), "win": v.get("win_pct"), "avg": v.get("avg_pct"), "n": v.get("n"),
            "per_r": per_r, "plan": EXIT_PLAN.get(b["setup"], "follow the exit alert") + tgt}


def build(day, candidates, rejected, live_tips, s, cal, why_none=""):
    """candidates: [(sym, buy dict, price)]; rejected: DataFrame rows (symbol, setup, why); live_tips: DataFrame."""
    cap = float(s.get("capital") or 0)
    L = [f"🧭 ATLAS - today's plan ({pd.Timestamp(day):%a %d %b}, 3:22 pm)", ""]
    items = sorted((item(sym, b, p, cal, s) for sym, b, p in candidates),
                   key=lambda x: -(x["per_r"] if x["per_r"] is not None else -9))
    if not items and not len(live_tips):
        L += ["🟰 No trade today.", why_none or "No signal passed the tested rules today - the available opportunities "
              "don't justify the risk.", ""]
    else:
        L.append(f"✅ Opportunities ({len(items)} VANTAGE{f' + {len(live_tips)} live-engine' if len(live_tips) else ''}), "
                 "best evidence first:")
        for i, x in enumerate(items, 1):
            L.append(f"{i}. {x['sym']} - {x['type']}: buy ≈ ₹{x['price']:,.2f}, stop ₹{x['stop']:,.2f}"
                     + (f" ({x['risk_pct']:.1f}% away)" if x["risk_pct"] else "")
                     + (f", qty {x['qty']} ≈ ₹{x['money']:,.0f}, max loss ≈ ₹{x['max_loss']:,.0f}" if x["qty"] else "")
                     + f"\n   Exit: {x['plan']}"
                     + (f"\n   Evidence: {x['win']}% of {x['n']:,} such trades won in 13 years, average {x['avg']:+.1f}% "
                        f"after costs, before tax (≈ ₹{x['per_r']:.2f} per ₹1 risked)" if x["avg"] is not None and x["per_r"] else ""))
        for r in live_tips.itertuples():
            L.append(f"• {r.symbol} - live engine {r.type}: entry ₹{float(r.entry):,.2f}, stop ₹{float(r.stop):,.2f} "
                     f"(details in its own message)")
        need = sum(x["money"] for x in items)
        risk = sum(x["max_loss"] for x in items)
        if cap > 0:
            L += ["", f"💰 Money for all VANTAGE buys ≈ ₹{need:,.0f} ({need / cap * 100:.0f}% of ₹{cap:,.0f}); "
                      f"total max loss if every stop hits ≈ ₹{risk:,.0f} ({risk / cap * 100:.1f}%)."]
            if need > cap:
                L.append("   More than your money: take them in the order above until the money runs out; never sell "
                         "a good open trade to make room (tested: it loses).")
        L.append("Ranking = each type's 13-year evidence per ₹1 risked. Tests found no order that reliably adds "
                 "profit, so if money allows, take all.")
    if len(rejected):
        L += ["", "⛔ Avoid today (signals the rules rejected):"]
        for r in rejected.head(8).itertuples():
            L.append(f"• {r.symbol} ({r.setup}) - {str(r.why).split(' (')[0]}")
        if len(rejected) > 8:
            L.append(f"• … and {len(rejected) - 8} more")
    L += ["", "Every tip has its own message with the exact quantity. Profit is the goal, protecting capital the "
              "limit, evidence the judge. Research, not advice."]
    return "\n".join(L)


def maybe_send(day, t, res, s, cal):
    """Called from the 3:15-3:29 pm close call. Sends the brief once, at 3:22 pm or later."""
    from . import telegram, safety, vantage
    if not s.get("atlas_brief", True) or t is None or t.hour * 60 + t.minute < BRIEF_AT:
        return False
    d = str(pd.Timestamp(day).date())
    if _sent_today(d):
        return False
    why = ""
    try:
        from .kite_daily import coverage
        if coverage() < 0.9:
            why = ("Kite price data is not complete yet - ATLAS makes no tips from incomplete or other data "
                   "(owner's Kite-only rule). Tips resume by themselves once Kite data is complete.")
    except Exception:
        pass
    if why:
        cands = []
    elif s.get("kill_switch") or safety.emergency_active():
        why = "The safety stop / kill switch is on - no new trades until it is cleared."
        cands = []
    else:
        calls = vantage._load_calls()
        today = set(calls.loc[calls["day"] == d, "sym"])
        cands = []
        for sym, st, tv in res:
            b = st.get("buy") if isinstance(st, dict) else None
            if b and sym in today:
                cands.append((sym, b, float(b["close"])))
    try:
        rej = pd.read_csv(vantage.REJ_F, dtype=str)
        rej = rej[rej["day"] == d]
    except Exception:
        rej = pd.DataFrame(columns=["symbol", "setup", "why"])
    try:
        from .live_engine import load_tips
        T = load_tips()
        lt = T[(T["day"].astype(str).str[:10] == d) & (T["type"].astype(str) != "INTRADAY")] if len(T) else T
    except Exception:
        lt = pd.DataFrame()
    text = build(day, cands, rej, lt, s, cal, why)
    _mark(d)                                         # record first, then send (never twice)
    telegram.send_reliable(s, text, label="vantage indicator")
    log.info("ATLAS brief sent: %d opportunities, %d avoided", len(cands), len(rej))
    return True
