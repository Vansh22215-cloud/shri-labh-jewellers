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


class Engine:
    def __init__(self, broker, market, params=None, notify=None):
        self.b, self.m = broker, market
        self.p = dict(P, **(params or {}))
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
            self.day, self.locked = t.normalize(), None
        self.manage(t)
        if self._hm(t) >= self.p["square_off"]:
            return
        net = self.b.day_pnl(self.day)
        if self.locked is None and (net >= self.p["day_target"] or net <= -self.p["day_max_loss"]):
            self.locked = "target" if net > 0 else "loss limit"
            self.notify("status", f"🔒 Day {'target reached' if net > 0 else 'loss limit hit'} (net ₹{net:,.0f}) - no new "
                                  "trades today.")
        if self.locked:
            return
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
            be = self.p["opt_be"] if pos.kind == "OPT" else self.p["stk_be"]
            if long and h >= pos.avg * (1 + be) and pos.stop < pos.avg:
                pos.stop = round(pos.avg, 2)
                self.b.save()
            if not long and l <= pos.avg * (1 - be) and pos.stop > pos.avg:
                pos.stop = round(pos.avg, 2)
                self.b.save()

    # ---------------------------------------------------------------- NIFTY options
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
        return SL.ctx(o, h, l, c, v, end_m, pc, pdh[0] if pdh else None, pdh[1] if pdh else None, pchg), f

    def nifty_entry(self, t):
        if self._hm(t) > self.p["opt_last_entry"] or self._open("NIFTY options"):
            return
        if len(self._today_closed("NIFTY options")) >= self.p["opt_max_trades"]:
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

    def _buy_option(self, t, c, side, lib):
        if side is None:
            return
        k = self.m.option(c, side, t)
        if k is None:
            return
        px = self.m.price(k["symbol"], t)
        if not px or px <= 1:
            return
        stop, tgt = px * (1 - self.p["opt_stop"]), px * (1 + self.p["opt_target"])
        lot = k["lot"]
        lots = int(min(self.p["opt_risk"] / ((px - stop) * lot), self.b.available() * 0.95 / (px * 1.003 * lot)))
        if lots < 1:
            return
        pos = self.b.open_position(f"OPT-{k['symbol']}-{t:%H%M}", k["name"], k["symbol"], "OPT", "LONG", lots * lot, px,
                                   stop, tgt, "NIFTY options", t, lots=lots,
                                   note=(f"NIFTY {c:,.0f}: {lib} signal" if lib else
                                         f"NIFTY {c:,.0f} {'above' if side == 'CE' else 'below'} 9:15-9:30 range"))
        if pos:
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
        for strength, sym, side, c in sorted(cands, reverse=True):
            opened = self._open("stocks")
            if len(opened) >= self.p["stk_max_open"] or len(opened) + len(self._today_closed("stocks")) >= self.p["stk_max_trades"]:
                break
            px = self.m.price(sym, t) or c
            stop = px * (1 - self.p["stk_stop"]) if side == "LONG" else px * (1 + self.p["stk_stop"])
            tgt = px * (1 + self.p["stk_target"]) if side == "LONG" else px * (1 - self.p["stk_target"])
            from .paper import MIS_MARGIN
            mr = None
            if hasattr(self.m, "margin_ratio"):
                mr = self.m.margin_ratio(sym, px, "BUY" if side == "LONG" else "SELL")
            mr = mr if mr and 0.05 <= mr <= 1.0 else MIS_MARGIN          # Kite's own figure, else the cautious 25%
            qty = int(min(self.p["stk_risk"] / (px * self.p["stk_stop"]), self.b.available() * 0.95 / (px * mr)))
            if qty < 1:
                continue
            pos = self.b.open_position(f"EQ-{sym}-{t:%H%M}", sym, sym, "EQ", side, qty, px, stop, tgt, "stocks", t,
                                       note=f"broke the 9:15-9:30 range {'up' if side == 'LONG' else 'down'} with "
                                            f"{strength:.1f}x volume · margin {mr * 100:.0f}%", margin=mr)
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
        return (f"{'🟢' if p.side == 'LONG' else '🔻'} <b>{act} {p.name}</b> · Intraday\n"
                f"Qty {p.qty}{lots} at ≈ ₹{p.avg:,.2f}\nStop-loss ₹{p.stop:,.2f} · Target ₹{p.target:,.2f}\n"
                f"Risk ≈ ₹{risk:,.0f} · {p.note}\n"
                + (f"Plan: book {p.book_frac:.0%} at ₹{p.t1:,.2f} (1R), stop to cost, rest to ₹{p.target:,.2f}\n" if p.t1 else "")
                + "<i>Practice account - place it yourself if you want it.</i>")

    @staticmethod
    def exit_text(c):
        icon = "🎯" if c["why"] == "target" else "🔴" if c["net"] < 0 else "⏹"
        act = "SELL" if c["side"] == "LONG" else "BUY back"
        return (f"{icon} <b>{act} {c['name']}</b> - {c['why']}\nQty {c['qty']} · buy ₹{c['buy_avg']:,.2f} → sell "
                f"₹{c['sell_avg']:,.2f}\nP&L ₹{c['pnl']:+,.2f} (after charges ₹{c['net']:+,.2f})")
