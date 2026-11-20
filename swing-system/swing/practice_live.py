"""The practice trader LIVE (from the next market day): the same rules as the replay (autotrader.py), on Kite's
streaming feed. Every entry and exit goes to the owner's Telegram at once (he may place it himself); after the
close, the dashboard picture. Practice money only - no order is ever placed."""
import threading
import time
from datetime import timedelta

import pandas as pd

from . import fno, kite, telegram
from .autotrader import Engine
from .config import DATA, PRIVATE, get_logger, load_settings
from .paper import Broker

log = get_logger()
ACCOUNT_F = PRIVATE / "paper.json"


class LiveMarket:
    def __init__(self, feed):
        self.feed = feed
        self.opt = {}                 # symbol -> [open, high, low, last] since the last minute check
        self._uni = {}
        self.lock = threading.Lock()

    def minutes(self, sym, t):
        m = self.feed.builder.minutes(sym)
        return m[m.index < pd.Timestamp(t)] if len(m) else None

    def bar(self, sym, t):
        if str(sym).startswith("NFO:"):
            with self.lock:
                b = self.opt.get(sym)
                if not b:
                    return None
                self.opt[sym] = [b[3], b[3], b[3], b[3]]
            return tuple(b)
        m = self.feed.builder.minutes(sym)
        k = pd.Timestamp(t) - timedelta(minutes=1)
        if not len(m) or k not in m.index:
            return None
        r = m.loc[k]
        return float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"])

    def price(self, sym, t):
        if str(sym).startswith("NFO:"):
            q = kite.quotes([sym]).get(sym)
            if q:
                with self.lock:
                    self.opt.setdefault(sym, [q["last"]] * 4)
            return q["last"] if q else None
        return self.feed.builder.ltp(sym)

    def option(self, spot, side, t):
        return fno.pick(spot, side, t)

    def prev_close(self, sym, t):
        return self.feed.builder.prev.get(sym)

    def prev_day(self, sym, t):
        from . import candles
        d = candles.load(sym, "day", adjusted=False)
        if d is None:
            return None
        d = d[d.index < pd.Timestamp(t).normalize()]
        return (float(d["high"].iloc[-1]), float(d["low"].iloc[-1])) if len(d) else None

    def vix_prev(self, t):
        from . import candles
        v = candles.load("INDIAVIX", "day", adjusted=False)
        if v is None:
            return None
        v = v[v.index < pd.Timestamp(t).normalize()]
        return float(v["close"].iloc[-1]) if len(v) else None

    def universe(self, t):
        day = pd.Timestamp(t).normalize()
        if day not in self._uni:
            cut = day + timedelta(hours=9, minutes=30)
            val = {}
            for s in list(self.feed.builder.done):
                if s in ("NIFTY50", "BANKNIFTY", "INDIAVIX"):
                    continue
                m = self.feed.builder.minutes(s)
                x = m[m.index < cut] if len(m) else m
                if len(x):
                    val[s] = float((x["close"] * x["volume"]).sum())
            self._uni[day] = [s for s, _ in sorted(val.items(), key=lambda kv: -kv[1])]
        return self._uni[day]

    def poll_options(self, broker):
        """Every 2 seconds: the live price of each open option position (Kite quote), for its stop and target."""
        while True:
            syms = [p.symbol for p in list(broker.acc.open.values()) if p.kind == "OPT"]
            if syms:
                q = kite.quotes(syms)
                with self.lock:
                    for s, v in q.items():
                        b = self.opt.setdefault(s, [v["last"]] * 4)
                        b[1], b[2], b[3] = max(b[1], v["last"]), min(b[2], v["last"]), v["last"]
            time.sleep(2)


def practice_params():
    """Settings the long test switched on (data/practice_params.json), else the defaults in autotrader.P."""
    import json
    try:
        return json.loads((DATA / "practice_params.json").read_text())
    except Exception:
        return {}


class PracticeLive:
    def __init__(self):
        s = load_settings()
        self.broker = Broker(ACCOUNT_F, start=float(s.get("paper_capital", 50800)))
        self.market = None
        self.engine = None
        self.sent_dash = None

    def notify(self, kind, text):
        s = load_settings()
        label = {"entry": "trade tip", "exit": "exit alert"}.get(kind, "system status")
        telegram.send_reliable(s, text, html=True, label=label)

    def on_close(self, interval, minute, feed, now=None):
        if self.market is None:
            self.market = LiveMarket(feed)
            self.engine = Engine(self.broker, self.market, params=practice_params(), notify=self.notify)
            threading.Thread(target=self.market.poll_options, args=(self.broker,), daemon=True).start()
        if interval == "minute":
            if load_settings().get("kill_switch") and self.engine.locked is None:
                self.engine.day, self.engine.locked = pd.Timestamp(minute).normalize(), "kill switch"
            self.engine.on_minute(pd.Timestamp(minute))
        if interval == "day":
            self.end_of_day(feed, pd.Timestamp(minute))

    def end_of_day(self, feed, t):
        day = t.normalize()
        if self.sent_dash == day:
            return
        self.sent_dash = day
        for key in list(self.broker.acc.open):
            p = self.broker.acc.open[key]
            self.broker.close_position(key, self.market.price(p.symbol, t) or p.ltp, t, "square-off")
        prices = {}
        for c in self.broker.day_closed(day):
            px = self.market.price(c["symbol"], t)
            if px:
                prices[c["symbol"]] = px
        self.broker.set_ltp(day, prices)
        send_dashboard(self.broker, day)


def send_dashboard(broker, day):
    from .dashboard import render
    s = load_settings()
    rows = broker.day_closed(day)
    ch, net = sum(r["charges"] for r in rows), sum(r["net"] for r in rows)
    png = DATA / f"dashboard-{pd.Timestamp(day).date()}.png"
    render(rows, png, pd.Timestamp(day), balance=broker.acc.cash, start=broker.acc.start, charges=ch, net=net,
           note="Live practice account · Kite prices")
    telegram.send_photo(s, png, caption=f"📊 Today: net ₹{net:+,.0f} · balance ₹{broker.acc.cash:,.0f}"
                                        + (" · 🎯 ₹10,000 goal reached" if net >= 10000 else ""))
    png.unlink(missing_ok=True)
