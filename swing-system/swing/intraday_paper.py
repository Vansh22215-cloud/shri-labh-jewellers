"""Intraday PAPER trading (adapted from 'trader-scanner' + 'trader-entry' + 'trader-exit'): owner's choice = paper only.

Every 5 minutes, 09:35-15:15 IST, on the ~150 most-traded NSE stocks, using only COMPLETED 5-minute bars:
  ORB    opening-range breakout: range = 09:15-09:30; first 5-min close above the high (long) or below the low
         (short) before 11:30. Stop = middle of the range, target = 1x the risk.
  FLAG   up 1.5%+ from the open in the first hour, then 3-6 bars resting within 0.6%; first close above the rest's
         high. Stop = the rest's low, target = 2x the risk.
  BOUNCE down 2.5%+ from yesterday's close and 5-min RSI(14) under 25; first bar closing above the previous bar's
         high. Stop = the day's low, target = 1x the risk.
One trade per stock per setup per day; at most 6 open at once. Sized to lose Rs 450 (1% of capital) at the stop, no
leverage. Stop counted first if stop and target fall in the same bar. Everything still open is closed at 15:20.
Results are after Zerodha intraday charges, kept in data/intraday_paper.csv and the lifelong archive.
NO tips or messages are sent from this - only a line in the Saturday summary and the 2-week review. It may only ever
send tips after passing the same walk-forward tests as the swing strategy, and with the owner's yes.
"""
import numpy as np
import pandas as pd

from .config import DATA, get_logger

log = get_logger()
TRADES_F = DATA / "intraday_paper.csv"
RISK_RS = 450.0
MAX_OPEN = 6
COLS = ["date", "symbol", "setup", "side", "entry_time", "entry", "stop", "target", "qty", "status",
        "exit_time", "exit", "pnl", "charges", "net"]


def load():
    return pd.read_csv(TRADES_F) if TRADES_F.exists() else pd.DataFrame(columns=COLS)


def _rsi(c, n=14):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def signals(b, prev_close=None):
    """Setups on ONE stock's completed 5-min bars of today (index = bar start time, IST naive).
    -> list of dicts {setup, side, entry_time, entry, stop, target}. Only the first trigger of each setup."""
    out = []
    if len(b) < 4:
        return out
    t = b.index
    orb = b[t < t[0].normalize() + pd.Timedelta(hours=9, minutes=30)]
    after = b[(t >= t[0].normalize() + pd.Timedelta(hours=9, minutes=30)) &
              (t < t[0].normalize() + pd.Timedelta(hours=11, minutes=30))]
    if len(orb) >= 3 and len(after):
        hi, lo = orb["high"].max(), orb["low"].min()
        mid = (hi + lo) / 2
        up = after[after["close"] > hi]
        dn = after[after["close"] < lo]
        first = min([x for x in (up.index[:1].tolist() + dn.index[:1].tolist())], default=None)
        if first is not None:
            c = float(after.at[first, "close"])
            if len(up) and up.index[0] == first:
                out.append({"setup": "ORB", "side": "buy", "entry_time": first, "entry": c, "stop": mid,
                            "target": c + (c - mid)})
            else:
                out.append({"setup": "ORB", "side": "sell", "entry_time": first, "entry": c, "stop": mid,
                            "target": c - (mid - c)})
    o = float(b["open"].iloc[0])
    first_hour = b[t < t[0].normalize() + pd.Timedelta(hours=10, minutes=15)]
    if len(first_hour) >= 4 and first_hour["high"].max() >= o * 1.015:
        peak_i = first_hour["high"].values.argmax()
        rest = b.iloc[peak_i + 1:]
        for k in range(3, 7):
            if len(rest) <= k:
                break
            box = rest.iloc[:k]
            if box["high"].max() / box["low"].min() - 1 <= 0.006:
                brk = rest.iloc[k:]
                brk = brk[brk["close"] > box["high"].max()]
                if len(brk):
                    c, lo_ = float(brk["close"].iloc[0]), float(box["low"].min())
                    if c > lo_:
                        out.append({"setup": "FLAG", "side": "buy", "entry_time": brk.index[0], "entry": c,
                                    "stop": lo_, "target": c + 2 * (c - lo_)})
                break
    if prev_close:
        r = _rsi(b["close"])
        down = b["close"] <= prev_close * 0.975
        oversold = down & (r < 25)
        if oversold.any():
            j = int(np.argmax(oversold.values))
            for i in range(j + 1, len(b)):
                if b["close"].iloc[i] > b["high"].iloc[i - 1]:
                    c, lo_ = float(b["close"].iloc[i]), float(b["low"].iloc[: i + 1].min())
                    if c > lo_:
                        out.append({"setup": "BOUNCE", "side": "buy", "entry_time": b.index[i], "entry": c,
                                    "stop": lo_, "target": c + (c - lo_)})
                    break
    return out


def _charges(entry, exit_, qty):
    try:
        from .intraday import mis_costs
        return float(mis_costs(entry * qty, exit_ * qty))
    except Exception:
        return 0.0003 * (entry + exit_) * qty + 40


def manage(trades, bars_by_sym, now):
    """Walk open paper trades through the new completed bars; close at stop/target, or all at 15:20."""
    for c in ("status", "exit_time"):
        if c in trades:
            trades[c] = trades[c].astype(object)
    for c in ("exit", "pnl", "charges", "net"):
        if c in trades:
            trades[c] = pd.to_numeric(trades[c], errors="coerce").astype(float)
    close_time = now.normalize() + pd.Timedelta(hours=15, minutes=20)
    for i, r in trades[trades["status"] == "open"].iterrows():
        b = bars_by_sym.get(r["symbol"])
        if b is None or not len(b):
            continue
        b = b[b.index > pd.Timestamp(r["entry_time"])]
        buy = r["side"] == "buy"
        res = None
        for ts, x in b.iterrows():
            hit_s = x["low"] <= r["stop"] if buy else x["high"] >= r["stop"]
            hit_t = x["high"] >= r["target"] if buy else x["low"] <= r["target"]
            if hit_s:
                res = ("stop", ts, r["stop"]); break
            if hit_t:
                res = ("target", ts, r["target"]); break
        if res is None and now >= close_time and len(b):
            res = ("closed 15:20", b.index[-1], float(b["close"].iloc[-1]))
        if res:
            st, ts, px = res
            pnl = (px - r["entry"]) * r["qty"] * (1 if buy else -1)
            ch = _charges(r["entry"], px, r["qty"])
            trades.loc[i, ["status", "exit_time", "exit", "pnl", "charges", "net"]] = \
                [st, str(ts), round(px, 2), round(pnl, 2), round(ch, 2), round(pnl - ch, 2)]
    return trades


def bars_today(symbols, now):
    """Completed 5-minute bars of today for each symbol (Kite when logged in, else Yahoo)."""
    out = {}
    try:
        from . import kite
        if kite.logged_in():
            import time as _t
            for s in symbols:
                h = kite.historical(s, "5minute", days=1)
                _t.sleep(0.35)                       # Kite allows ~3 history requests a second
                if h is not None and len(h):
                    h.index = pd.to_datetime(h.index).tz_localize(None) if h.index.tz is not None else h.index
                    out[s] = h[h.index.normalize() == now.normalize()]
            if len(out) >= len(symbols) // 2:
                res = {s: b[b.index + pd.Timedelta(minutes=5) <= now] for s, b in out.items()}
                res["_prev"] = {s: v["prev"] for s, v in kite.quotes(list(out)).items() if v.get("prev")}
                res["_source"] = "Zerodha"
                return res
    except Exception:
        out = {}
    import yfinance as yf
    from .data_prices import yahoo_ticker
    tick = {yahoo_ticker(s): s for s in symbols}
    raw = yf.download(list(tick), period="5d", interval="5m", group_by="ticker", progress=False, threads=True,
                      auto_adjust=False)
    prev = {}
    for t, s in tick.items():
        try:
            d = (raw[t] if len(tick) > 1 else raw).dropna(subset=["Close"])
        except KeyError:
            continue
        d = d.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]]
        d.index = d.index.tz_convert("Asia/Kolkata").tz_localize(None)
        today = d[d.index.normalize() == now.normalize()]
        before = d[d.index.normalize() < now.normalize()]
        if len(before):
            prev[s] = float(before["close"].iloc[-1])
        out[s] = today[today.index + pd.Timedelta(minutes=5) <= now]          # completed bars only
    out["_prev"] = prev
    out["_source"] = "Yahoo"
    return out


def step(now=None, symbols=None, bars=None):
    """One pass: manage open paper trades, open new ones. Returns the trades table."""
    now = now or pd.Timestamp.now(tz="Asia/Kolkata").tz_localize(None)
    if symbols is None:
        from .archive import intraday_universe
        symbols = intraday_universe()[:150]
    bars = bars if bars is not None else bars_today(symbols, now)
    prev = bars.pop("_prev", {}) if isinstance(bars, dict) else {}
    source = bars.pop("_source", "Yahoo") if isinstance(bars, dict) else "Yahoo"
    tr = load()
    tr = manage(tr, bars, now)
    today = str(now.date())
    if now.hour * 60 + now.minute < 15 * 60 + 15:
        n_open = int((tr["status"] == "open").sum())
        done = set(zip(tr.loc[tr["date"] == today, "symbol"], tr.loc[tr["date"] == today, "setup"]))
        new = []
        for s, b in bars.items():
            for sg in signals(b, prev.get(s)):
                if (s, sg["setup"]) in done or n_open >= MAX_OPEN:
                    continue
                if pd.Timestamp(sg["entry_time"]) + pd.Timedelta(minutes=10) < now - pd.Timedelta(minutes=5):
                    continue            # only fresh triggers (the entry timer acts on the bar that just closed)
                risk_ps = abs(sg["entry"] - sg["stop"])
                if risk_ps <= 0:
                    continue
                qty = int(min(RISK_RS / risk_ps, 45000 / sg["entry"]))
                if qty < 1:
                    continue
                new.append(dict(sg, date=today, symbol=s, qty=qty, status="open", entry_time=str(sg["entry_time"]),
                                entry=round(sg["entry"], 2), stop=round(sg["stop"], 2), target=round(sg["target"], 2)))
                done.add((s, sg["setup"]))
                n_open += 1
        if new:
            try:
                sent = send_tips(new, now, source)
                for n_ in new:
                    n_["tipped"] = n_["symbol"] + n_["setup"] in sent
            except Exception as e:
                log.warning("intraday tips failed: %s", type(e).__name__)
            tr = pd.concat([tr, pd.DataFrame(new)], ignore_index=True)
            log.info("Intraday: %d new setup(s), %d sent as tips", len(new), sum(bool(n_.get("tipped")) for n_ in new))
    tr.to_csv(TRADES_F, index=False)
    try:
        if now.hour * 60 + now.minute >= 15 * 60 + 20:
            from . import archive
            archive.write_day("intraday_paper", now.date(), tr[tr["date"] == today].astype(str))
    except Exception:
        pass
    return tr


SETUPS_F = DATA / "intraday_setups.json"
SETUP_WORDS = {"ORB": "opening-range breakout", "FLAG": "bull flag breakout", "BOUNCE": "oversold bounce"}


def allowed_setups():
    """-> (set of setups allowed to send tips, validated?) from the Kite-history test; all three until it has run."""
    import json
    try:
        d = json.loads(SETUPS_F.read_text())
        return set(d.get("allowed", [])), True
    except Exception:
        return set(SETUP_WORDS), False


def send_tips(new, now, source="Yahoo", settings=None):
    """Owner's choice (D94): live intraday tips in aggressive mode. Returns {symbol+setup} that were sent."""
    from .config import load_settings
    s = settings or load_settings()
    if not s.get("intraday_tips", False) or s.get("kill_switch"):
        return set()
    m = now.hour * 60 + now.minute
    if not (9 * 60 + 35 <= m <= 14 * 60 + 30):          # no new intraday tips after 2:30 pm
        return set()
    allowed, validated = allowed_setups()
    tr = load()
    sent_today = int(tr.loc[tr["date"] == str(now.date()), "tipped"].fillna(False).astype(bool).sum()) \
        if "tipped" in tr else 0
    cap = int(s.get("intraday_max_tips", 2))
    from . import risk, telegram
    from .bot import send_ticket
    tok, chat = (s.get("telegram_bot_token") or "").strip(), str(s.get("telegram_chat_id") or "").strip()
    out = set()
    for n in sorted(new, key=lambda x: x["setup"] != "ORB"):
        if sent_today >= cap or n["setup"] not in allowed:
            continue
        tm_line = None
        try:
            from . import kite, timemachine
            hist = kite.historical(n["symbol"], "5minute", days=30)
            left = max(1, int(((now.normalize() + pd.Timedelta(hours=15, minutes=15)) - now).total_seconds() // 300))
            tm = timemachine.simulate(hist, n["side"], n["entry"], n["stop"], n["target"], left, lookback=1500) \
                if hist is not None else None
            tm_line = timemachine.line(tm, "5-min bars", f"{n['symbol']}'s last 30 days of 5-minute bars, until 3:15 pm")
        except Exception:
            pass
        act = "BUY" if n["side"] == "buy" else "SELL (short, intraday only)"
        lab = ("validated on Kite history" if validated else "AGGRESSIVE - not yet validated (test runs tonight)")
        msg = (f"⚡ <b>INTRADAY TIP</b> · {now:%I:%M %p} · {lab}\n"
               f"<b>{act} {n['symbol']}</b> now near {n['entry']:,.2f} - {SETUP_WORDS[n['setup']]}\n"
               f"<code>Stop {n['stop']:,.2f} · Target {n['target']:,.2f} · exit by 3:15 pm at the latest</code>\n"
               f"👉 Only if the price is still within 0.3% of {n['entry']:,.2f}; skip it if it ran away. Intraday "
               f"(MIS) - Zerodha squares off at 3:20 pm.\n" + (f"🎰 {tm_line}\n" if tm_line else "") +
               f"<i>Prices: {source}. Most intraday traders lose money - small size only. Research, not advice.</i>")
        if telegram.send(s, msg, html=True, label="intraday tip").startswith("Telegram message sent"):
            sent_today += 1
            out.add(n["symbol"] + n["setup"])
            try:
                t = risk.new_ticket(n["symbol"], n["side"], n["entry"], n["stop"], n["target"],
                                    f"intraday {n['setup']} {now:%d %b}", product="MIS", settings=s)
                if tok and chat:
                    send_ticket(tok, chat, t)
            except Exception as e:
                log.warning("intraday ticket failed: %s", type(e).__name__)
    return out


def week_line(today=None):
    """'Intraday paper: 23 trades this week, 11 won, 12 lost, net -₹180 after charges (ORB +, FLAG -, ...)'."""
    tr = load()
    if not len(tr):
        return "📊 Intraday paper: no paper trades yet."
    today = pd.Timestamp(today or pd.Timestamp.now().date())
    w = tr[(pd.to_datetime(tr["date"]) > today - pd.Timedelta(days=7)) & (tr["status"] != "open")]
    if not len(w):
        return "📊 Intraday paper: no finished paper trades this week."
    won = int((w["net"].astype(float) > 0).sum())
    by = w.groupby("setup")["net"].sum().astype(float)
    return (f"📊 Intraday paper (not tips): {len(w)} trades this week, {won} won, {len(w) - won} lost, net "
            f"₹{w['net'].astype(float).sum():+,.0f} after charges (" +
            ", ".join(f"{k} ₹{v:+,.0f}" for k, v in by.items()) + ").")
