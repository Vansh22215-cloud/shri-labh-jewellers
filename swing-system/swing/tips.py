"""LIVE TIPS: approved strategies on live Kite candles of every NSE stock -> Telegram BUY with entry, stop-loss,
target(s), quantity; then the SELL alert when the stop, the target, the strategy's exit rule or the 3:20 pm
square-off is reached.

Only strategies listed in settings.yaml `live_strategies` (= tested on Kite data AND approved by the owner) send
tips. The kill switch (/stop) and the daily loss limit block NEW tips; exit alerts for open tips always go out.
Every tip is written to data/private/tips.csv BEFORE it is sent (private cache, never in git) with its context at
entry, and when it closes with how it ended - the Learner reads it.
Prices: Kite only (the streaming feed). Same strategy code as the tester."""
import threading
from datetime import timedelta

import pandas as pd

from .config import PRIVATE, get_logger, load_settings

log = get_logger()
TIPS_F = PRIVATE / "tips.csv"
_LOCK = threading.Lock()
HISTORY_BARS = 600


def load_tips():
    try:
        T = pd.read_csv(TIPS_F, parse_dates=["signal", "entry_time", "exit_time"])
    except Exception:
        return pd.DataFrame()
    for c in ("why", "targets", "id", "strategy", "sym", "kind", "interval"):
        if c in T:
            T[c] = T[c].astype(object)
    for c in ("exit", "gross_pct", "net_pct", "cost_pct", "best_pct", "worst_pct"):
        if c in T:
            T[c] = T[c].astype("float64")
    return T


def _save(T):
    TIPS_F.parent.mkdir(parents=True, exist_ok=True)
    tmp = TIPS_F.with_suffix(".tmp")
    T.to_csv(tmp, index=False)
    tmp.replace(TIPS_F)


def quantity(entry, stop, settings):
    """Shares for a tip: loss at the stop <= risk_per_trade_pct of capital AND value <= max_order_pct of capital.
    No capital set -> 0 (no quantity is guessed)."""
    cap = float(settings.get("capital") or 0)
    if cap <= 0 or not entry > stop > 0:
        return 0
    lim = settings.get("risk_limits") or {}
    by_risk = cap * float(lim.get("risk_per_trade_pct", 1)) / 100 / (entry - stop)
    by_cap = cap * float(lim.get("max_order_pct", 25)) / 100 / entry
    return int(max(0, min(by_risk, by_cap)))


def daily_loss_hit(settings, day=None):
    T = load_tips()
    cap = float(settings.get("capital") or 0)
    if not len(T) or cap <= 0 or "net_pct" not in T:
        return False
    day = pd.Timestamp(day or pd.Timestamp.now()).normalize()
    c = T[T["exit_time"].notna() & (T["exit_time"].dt.normalize() == day)]
    loss = -(c["net_pct"] / 100 * c["qty"] * c["entry"]).sum()
    return loss >= cap * float((settings.get("risk_limits") or {}).get("daily_loss_pct", 2)) / 100


def tip_text(sig, qty, settings):
    risk_pct = (sig.entry - sig.stop) / sig.entry * 100
    tg = " / ".join(f"₹{t:,.2f}" for t in sig.targets) or "-"
    L = [f"🟢 <b>BUY {sig.sym}</b> - {sig.strategy} ({sig.interval}, {sig.kind})",
         f"Entry ≈ ₹{sig.entry:,.2f} (candle closed {sig.time:%H:%M})",
         f"Stop-loss ₹{sig.stop:,.2f} ({risk_pct:.1f}% below)",
         f"Target {tg}"]
    if qty:
        L.append(f"Qty {qty} ≈ ₹{qty * sig.entry:,.0f} · max loss ≈ ₹{qty * (sig.entry - sig.stop):,.0f}")
    else:
        L.append("Qty: set your capital with /capital to get a quantity")
    L.append("Exit: stop / target / the strategy's exit rule" + (" / by 3:20 pm" if sig.kind == "intraday" else "")
             + " - I send the SELL alert.")
    L.append("<i>Kite live data. Research, not advice.</i>")
    return "\n".join(L)


def record_and_send(sig, settings, context=None):
    """One tip: skip if the same strategy already has this stock open; record first, then send."""
    from . import telegram
    with _LOCK:
        T = load_tips()
        if len(T) and ((T["strategy"] == sig.strategy) & (T["sym"] == sig.sym) & T["exit_time"].isna()).any():
            return False
        qty = quantity(sig.entry, sig.stop, settings)
        row = {"id": f"{sig.strategy}-{sig.sym}-{sig.time:%Y%m%d%H%M}", "strategy": sig.strategy, "interval": sig.interval,
               "kind": sig.kind, "sym": sig.sym, "signal": sig.time, "entry_time": sig.time, "entry": sig.entry,
               "stop": sig.stop, "target": sig.targets[-1] if sig.targets else None,
               "targets": "/".join(str(t) for t in sig.targets), "qty": qty, "exit_time": pd.NaT, "exit": None,
               "why": None, "gross_pct": None, "net_pct": None, "cost_pct": None, "best_pct": 0.0, "worst_pct": 0.0,
               "bars": 0, **(context or {})}
        T = pd.concat([T, pd.DataFrame([row])], ignore_index=True)
        _save(T)
    telegram.send_reliable(settings, tip_text(sig, qty, settings), html=True, label="trade tip")
    log.info("Tip sent: %s %s", sig.strategy, sig.interval)
    return True


def close_tip(i, T, when, price, why, settings):
    from . import costs, telegram
    r = T.loc[i]
    gross = price / r["entry"] - 1
    cost = costs.round_trip_pct(max(int(r["qty"] or 0), 1) * r["entry"], "intraday" if r["kind"] == "intraday" else "delivery")
    T.loc[i, ["exit_time", "exit", "why", "gross_pct", "net_pct", "cost_pct"]] = \
        [when, round(price, 2), why, round(gross * 100, 3), round((gross - cost) * 100, 3), round(cost * 100, 3)]
    icon = "🎯" if why == "target" else "🔴" if why == "stop-loss" else "⏹"
    q = int(r["qty"] or 0)
    money = f" · ≈ ₹{q * r['entry'] * (gross - cost):+,.0f} after costs" if q else ""
    telegram.send_reliable(settings, f"{icon} <b>SELL {r['sym']}</b> - {why} ({r['strategy']})\n"
                                     f"Exit ≈ ₹{price:,.2f} · bought ₹{r['entry']:,.2f} · {gross * 100:+.2f}% "
                                     f"({(gross - cost) * 100:+.2f}% after costs){money}\n<i>Kite live data.</i>",
                           html=True, label="exit alert")


def check_exits(feed, minute, interval_closed, strategies, settings, now=None):
    """Every finished 1-minute candle: stop/target of every open tip; at its interval's close: the exit rule;
    3:20 pm: intraday square-off."""
    with _LOCK:
        T = load_tips()
        if not len(T):
            return 0
        n = 0
        for i in T.index[T["exit_time"].isna()]:
            r = T.loc[i]
            m = feed.builder.today(r["sym"], "minute", now=now)
            if not len(m):
                continue
            m = m[m.index > pd.Timestamp(r["entry_time"])]
            if not len(m):
                continue
            last = m.iloc[-1]
            T.loc[i, "best_pct"] = max(float(r["best_pct"] or 0), (m["high"].max() / r["entry"] - 1) * 100)
            T.loc[i, "worst_pct"] = min(float(r["worst_pct"] or 0), (m["low"].min() / r["entry"] - 1) * 100)
            when = m.index[-1] + timedelta(minutes=1)
            if last["low"] <= r["stop"]:
                close_tip(i, T, when, min(float(last["open"]), float(r["stop"])), "stop-loss", settings)
            elif r["target"] == r["target"] and r["target"] and last["high"] >= r["target"]:
                close_tip(i, T, when, max(float(last["open"]), float(r["target"])), "target", settings)
            elif r["kind"] == "intraday" and when.strftime("%H:%M") >= "15:20":
                close_tip(i, T, when, float(last["close"]), "square-off 3:20 pm", settings)
            elif r["interval"] in interval_closed and r["strategy"] in strategies:
                st = strategies[r["strategy"]]
                d = history(feed, r["sym"], r["interval"], now=now)
                if d is not None and len(d) and bool(st.exits(d).iloc[-1]):
                    close_tip(i, T, when, float(d["close"].iloc[-1]), "exit rule", settings)
                else:
                    continue
            else:
                continue
            n += 1
        _save(T)
        return n


_HIST = {}


def history(feed, sym, interval, now=None):
    """Library candles (up to yesterday) + today's live ones. The library part is read once a day per stock."""
    from . import candles
    day = pd.Timestamp.now().normalize()
    k = (sym, interval, day)
    if k not in _HIST:
        base = "day" if interval == "day" else interval
        h = candles.load(sym, base)
        _HIST[k] = h[h.index < day].tail(HISTORY_BARS) if h is not None else pd.DataFrame(columns=candles.COLS)
    t = feed.builder.today(sym, interval, now=now)
    return pd.concat([_HIST[k], t]) if len(t) else _HIST[k]


class Scanner:
    """Called by the live feed whenever candles close (live_feed.LiveFeed(on_close=Scanner().on_close))."""

    def __init__(self, settings=None):
        from .strategy import load_all
        self.settings = settings or load_settings()
        allowed = set(self.settings.get("live_strategies") or [])
        self.strategies = {k: v for k, v in load_all().items() if k in allowed}
        self.blocked_told = False

    def on_close(self, interval, minute, feed, now=None):
        s = load_settings()
        if interval == "minute":                  # once a minute: every open tip, with all intervals closing now
            from .live_feed import closed_intervals
            check_exits(feed, minute, set(closed_intervals(minute - timedelta(minutes=1))), self.strategies, s, now=now)
        if not self.strategies:
            return 0
        if s.get("kill_switch") or daily_loss_hit(s):
            if not self.blocked_told:
                log.info("Tips: kill switch / daily loss limit on - no new tips")
                self.blocked_told = True
            return 0
        # day strategies are checked at 3:20 pm on the forming day candle (time to buy before the close)
        ivs = {interval} - {"day"}
        if interval == "5minute" and minute.strftime("%H:%M") == "15:20":
            ivs.add("day")
        sent = 0
        for st in self.strategies.values():
            if st.interval not in ivs:
                continue
            for sym in list(feed.builder.day):
                if sym in ("NIFTY50", "BANKNIFTY", "INDIAVIX"):
                    continue
                d = history(feed, sym, st.interval, now=now)
                try:
                    sig = st.signal_at(sym, d, s)
                except Exception as e:
                    log.info("Tips: %s %s failed: %s", st.name, sym, type(e).__name__)
                    continue
                if sig is None:
                    continue
                if st.interval == "day":
                    sig.time = pd.Timestamp(minute)      # bought at ~3:20 pm: exits are watched from then on
                ctx = {}
                try:
                    from . import backtest, candles
                    ctx = backtest.context_at(sig.time, st.interval, backtest.daily_context(sym, candles.load("NIFTY50", "day"),
                                                                                            candles.load("INDIAVIX", "day")), d)
                except Exception:
                    pass
                sent += bool(record_and_send(sig, s, ctx))
        return sent
