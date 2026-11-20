"""LIVE candles of every NSE stock from Kite's streaming feed (owner 20 Nov: "watch all minute, hourly and 1-day
candles in live scanning").

Kite WebSocket (wss://ws.kite.trade, read-only market data, part of the owner's Kite Connect plan) in 'quote'
mode: every trade update of every subscribed stock (up to 3,000 per connection, 3 connections). From the ticks:
  - 1-minute candles: open/high/low/close of the prices seen in the minute (IST clock), volume = growth of the
    day's traded volume during the minute;
  - 3/5/10/15/30/60-minute candles: built from the 1-minute ones, aligned to the 9:15 open;
  - today's day candle: the exchange's own day open/high/low, the last price, the day's volume.
When a candle closes, every live strategy that uses that interval is called (scanner.on_close).
GitHub hands over to a new run during the day (runs last ~5 h): a new run first fills the minutes it missed with
Kite's own historical 1-minute candles (repair_today), then continues from the stream. After the close the
evening download replaces today's live candles with Kite's official ones in the library.
No Kite login -> nothing is built, no tips (reported once a day)."""
import json
import struct
import threading
import time
from datetime import datetime, timedelta, timezone

import pandas as pd

from .config import DATA, get_logger

log = get_logger()
IST = timezone(timedelta(hours=5, minutes=30))
WS_URL = "wss://ws.kite.trade"
from .r2 import root as _kite_root
LIVE = _kite_root() / "live"
PER_CONN = 3000
OPEN_M, CLOSE_M = 9 * 60 + 15, 15 * 60 + 30
INTRADAY = {"minute": 1, "3minute": 3, "5minute": 5, "10minute": 10, "15minute": 15, "30minute": 30, "60minute": 60}


# ----------------------------------------------------------------------------- packets
def parse_binary(msg):
    """Kite binary message -> list of ticks {token, ltp, volume, open, high, low, close}. 1-byte = heartbeat."""
    if len(msg) < 2:
        return []
    n = struct.unpack(">H", msg[:2])[0]
    out, j = [], 2
    for _ in range(n):
        if j + 2 > len(msg):
            break
        ln = struct.unpack(">H", msg[j:j + 2])[0]
        p = msg[j + 2:j + 2 + ln]
        j += 2 + ln
        if len(p) < 8:
            continue
        tok = struct.unpack(">I", p[:4])[0]
        div = 100.0
        if len(p) in (28, 32):                     # index packet: token, ltp, high, low, open, close, change
            ltp, hi, lo, op, cl = (x / div for x in struct.unpack(">iiiii", p[4:24]))
            out.append({"token": tok, "ltp": ltp, "volume": None, "open": op, "high": hi, "low": lo, "close": cl})
        elif len(p) >= 44:                         # quote/full packet
            f = struct.unpack(">iiiiiiiiiii", p[:44])
            out.append({"token": tok, "ltp": f[1] / div, "volume": float(f[4]), "open": f[7] / div,
                        "high": f[8] / div, "low": f[9] / div, "close": f[10] / div})
        elif len(p) == 8:                          # ltp only
            out.append({"token": tok, "ltp": struct.unpack(">i", p[4:8])[0] / div, "volume": None})
    return out


def minute_of(ts):
    """The 1-minute candle a time belongs to (floor to the minute), or None outside 9:15-15:29."""
    m = ts.hour * 60 + ts.minute
    if not OPEN_M <= m < CLOSE_M:
        return None
    return ts.replace(second=0, microsecond=0)


# ----------------------------------------------------------------------------- candle builder
class CandleBuilder:
    """Ticks -> finished 1-minute candles per symbol (+ today's day candle). Thread-safe."""

    def __init__(self, tok2sym):
        self.tok2sym = tok2sym
        self.cur = {}            # sym -> [minute, o, h, l, c, vol_at_start, vol_last]
        self.done = {}           # sym -> list of (minute, o, h, l, c, v)
        self.day = {}            # sym -> dict(open, high, low, close, volume)
        self.last_vol = {}       # sym -> cumulative day volume at the end of the last finished minute
        self.prev = {}           # sym -> previous day's close (from the exchange)
        self.lock = threading.Lock()

    def tick(self, t, now):
        sym = self.tok2sym.get(t["token"])
        if sym is None or not t.get("ltp"):
            return
        m = minute_of(now)
        with self.lock:
            if t.get("close"):
                self.prev[sym] = t["close"]
            if t.get("open"):
                self.day[sym] = {"open": t["open"], "high": max(t["high"], t["ltp"]), "low": min(t["low"], t["ltp"]),
                                 "close": t["ltp"], "volume": t.get("volume") or 0.0}
            if m is None:
                return
            c = self.cur.get(sym)
            vol = t.get("volume")
            if c is not None and c[0] != m:
                self._finish(sym)
                c = None
            if c is None:
                start = self.last_vol.get(sym, vol if vol is not None else 0.0)
                self.cur[sym] = [m, t["ltp"], t["ltp"], t["ltp"], t["ltp"], start, vol if vol is not None else start]
            else:
                c[2], c[3], c[4] = max(c[2], t["ltp"]), min(c[3], t["ltp"]), t["ltp"]
                if vol is not None:
                    c[6] = vol

    def _finish(self, sym):
        m, o, h, l, c, v0, v1 = self.cur.pop(sym)
        self.done.setdefault(sym, []).append((m, o, h, l, c, max(0.0, (v1 or 0) - (v0 or 0))))
        self.last_vol[sym] = v1

    def close_minute(self, minute):
        """Finish every candle of minutes before `minute` (called each second by the clock) -> symbols finished."""
        out = []
        with self.lock:
            for sym in [s for s, c in self.cur.items() if c[0] < minute]:
                self._finish(sym)
                out.append(sym)
        return out

    def add_history(self, sym, df):
        """Kite's own 1-minute candles for today (gap repair) - they win over stream-built ones."""
        with self.lock:
            have = {r[0]: r for r in self.done.get(sym, [])}
            for ts, r in df.iterrows():
                have[ts.to_pydatetime().replace(tzinfo=None)] = (ts.to_pydatetime().replace(tzinfo=None), float(r["open"]),
                                                                 float(r["high"]), float(r["low"]), float(r["close"]),
                                                                 float(r["volume"]))
            self.done[sym] = sorted(have.values(), key=lambda r: r[0])

    def ltp(self, sym):
        with self.lock:
            c = self.cur.get(sym)
            if c:
                return c[4]
            d = self.day.get(sym)
            return d["close"] if d else None

    def minutes(self, sym):
        with self.lock:
            rows = [(r[0].replace(tzinfo=None) if hasattr(r[0], "tzinfo") else r[0], *r[1:]) for r in self.done.get(sym, [])]
        if not rows:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        d = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"]).set_index("date")
        return d[~d.index.duplicated(keep="last")].sort_index()

    def today(self, sym, interval, now=None):
        """Today's finished candles at any interval (day = the running day candle)."""
        if interval == "day":
            d = self.day.get(sym)
            if not d:
                return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
            day = pd.Timestamp.now().normalize()
            return pd.DataFrame([d], index=pd.DatetimeIndex([day], name="date"))
        m = self.minutes(sym)
        n = INTRADAY[interval]
        if n == 1 or not len(m):
            return m
        from .candles import resample
        r = resample(m, f"{n}min")
        last_end = pd.Timestamp(now or datetime.now(IST).replace(tzinfo=None)).floor("min")
        ends = [min(i + timedelta(minutes=n), i.normalize() + timedelta(minutes=CLOSE_M)) for i in r.index]
        return r[[e <= last_end for e in ends]]          # finished candles only

    def save(self, day=None):
        """Today's 1-minute candles of every stock -> data/live/<day>.parquet (private cache)."""
        day = day or pd.Timestamp.now().strftime("%Y-%m-%d")
        frames = []
        for sym in list(self.done):
            m = self.minutes(sym)
            if len(m):
                m = m.reset_index()
                m.insert(0, "sym", sym)
                frames.append(m)
        if not frames:
            return 0
        LIVE.mkdir(parents=True, exist_ok=True)
        df = pd.concat(frames)
        tmp = LIVE / f"{day}.tmp"
        df.to_parquet(tmp, compression="zstd")
        tmp.replace(LIVE / f"{day}.parquet")
        return len(df)

    def load_saved(self, day=None):
        f = LIVE / f"{day or pd.Timestamp.now().strftime('%Y-%m-%d')}.parquet"
        if not f.exists():
            return 0
        df = pd.read_parquet(f)
        for sym, g in df.groupby("sym"):
            self.add_history(sym, g.set_index("date")[["open", "high", "low", "close", "volume"]])
        return len(df)


def closed_intervals(minute):
    """Which intervals finish when the candle starting at `minute` closes (minute = start of the candle that just
    ended). E.g. the 9:15 1-minute candle closes at 9:16; the 9:15 5-minute candle when the 9:19 minute ends."""
    end = minute + timedelta(minutes=1)
    since = end.hour * 60 + end.minute - OPEN_M
    out = [iv for iv, n in INTRADAY.items() if since > 0 and since % n == 0]
    if end.hour * 60 + end.minute >= CLOSE_M:          # at 3:30 pm every last (shorter) candle ends, and the day
        out = list(INTRADAY) + ["day"]
    return out


# ----------------------------------------------------------------------------- the feed
class LiveFeed:
    def __init__(self, on_close=None):
        from . import kite
        ins = kite.instruments()
        syms = kite.equity_symbols()
        idx = {"NIFTY 50": "NIFTY50", "NIFTY BANK": "BANKNIFTY", "INDIA VIX": "INDIAVIX"}
        rows = ins[ins["tradingsymbol"].isin(syms) | ins["tradingsymbol"].isin(idx)]
        self.tok2sym = {int(r.instrument_token): idx.get(r.tradingsymbol, r.tradingsymbol) for r in rows.itertuples()}
        self.builder = CandleBuilder(self.tok2sym)
        self.on_close = on_close
        self.stop_ev = threading.Event()
        self.ticks = 0
        self.last_tick = 0.0
        self.conns = []
        self.errors = 0

    # --- streaming
    def _connect(self, tokens):
        import websocket
        from . import kite
        k, _ = kite.keys()
        tok = kite.token()
        if not (k and tok):
            raise RuntimeError("not logged in")

        def on_open(ws):
            ws.send(json.dumps({"a": "subscribe", "v": tokens}))
            ws.send(json.dumps({"a": "mode", "v": ["quote", tokens]}))

        def on_message(ws, msg):
            if isinstance(msg, (bytes, bytearray)) and len(msg) > 1:
                now = datetime.now(IST).replace(tzinfo=None)
                for t in parse_binary(msg):
                    self.builder.tick(t, now)
                    self.ticks += 1
                self.last_tick = time.time()

        def on_error(ws, err):
            self.errors += 1
            log.warning("Live feed: stream error %s", type(err).__name__)

        while not self.stop_ev.is_set():
            ws = websocket.WebSocketApp(f"{WS_URL}?api_key={k}&access_token={tok}", on_open=on_open,
                                        on_message=on_message, on_error=on_error)
            self.conns.append(ws)
            ws.run_forever(ping_interval=20, ping_timeout=10)
            if self.stop_ev.is_set() or not kite.logged_in():
                break
            time.sleep(min(60, 5 * (1 + self.errors)))     # reconnect with a growing pause

    def _clock(self):
        """Every second: finish candles of past minutes; on each finished minute call the scanner for the
        intervals that just closed."""
        last = None
        while not self.stop_ev.is_set():
            now = datetime.now(IST).replace(tzinfo=None)
            m = now.replace(second=0, microsecond=0)
            if last is not None and m > last and OPEN_M < m.hour * 60 + m.minute <= CLOSE_M:
                self.builder.close_minute(m)
                if self.on_close:
                    for iv in closed_intervals(m - timedelta(minutes=1)):
                        try:
                            self.on_close(iv, m, self)
                        except Exception as e:
                            log.warning("Live feed: scanner failed on %s: %s", iv, type(e).__name__)
                if m.minute % 5 == 0:
                    try:
                        self.builder.save()
                    except Exception as e:
                        log.warning("Live feed: save failed: %s", type(e).__name__)
            last = m
            if now.hour * 60 + now.minute > CLOSE_M + 2:
                self.builder.save()
                self.stop()
                break
            time.sleep(1)

    def repair_today(self, max_requests=4000):
        """Fill minutes this run missed (started late / handed over) with Kite's own 1-minute candles of today."""
        from . import candles
        today = pd.Timestamp.now().normalize()
        n = 0
        for sym in list(self.tok2sym.values()):
            if self.stop_ev.is_set() or n >= max_requests:
                break
            try:
                d = candles._fetch(sym, "minute", today, today)
                n += 1
                if d is not None and len(d):
                    cut = pd.Timestamp(datetime.now(IST).replace(tzinfo=None, second=0, microsecond=0))
                    self.builder.add_history(sym, d[d.index < cut])
            except Exception as e:
                log.info("Live feed: repair %s: %s", sym, type(e).__name__)
        log.info("Live feed: today's earlier minutes filled from Kite for %d stocks", n)
        return n

    def start(self, repair=True):
        self.builder.load_saved()
        toks = list(self.tok2sym)
        for i in range(0, len(toks), PER_CONN):
            threading.Thread(target=self._connect, args=(toks[i:i + PER_CONN],), daemon=True).start()
        threading.Thread(target=self._clock, daemon=True).start()
        now = datetime.now(IST)
        if repair and now.hour * 60 + now.minute > OPEN_M + 1:
            threading.Thread(target=self.repair_today, daemon=True).start()
        log.info("Live feed: streaming %d instruments", len(toks))
        return self

    def stop(self):
        self.stop_ev.set()
        for ws in self.conns:
            try:
                ws.close()
            except Exception:
                pass

    def alive(self):
        return not self.stop_ev.is_set()

    def status(self):
        age = time.time() - self.last_tick if self.last_tick else None
        return {"instruments": len(self.tok2sym), "ticks": self.ticks,
                "last_tick_s": round(age) if age is not None else None,
                "stocks_with_candles": len(self.builder.done)}
