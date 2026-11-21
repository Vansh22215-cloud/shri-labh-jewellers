"""ATLAS PRACTICE TRADER (owner 20 Nov: "you decide, earn ₹10,000 a day; losses are okay - it is an experiment").
Goal: ₹10,000+ a day on a ₹50,800 practice account. Honest note: that is ~20% a day; no rule can promise it.

The same code runs on past days (replay.py, Kite's historical minute candles) and live (Kite's streaming feed),
deciding at the close of every minute. Two strategies:

1. NIFTY weekly options - opening-range breakout with the trend
   - opening range = NIFTY's high/low of 9:15-9:30;
   - a 5-minute candle closing above the range high, above its 20-candle average and above the day's open
     -> buy the at-the-money CALL of the nearest weekly expiry; mirror image below -> buy the PUT;
   - stop-loss 30% below the premium paid, target +60% (2x the risk); once +30% the stop moves to the entry;
     sold by 3:15 pm at the latest; at most 2 NIFTY trades a day, one at a time; entries 9:35 am - 2:30 pm;
   - size: about ₹3,000 at risk per trade (6% of the account), never more premium than the free money.
2. Intraday stocks - opening-range breakout with volume, on the day's 100 most-traded stocks (by value traded
   9:15-9:30)
   - a 5-minute candle closing beyond the 9:15-9:30 range, on the same side of the day's VWAP, with 1.5x the
     day's average 5-minute volume -> buy (above) or short-sell (below);
   - stop-loss 1% (the owner's default), target 2%; once +1% the stop moves to the entry; sold by 3:15 pm;
   - size: about ₹1,500 at risk (1% stop -> ₹1.5 lakh of shares, ~₹37,500 of margin at 4x); at most 3 stock
     trades a day and 2 at a time; entries 9:35-11:30 am; gaps of more than 3% are skipped.
Day limits: no new trades once the day's net result is +₹10,000 (target reached) or -₹7,500 (loss limit).
Every entry and exit is sent to the owner on Telegram at once (live), so he can place it himself."""
from datetime import timedelta

import numpy as np
import pandas as pd

from . import strategies_lib as SLIB
from .config import get_logger

log = get_logger()
P = dict(opt_risk=3000.0, opt_stop=0.30, opt_target=0.60, opt_be=0.30, opt_max_trades=2, opt_last_entry="14:30",
         stk_risk=1500.0, stk_stop=0.01, stk_target=0.02, stk_be=0.01, stk_max_trades=0, stk_max_open=2,
         stk_last_entry="11:30", stk_vol_mult=1.5, stk_max_gap=0.03, universe=100,
         day_target=10000.0, day_max_loss=7500.0, square_off="15:15", first_entry="09:35",
         stk_sides="both", stk_factors=0, opt_factors=0, stk_scale=0.0, opt_scale=0.0)
# scaling out (owner 21 Nov): stk_scale / opt_scale = share booked at 1R (0 = off); the stop on the rest moves to
# the entry and the rest runs to stk_target / opt_target. Switched on only by the long test (longtest.py).
# 21 Nov long test (Kite 5-minute, 2,772 stocks, 2015-2026): the stock breakout loses (-₹560 a day recent, every
# variant negative) -> stock trades PAUSED (stk_max_trades=0) until a stock rule passes the test.
# extra factors (bit flags, chosen by the long test - longtest.py FILTERS / NMASKS):
#   1 beyond yesterday's high/low · 2 NIFTY moving the same way · 4 stronger than NIFTY today ·
#   8 India VIX below 20 · 16 no resistance (yesterday's high/low) within 1%


def resample5(m):
    if m is None or not len(m):
        return m
    g = m.resample("5min", origin="start_day", offset="15min", label="left", closed="left")
    return pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(), "low": g["low"].min(),
                         "close": g["close"].last(), "volume": g["volume"].sum()}).dropna(subset=["open"])


OWNER_STOCK_STOP = 0.01
# owner 21 Nov (D178): "making the most money ... and in losses, saving my capital as much as I can".
# These caps win over any setting the tests write: risk a trade, worst day, and profit protection.
OWNER_CAPS = dict(stk_risk=1000.0, opt_risk=2500.0, day_max_loss=3000.0)   # 2,500 = 1 NIFTY lot, 20% stop
PROTECT_FROM, PROTECT_KEEP = 3000.0, 0.5
# expiry day (D180): an option that expires today loses its time value fast, most of all in the afternoon.
EXPIRY_OUT, EXPIRY_WAIT_MIN, EXPIRY_MIN_GAIN = "14:45", 30, 0.10
MARKET_READS = ("09:45", "11:15", "13:15")     # once the day is +₹3,000, stop new trades if it falls below half its best


class Engine:
    def __init__(self, broker, market, params=None, notify=None):
        self.b, self.m = broker, market
        self.p = dict(P, **(params or {}))
        self.p["stk_stop"] = OWNER_STOCK_STOP            # owner 21 Nov: the stock stop-loss is always 1%
        for k, cap in OWNER_CAPS.items():
            self.p[k] = min(float(self.p[k]), cap)
        self.p["day_target"] = float("inf")              # no profit cap: keep earning while the day goes well
        self.peak = 0.0
        self._told = {}
        self._ncache = (None, None)
        for k in ("stk_last_entry", "opt_last_entry"):
            self.p[k] = str(self.p[k])
        self.notify = notify or (lambda kind, text: None)
        self.day = None
        self.locked = None

    # ---------------------------------------------------------------- helpers
    def _today_closed(self, strat):
        return [c for c in self.b.day_closed(self.day) if c["strategy"] == strat]

    def _open(self, strat):
        return [p for p in self.b.acc.open.values() if p.strategy == strat]

    def _hm(self, t):
        return t.strftime("%H:%M")

    # ---------------------------------------------------------------- every minute
    def on_minute(self, t):
        """t = the END of the minute that just finished (e.g. 09:36 after the 09:35 candle)."""
        t = pd.Timestamp(t)
        if self.day != t.normalize():
            self.day, self.locked, self.peak = t.normalize(), None, 0.0
        self.manage(t)
        if self._hm(t) >= self.p["square_off"]:
            return
        net = self.b.day_pnl(self.day)
        self.peak = max(self.peak, net)
        if self.locked is None:
            if net <= -self.p["day_max_loss"]:
                self.locked = "loss limit"
                self.notify("status", f"🔒 Day loss limit (net ₹{net:,.0f}) - no new trades today. Capital protected.")
            elif self.peak >= PROTECT_FROM and net < self.peak * PROTECT_KEEP:
                self.locked = "profit kept"
                self.notify("status", f"🔒 Profit protection: the day was +₹{self.peak:,.0f}, now ₹{net:,.0f} - no new "
                                      "trades today, keep what is left.")
        if self.locked:
            return
        if self._hm(t) in MARKET_READS:
            try:
                self.notify("status", self.market_read(t))
            except Exception as e:
                log.warning("market read failed: %s", e)
        since = (t.hour * 60 + t.minute) - (9 * 60 + 15)
        if since % 5 != 0 or since < 5:
            return
        self.nifty_entry(t)
        self.stock_entries(t)

    # ---------------------------------------------------------------- exits
    def manage(self, t):
        for key, pos in list(self.b.acc.open.items()):
            bar = self.m.bar(pos.symbol, t)
            if bar is None:
                continue
            o, h, l, c = bar
            self.b.mark(key, c)
            long = pos.side == "LONG"
            why, px = None, None
            if (l <= pos.stop) if long else (h >= pos.stop):
                why = "stop-loss" if (pos.stop < pos.avg if long else pos.stop > pos.avg) else "stop at entry"
                px = min(o, pos.stop) if long else max(o, pos.stop)
            elif (h >= pos.target) if long else (l <= pos.target):
                why, px = "target", (max(o, pos.target) if long else min(o, pos.target))
            elif self._hm(t) >= self.p["square_off"]:
                why, px = "square-off 3:15 pm", c
            elif pos.kind == "OPT" and pos.expiry == str(t.date()):
                held = (t - pd.Timestamp(pos.entry_time)).total_seconds() / 60
                if self._hm(t) >= EXPIRY_OUT:
                    why, px = "expiry day: out by 2:45 pm (time value melts)", c
                elif held >= EXPIRY_WAIT_MIN and max(pos.best, c) < pos.avg * (1 + EXPIRY_MIN_GAIN) and c < pos.avg:
                    why, px = f"expiry day: no move in {EXPIRY_WAIT_MIN} minutes (time decay) - capital saved", c
            if not why and pos.t1 and not pos.scaled and ((h >= pos.t1) if long else (l <= pos.t1)):
                lot = max(1, pos.qty // pos.lots) if pos.lots else 1
                units = pos.qty // lot
                book = min(max(int(round(units * pos.book_frac)), 1), units - 1) * lot if units >= 2 else 0
                px1 = max(o, pos.t1) if long else min(o, pos.t1)
                pos.scaled = True
                if book:
                    cl = self.b.close_part(key, book, px1, t, "booked part at 1R")
                    if cl:
                        self.notify("exit", self.exit_text(cl) + "\nRest: stop moved to cost, running to the next target.")
                else:
                    why, px = "target 1R (one lot only)", px1
                pos.stop = round(pos.avg, 2)
                self.b.save()
            if why:
                cl = self.b.close_position(key, px, t, why)
                if cl:
                    self.notify("exit", self.exit_text(cl))
                continue
            if pos.kind == "OPT" and pos.exit_mode in ("cost", "keep", "trail") and pos.r_frac:
                self._opt_exit_rule(pos, h)                # D182: the exit the strategy search chose
                continue
            be = self.p["opt_be"] if pos.kind == "OPT" else self.p["stk_be"]
            if (long and h >= pos.avg * (1 + be) and pos.stop < pos.avg) or \
                    (not long and l <= pos.avg * (1 - be) and pos.stop > pos.avg):
                pos.stop = round(pos.avg, 2)
                self.b.save()
                self.notify("status", f"✏️ <b>{pos.name}</b>: move your stop-loss to ₹{pos.stop:,.2f} (your buy price) "
                                      "- this trade can no longer lose.")

    # ---------------------------------------------------------------- NIFTY options
    def _rules(self, t):
        """Strategy/condition pairs allowed by the strategy search; each strategy checked once per stock."""
        out = []
        for name, tgt, al, vb in self.p.get("stk_rules") or []:
            if name in SLIB.STOCK:
                out.append((name, tgt, int(al), int(vb)))
        return out

    def _cond(self, t, lng):
        """Today's market condition for a trade in this direction: (with/against NIFTY, VIX bucket)."""
        n = self.m.minutes("NIFTY50", t)
        al = SLIB.market_align(float(n["open"].iloc[0]), float(n["close"].iloc[-1]), lng) if n is not None and len(n) else 0
        vx = self.m.vix_prev(t) if hasattr(self.m, "vix_prev") else None
        return al, SLIB.vix_bucket(vx)

    def _opt_exit_rule(self, pos, high):
        """After this minute (its stop/target already checked): cost = stop to the entry once +1R; keep = never
        move; trail = once +1R, the stop follows the best price at 1R distance, never below the entry."""
        r = pos.r_frac
        pos.best = max(pos.best or pos.avg, high)
        if pos.exit_mode == "keep" or pos.best < pos.avg * (1 + r):
            return
        new = pos.avg if pos.exit_mode == "cost" else max(pos.avg, pos.best * (1 - r))
        if new > pos.stop + 0.04:
            first = pos.stop < pos.avg
            pos.stop = round(new, 2)
            self.b.save()
            told = self._told.get(pos.key, 0.0)
            if first or pos.stop >= told + pos.avg * r * 0.5:   # tell the owner on the first move, then every 0.5R
                self._told[pos.key] = pos.stop
                self.notify("status", f"✏️ <b>{pos.name}</b>: move your stop-loss to ₹{pos.stop:,.2f}"
                                      + (" (your buy price) - this trade can no longer lose." if first
                                         else f" - locking profit (best so far ₹{pos.best:,.2f})."))

    def market_read(self, t):
        """A live picture of the market for the owner's own judgment (not a signal): NIFTY, VIX, expiry, the
        strongest movers among the most-traded stocks."""
        n = self.m.minutes("NIFTY50", t)
        L = [f"📊 <b>Market at {t:%H:%M}</b>"]
        if n is not None and len(n):
            o0, c = float(n["open"].iloc[0]), float(n["close"].iloc[-1])
            pc = self.m.prev_close("NIFTY50", t)
            ema = float(resample5(n)["close"].ewm(span=20, adjust=False).mean().iloc[-1])
            mood = "up-trend" if c > o0 * 1.002 and c > ema else "down-trend" if c < o0 * 0.998 and c < ema else "sideways"
            L.append(f"NIFTY {c:,.0f}" + (f" ({c / pc - 1:+.2%} vs yesterday)" if pc else "") +
                     f", {c / o0 - 1:+.2%} since open · range {float(n['low'].min()):,.0f}-{float(n['high'].max()):,.0f} · {mood}")
        vx = self.m.vix_prev(t) if hasattr(self.m, "vix_prev") else None
        if vx:
            L.append(f"India VIX (yesterday) {vx:.1f} - " + ("calm" if vx < 14 else "normal" if vx < 20 else "nervous, wide swings"))
        try:
            k = self.m.option(float(n["close"].iloc[-1]), "CE", t) if n is not None and len(n) else None
            if k and k.get("expiry") == str(t.date()):
                L.append("⏳ <b>Expiry day</b>: option premiums melt fast after lunch - quick trades, I exit options by 2:45 pm.")
        except Exception:
            pass
        uni = self.m.universe_open(t) if hasattr(self.m, "universe_open") else self.m.universe(t)
        mv = []
        for sym in uni[:60]:
            m = self.m.minutes(sym, t)
            if m is None or len(m) < 10:
                continue
            o0, c = float(m["open"].iloc[0]), float(m["close"].iloc[-1])
            f = resample5(m)
            avgv = float(f["volume"].iloc[:-1].mean()) if len(f) > 1 else 0
            mv.append((c / o0 - 1, sym, float(f["volume"].iloc[-1]) / avgv if avgv > 0 else 0))
        if mv:
            mv.sort()
            up = [f"{s} {x:+.1%}" for x, s, _ in reversed(mv[-3:]) if x > 0]
            dn = [f"{s} {x:+.1%}" for x, s, _ in mv[:3] if x < 0]
            if up:
                L.append("Strongest: " + ", ".join(up))
            if dn:
                L.append("Weakest: " + ", ".join(dn))
        net = self.b.day_pnl(self.day) if self.day is not None else 0.0
        L.append(f"Today so far: ₹{net:+,.0f} · open trades {len(self.b.acc.open)}")
        L.append("<i>For your own judgment - not a trade signal.</i>")
        return "\n".join(L)

    def _room(self):
        """₹ a new trade may still risk today: day loss limit - today's loss - risk already open."""
        loss = max(0.0, -self.b.day_pnl(self.day))
        open_risk = sum(max(0.0, (p.avg - p.stop) if p.side == "LONG" else (p.stop - p.avg)) * p.qty
                        for p in self.b.acc.open.values())
        return self.p["day_max_loss"] - loss - open_risk

    def _lib_ctx(self, sym, t, m):
        """Strategy-library view of today's 5-minute candles so far (same code as the strategy search)."""
        from . import strategies_lib as SL
        f = resample5(m)
        if f is None or len(f) < 1:
            return None, None
        o, h, l, c, v = (f[k].values.astype(float) for k in ("open", "high", "low", "close", "volume"))
        end_m = np.array([ts.hour * 60 + ts.minute + 5 for ts in f.index])
        pdh = self.m.prev_day(sym, t) if hasattr(self.m, "prev_day") else None
        pc = self.m.prev_close(sym, t)
        pchg = self.m.prev_change(sym, t) if hasattr(self.m, "prev_change") else None
        return SL.ctx(o, h, l, c, v, end_m, pc, pdh[0] if pdh else None, pdh[1] if pdh else None, pchg,
                      nifty=None if sym == "NIFTY50" else self._nifty_now(t)), f

    def _nifty_now(self, t):
        """(NIFTY's open today, {5-minute candle end: close}) up to t - what rs_divergence compares with."""
        if self._ncache[0] != t:
            n = self.m.minutes("NIFTY50", t)
            val = None
            if n is not None and len(n):
                f = resample5(n)
                val = (float(n["open"].iloc[0]), {ts.hour * 60 + ts.minute + 5: float(v) for ts, v in f["close"].items()})
            self._ncache = (t, val)
        return self._ncache[1]

    def nifty_entry(self, t):
        if self._hm(t) > self.p["opt_last_entry"] or self._open("NIFTY options"):
            return
        if len(self._today_closed("NIFTY options")) >= self.p["opt_max_trades"]:
            return
        multi = [r for r in (self.p.get("opt_strategies") or []) if r[0] in SLIB.NIFTY]
        if multi:                                         # D179: every NIFTY strategy that earned; first to fire
            m = self.m.minutes("NIFTY50", t)
            if m is None or len(m) < 4:
                return
            x, f = self._lib_ctx("NIFTY50", t, m)
            if x is None:
                return
            vx = None
            for row in multi:
                name, stop_f, tgt_f, mask = row[:4]
                mode = row[4] if len(row) > 4 else "cost"
                if int(mask) & 8:
                    vx = vx if vx is not None else self.m.vix_prev(t)
                    if vx is None or vx >= 20:
                        continue
                lg, sh = SLIB.NIFTY[name](x)
                side = "CE" if lg[-1] else "PE" if sh[-1] else None
                if side:
                    return self._buy_option(t, float(f["close"].iloc[-1]), side, name, float(stop_f), float(tgt_f), mode)
            return
        lib = self.p.get("opt_strategy")
        lib = lib if lib and lib != "n_orb" else None
        if not lib and self._hm(t) < self.p["first_entry"]:
            return
        m = self.m.minutes("NIFTY50", t)
        if m is None or len(m) < (4 if lib else 20):
            return
        if lib:                                           # a strategy chosen by the strategy search: it fires from
            if int(self.p["opt_factors"]) & 8:            # the first 5-minute candle, exactly as in the search
                vx = self.m.vix_prev(t)
                if vx is None or vx >= 20:
                    return
            from . import strategies_lib as SL
            x, f = self._lib_ctx("NIFTY50", t, m)
            if x is None:
                return
            lg, sh = SL.NIFTY[lib](x)
            c = float(f["close"].iloc[-1])
            side = "CE" if lg[-1] else "PE" if sh[-1] else None
            return self._buy_option(t, c, side, lib)
        orng = m[m.index < m.index[0].normalize() + timedelta(hours=9, minutes=30)]
        if len(orng) < 10:
            return
        hi, lo, day_open = orng["high"].max(), orng["low"].min(), float(m["open"].iloc[0])
        of = int(self.p["opt_factors"])
        if of & 8:
            vx = self.m.vix_prev(t)
            if vx is None or vx >= 20:
                return
        if of & 1:
            pdh = self.m.prev_day("NIFTY50", t)
            if pdh:
                hi, lo = max(hi, pdh[0]), min(lo, pdh[1])
        f = resample5(m)
        if len(f) < 4:
            return
        c = float(f["close"].iloc[-1])
        ema = float(f["close"].ewm(span=20, adjust=False).mean().iloc[-1])
        side = "CE" if (c > hi and c > ema and c > day_open) else "PE" if (c < lo and c < ema and c < day_open) else None
        return self._buy_option(t, c, side, None)

    def _buy_option(self, t, c, side, lib, stop_f=None, tgt_f=None, mode=None):
        if side is None:
            return
        k = self.m.option(c, side, t)
        if k is None:
            return
        px = self.m.price(k["symbol"], t)
        if not px or px <= 1:
            return
        stop_f = self.p["opt_stop"] if stop_f is None else stop_f
        tgt_f = self.p["opt_target"] if tgt_f is None else tgt_f
        stop, tgt = px * (1 - stop_f), px * (1 + tgt_f)
        lot = k["lot"]
        lots = int(min(min(self.p["opt_risk"], self._room()) / ((px - stop) * lot),
                       self.b.available() * 0.95 / (px * 1.003 * lot)))
        if lots < 1:
            return
        pos = self.b.open_position(f"OPT-{k['symbol']}-{t:%H%M}", k["name"], k["symbol"], "OPT", "LONG", lots * lot, px,
                                   stop, tgt, "NIFTY options", t, lots=lots,
                                   note=(f"NIFTY {c:,.0f}: {lib} signal" if lib else
                                         f"NIFTY {c:,.0f} {'above' if side == 'CE' else 'below'} 9:15-9:30 range"))
        if pos:
            pos.expiry = str(k.get("expiry") or "")
            pos.exit_mode = mode or self.p.get("opt_exit") or ""
            pos.r_frac = float(stop_f)
            self.b.save()
            if self.p["opt_scale"]:
                pos.t1, pos.book_frac = round(px * (1 + self.p["opt_stop"]), 2), float(self.p["opt_scale"])
                self.b.save()
            self.notify("entry", self.entry_text(pos))

    # ---------------------------------------------------------------- stocks
    def stock_entries(self, t):
        lib = self.p.get("stk_strategy")
        if self._hm(t) > (self.p["stk_last_entry"] if not lib or lib == "orb" else "14:05"):
            return
        if (not lib or lib == "orb") and self._hm(t) < self.p["first_entry"]:
            return
        opened, done = self._open("stocks"), self._today_closed("stocks")
        if len(opened) >= self.p["stk_max_open"] or len(opened) + len(done) >= self.p["stk_max_trades"]:
            return
        traded = {p.symbol for p in opened} | {c["symbol"] for c in done}
        cands = []
        if lib and lib != "orb":                          # a strategy chosen by the strategy search
            from . import strategies_lib as SL
            uni = self.m.universe_open(t) if hasattr(self.m, "universe_open") else self.m.universe(t)
            for sym in uni[: self.p["universe"]]:
                if sym in traded:
                    continue
                m = self.m.minutes(sym, t)
                if m is None or len(m) < 5:
                    continue
                x, f = self._lib_ctx(sym, t, m)
                if x is None:
                    continue
                if lib == "rules":                        # D179: any strategy, in the market conditions it earned in
                    for name, tgt, al, vb in self._rules(t):
                        sig = SL.first_signal(SL.STOCK[name], x)
                        if sig and sig[0] == len(f) - 1 and self._cond(t, sig[1]) == (al, vb):
                            cands.append((float(x["strength"][-1]), sym, "LONG" if sig[1] else "SHORT",
                                          float(f["close"].iloc[-1]), float(tgt),
                                          f"{name} · {SL.ALIGN[al]} · {SL.VIXB[vb]}"))
                            break
                    continue
                sig = SL.first_signal(SL.STOCK[lib], x)
                if sig and sig[0] == len(f) - 1:          # today's FIRST signal, on the candle that just closed
                    cands.append((float(x["strength"][-1]), sym, "LONG" if sig[1] else "SHORT", float(f["close"].iloc[-1])))
        for sym in ([] if (lib and lib != "orb") else self.m.universe(t)[: self.p["universe"]]):
            if sym in traded:
                continue
            m = self.m.minutes(sym, t)
            if m is None or len(m) < 20:
                continue
            orng = m[m.index < m.index[0].normalize() + timedelta(hours=9, minutes=30)]
            if len(orng) < 10:
                continue
            prev = self.m.prev_close(sym, t)
            if prev and abs(float(m["open"].iloc[0]) / prev - 1) > self.p["stk_max_gap"]:
                continue
            f = resample5(m)
            if len(f) < 4:
                continue
            c, v = float(f["close"].iloc[-1]), float(f["volume"].iloc[-1])
            avgv = float(f["volume"].iloc[:-1].mean()) if len(f) > 1 else 0
            vwap = float((m["close"] * m["volume"]).sum() / m["volume"].sum()) if m["volume"].sum() > 0 else c
            hi, lo = orng["high"].max(), orng["low"].min()
            strength = v / avgv if avgv > 0 else 0
            if strength < self.p["stk_vol_mult"]:
                continue
            side = "LONG" if (c > hi and c > vwap) else "SHORT" if (c < lo and c < vwap and self.p["stk_sides"] == "both") else None
            if side and self.factors_ok(sym, side, c, float(m["open"].iloc[0]), t):
                cands.append((strength, sym, side, c))
        for cand in sorted(cands, key=lambda z: -z[0]):
            strength, sym, side, c = cand[:4]
            tgt_f = cand[4] if len(cand) > 4 else self.p["stk_target"]
            why = cand[5] if len(cand) > 5 else None
            opened = self._open("stocks")
            if len(opened) >= self.p["stk_max_open"] or len(opened) + len(self._today_closed("stocks")) >= self.p["stk_max_trades"]:
                break
            px = self.m.price(sym, t) or c
            stop = px * (1 - self.p["stk_stop"]) if side == "LONG" else px * (1 + self.p["stk_stop"])
            tgt = px * (1 + tgt_f) if side == "LONG" else px * (1 - tgt_f)
            from .paper import MIS_MARGIN
            mr = None
            if hasattr(self.m, "margin_ratio"):
                mr = self.m.margin_ratio(sym, px, "BUY" if side == "LONG" else "SELL")
            mr = mr if mr and 0.05 <= mr <= 1.0 else MIS_MARGIN          # Kite's own figure, else the cautious 25%
            qty = int(min(min(self.p["stk_risk"], self._room()) / (px * self.p["stk_stop"]),
                          self.b.available() * 0.95 / (px * mr)))
            if qty < 1:
                continue
            pos = self.b.open_position(f"EQ-{sym}-{t:%H%M}", sym, sym, "EQ", side, qty, px, stop, tgt, "stocks", t,
                                       note=(why or f"{lib} signal" if lib and lib != "orb" else
                                             f"5-day rule (learning, small size): broke the 9:15-9:30 range "
                                             f"{'up' if side == 'LONG' else 'down'} with {strength:.1f}x volume")
                                       + f" · margin {mr * 100:.0f}%", margin=mr)
            if pos and self.p["stk_scale"]:
                r = self.p["stk_stop"]
                pos.t1 = round(pos.avg * (1 + r) if side == "LONG" else pos.avg * (1 - r), 2)
                pos.book_frac = float(self.p["stk_scale"])
                self.b.save()
            if pos:
                self.notify("entry", self.entry_text(pos))

    def factors_ok(self, sym, side, c, open0, t):
        f = int(self.p["stk_factors"])
        if not f:
            return True
        lng = side == "LONG"
        pdh = self.m.prev_day(sym, t)
        if f & 1 and pdh and not ((lng and c > pdh[0]) or (not lng and c < pdh[1])):
            return False
        if f & 16 and pdh:
            res = pdh[0] if lng else pdh[1]
            if (lng and c < res < c * 1.01) or (not lng and c * 0.99 < res < c):
                return False
        if f & (2 | 4):
            n = self.m.minutes("NIFTY50", t)
            if n is None or not len(n):
                return False
            nopen, nc = float(n["open"].iloc[0]), float(n["close"].iloc[-1])
            if f & 2 and not ((lng and nc > nopen) or (not lng and nc < nopen)):
                return False
            if f & 4 and not ((lng and c / open0 > nc / nopen) or (not lng and c / open0 < nc / nopen)):
                return False
        if f & 8:
            vx = self.m.vix_prev(t)
            if vx is None or vx >= 20:
                return False
        return True

    # ---------------------------------------------------------------- messages
    @staticmethod
    def entry_text(p):
        act = "BUY" if p.side == "LONG" else "SELL (short)"
        lots = f" ({p.lots} lot{'s' if p.lots > 1 else ''})" if p.lots else ""
        risk = abs(p.avg - p.stop) * p.qty
        opt = p.kind == "OPT"
        sym = str(p.symbol).split(":")[-1]
        far = p.avg * (1.10 if opt else 1.005) if p.side == "LONG" else p.avg * 0.995
        return (f"{'🟢' if p.side == 'LONG' else '🔻'} <b>{act} {p.name}</b>\n"
                f"Kite: <code>{sym}</code> · {'NFO, NRML or MIS' if opt else 'NSE, MIS (intraday)'}\n"
                f"Qty {p.qty}{lots} at ≈ ₹{p.avg:,.2f}\nStop-loss ₹{p.stop:,.2f} · Target ₹{p.target:,.2f}\n"
                f"Risk ≈ ₹{risk:,.0f} · {p.note}\n"
                + (f"Plan: book {p.book_frac:.0%} at ₹{p.t1:,.2f} (1R), stop to cost, rest to ₹{p.target:,.2f}\n" if p.t1 else "")
                + f"⚠️ Right after the order fills, place an SL order at ₹{p.stop:,.2f} in Kite. "
                f"Skip it if the price is already {'above' if p.side == 'LONG' else 'below'} ₹{far:,.2f}.\n"
                "<i>Signal only - ATLAS places no orders. Exit when I message.</i>")

    @staticmethod
    def exit_text(c):
        icon = "🎯" if c["why"] == "target" else "🔴" if c["net"] < 0 else "⏹"
        act = "SELL" if c["side"] == "LONG" else "BUY back"
        return (f"{icon} <b>{act} {c['name']} NOW</b> (at market) - {c['why']}\nQty {c['qty']} · buy ₹{c['buy_avg']:,.2f} → sell "
                f"₹{c['sell_avg']:,.2f}\nP&L ₹{c['pnl']:+,.2f} (after charges ₹{c['net']:+,.2f})")
