"""PRACTICE REPLAY of past market days (owner 20 Nov: "tell me results for 5 days, one by one").
Runs the practice trader (autotrader.py) minute by minute over each day exactly as it would have run live:
decisions at each minute's close, fills at the next minute's open (+ slippage), stops/targets on each minute's
high/low, Zerodha charges, ₹50,800 carried from day to day. Data: Kite historical 1-minute candles only -
NIFTY 50, every NSE stock Kite lists (to pick the day's 100 most-traded stocks at 9:30, as live does) and the
NIFTY option contracts the trader picks.
Honest limits (written into the report):
  - Kite keeps no candles of EXPIRED option contracts, so on days whose own weekly expiry has passed, the next
    weekly expiry still listed is used (more expensive and slower than the one a trader would really have used);
  - 5 days is far too few to judge any strategy - it shows how the trader behaves, not whether it earns."""
import json
from datetime import timedelta

import pandas as pd

from . import fno, kite, telegram
from .autotrader import Engine
from .config import DATA, PRIVATE, RESULTS, get_logger, load_settings
from .paper import Broker

log = get_logger()
CACHE = DATA / "replay"
REPORT = RESULTS / "practice_replay.md"


def fetch(token, fr, to, interval="minute"):
    import time
    time.sleep(0.36)
    r = kite._get(f"/instruments/historical/{token}/{interval}",
                  params={"from": f"{fr:%Y-%m-%d} 09:00:00", "to": f"{to:%Y-%m-%d} 15:35:00"}, timeout=60)
    c = r.json()["data"]["candles"]
    if not c:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    d = pd.DataFrame([x[:6] for x in c], columns=["date", "open", "high", "low", "close", "volume"])
    d["date"] = pd.to_datetime(d["date"]).dt.tz_localize(None)
    return d.set_index("date").astype(float)


class Market:
    """The market as it looked at minute t of one past day."""

    def __init__(self, data, nfo_table, opt_loader):
        self.data, self.nfo, self.opt_loader = data, nfo_table, opt_loader
        self.day = None
        self._uni = {}

    def set_day(self, day):
        self.day = pd.Timestamp(day).normalize()

    def _df(self, sym):
        d = self.data.get(sym)
        if d is None and str(sym).startswith("NFO:"):
            d = self.opt_loader(sym)
        return d

    def _today(self, sym):
        d = self._df(sym)
        if d is None or not len(d):
            return None
        return d[(d.index >= self.day) & (d.index < self.day + timedelta(days=1))]

    def minutes(self, sym, t):
        d = self._today(sym)
        return None if d is None else d[d.index < pd.Timestamp(t)]

    def bar(self, sym, t):
        d = self._today(sym)
        if d is None:
            return None
        k = pd.Timestamp(t) - timedelta(minutes=1)
        if k not in d.index:
            return None
        r = d.loc[k]
        return float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"])

    def price(self, sym, t):
        d = self._today(sym)
        if d is None or not len(d):
            return None
        nxt = d[d.index >= pd.Timestamp(t)]
        if len(nxt):
            return float(nxt["open"].iloc[0])
        return float(d["close"].iloc[-1])

    def option(self, spot, side, t):
        return fno.pick(spot, side, t, table=self.nfo)

    def prev_close(self, sym, t):
        d = self._df(sym)
        if d is None:
            return None
        p = d[d.index < self.day]
        return float(p["close"].iloc[-1]) if len(p) else None

    def prev_day(self, sym, t):
        d = self._df(sym)
        if d is None:
            return None
        p = d[d.index < self.day]
        if not len(p):
            return None
        last = p[p.index >= p.index[-1].normalize()]
        return float(last["high"].max()), float(last["low"].min())

    def vix_prev(self, t):
        from . import candles
        v = candles.load("INDIAVIX", "day", adjusted=False)
        if v is None:
            return None
        v = v[v.index < self.day]
        return float(v["close"].iloc[-1]) if len(v) else None

    def universe(self, t):
        if self.day not in self._uni:
            cut = self.day + timedelta(hours=9, minutes=30)
            val = {}
            for s, d in self.data.items():
                if s in ("NIFTY50", "BANKNIFTY", "INDIAVIX") or str(s).startswith("NFO:"):
                    continue
                x = d[(d.index >= self.day) & (d.index < cut)]
                if len(x):
                    val[s] = float((x["close"] * x["volume"]).sum())
            self._uni[self.day] = [s for s, _ in sorted(val.items(), key=lambda kv: -kv[1])]
        return self._uni[self.day]

    def last_prices(self):
        out = {}
        for s in list(self.data):
            d = self._today(s)
            if d is not None and len(d):
                out[s] = float(d["close"].iloc[-1])
        return out


def load_data(n_days=5):
    """Kite minute candles for the last n trading days (+1 day before, for gaps) of NIFTY 50 and every NSE stock."""
    CACHE.mkdir(parents=True, exist_ok=True)
    ins = kite.instruments()
    tok = {r.tradingsymbol: int(r.instrument_token) for r in ins.itertuples()}
    today = pd.Timestamp.now().normalize()
    nifty = fetch(tok["NIFTY 50"], today - timedelta(days=16), today)
    days = sorted({d.normalize() for d in nifty.index})
    days = [d for d in days if len(nifty[(nifty.index >= d) & (nifty.index < d + timedelta(days=1))]) >= 300]
    use, first = days[-n_days:], days[-n_days - 1] if len(days) > n_days else days[0]
    data = {"NIFTY50": nifty}
    syms = kite.equity_symbols()
    for i, s in enumerate(syms):
        f = CACHE / f"{s}.parquet"
        try:
            if f.exists():
                d = pd.read_parquet(f)
                if len(d) and d.index.max() >= use[-1]:
                    data[s] = d
                    continue
            if s in tok:
                d = fetch(tok[s], first, use[-1])
                d.to_parquet(f)
                if len(d):
                    data[s] = d
        except Exception as e:
            log.info("Replay data %s: %s", s, type(e).__name__)
            if "session" in str(e) or "not logged" in str(e):
                raise
    return data, use


def run(n_days=5, send=True):
    s = load_settings()
    data, days = load_data(n_days)
    table = fno.nfo()
    opt_cache = {}

    def opt_loader(symbol):
        if symbol not in opt_cache:
            r = table[table["tradingsymbol"] == symbol.split(":", 1)[1]]
            opt_cache[symbol] = fetch(int(r["instrument_token"].iloc[0]), days[0] - timedelta(days=1), days[-1]) if len(r) else None
        return opt_cache[symbol]

    start = float(s.get("paper_capital", 50800))
    path = PRIVATE / "paper_replay.json"
    path.unlink(missing_ok=True)
    broker = Broker(path, start=start)
    mkt = Market(data, table, opt_loader)
    msgs = []
    eng = Engine(broker, mkt, notify=lambda kind, text: msgs.append((kind, text)))
    out = []
    for d in days:
        mkt.set_day(d)
        t = d + timedelta(hours=9, minutes=16)
        while t <= d + timedelta(hours=15, minutes=30):
            eng.on_minute(t)
            t += timedelta(minutes=1)
        for key in list(broker.acc.open):                      # never carried overnight
            p = broker.acc.open[key]
            px = mkt.price(p.symbol, d + timedelta(hours=15, minutes=29)) or p.ltp
            broker.close_position(key, px, d + timedelta(hours=15, minutes=29), "square-off")
        broker.set_ltp(d, mkt.last_prices())
        for sym, v in opt_cache.items():
            if v is not None:
                x = v[(v.index >= d) & (v.index < d + timedelta(days=1))]
                if len(x):
                    broker.set_ltp(d, {sym: float(x["close"].iloc[-1])})
        rows = broker.day_closed(d)
        out.append({"day": str(d.date()), "trades": len(rows), "pnl": round(sum(r["pnl"] for r in rows), 2),
                    "charges": round(sum(r["charges"] for r in rows), 2), "net": round(sum(r["net"] for r in rows), 2),
                    "balance": broker.acc.cash})
        if send:
            from .dashboard import render
            png = DATA / f"replay-{d.date()}.png"
            note = "Replay on Kite minute candles" + (" · option = next listed expiry (the real one has expired)"
                                                       if any(r["kind"] == "OPT" and pd.Timestamp(fno_expiry(r, table)) > d + timedelta(days=7)
                                                              for r in rows) else "")
            render(rows, png, d, balance=broker.acc.cash, start=start, charges=out[-1]["charges"], net=out[-1]["net"], note=note)
            telegram.send_photo(s, png, caption=f"📊 Practice day {len(out)} of {len(days)} - {d:%a %d %b}: "
                                                f"net ₹{out[-1]['net']:+,.0f} · balance ₹{broker.acc.cash:,.0f}")
            png.unlink(missing_ok=True)
    write_report(out, start, days)
    if send:
        tot = sum(o["net"] for o in out)
        hit = sum(1 for o in out if o["net"] >= 10000)
        telegram.send(s, f"🧾 Practice replay, last {len(out)} market days (Kite minute candles, ₹{start:,.0f} start):\n"
                         + "\n".join(f"• {pd.Timestamp(o['day']):%a %d %b}: {o['trades']} trades, net ₹{o['net']:+,.0f}" for o in out)
                         + f"\nTotal net ₹{tot:+,.0f} · balance ₹{start + tot:,.0f} · days with ₹10,000+: {hit} of {len(out)}.\n"
                           "5 days is far too few to judge a strategy - from Monday it runs live on the practice account "
                           "and every entry/exit comes here at once.", label="test result")
    return out


def fno_expiry(row, table):
    r = table[table["tradingsymbol"] == str(row["symbol"]).split(":", 1)[-1]]
    return r["expiry"].iloc[0] if len(r) else pd.Timestamp("2000-01-01")


def write_report(out, start, days):
    L = [f"# Practice replay - last {len(out)} market days ({pd.Timestamp.now(tz='Asia/Kolkata'):%d %b %Y %H:%M} IST)", "",
         "**Data: Kite Connect historical 1-minute candles only (NIFTY 50, every NSE stock Kite lists, the NIFTY option "
         "contracts used). Expired weekly options are not on Kite: on those days the next listed expiry was used.**", "",
         f"Practice account ₹{start:,.0f}; rules in swing/autotrader.py; Zerodha charges and slippage included.", "",
         "| Day | Trades | P&L (before charges) | Charges | Net | Balance |", "|---|---|---|---|---|---|"]
    for o in out:
        L.append(f"| {o['day']} | {o['trades']} | ₹{o['pnl']:+,.0f} | ₹{o['charges']:,.0f} | ₹{o['net']:+,.0f} | ₹{o['balance']:,.0f} |")
    L += ["", "Five days cannot show whether this earns; it shows how the trader behaves."]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(L) + "\n")
