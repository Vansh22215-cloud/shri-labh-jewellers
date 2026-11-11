"""LIVE MARKET ENGINE (owner's design, DECISIONS D95): one background engine that runs from 09:15 to 15:30 on market
days and keeps scanning the WHOLE market on Zerodha data, then sends only the best trades, ranked 1-10.

  Universe   ~400 most-traded NSE stocks + every F&O stock + Nifty / Bank Nifty.
  Candles    Kite 5-minute candles fetched in a continuous rotation (~2.5 requests a second - Kite's limit is 3), so
             every stock is refreshed every few minutes; each refresh is scanned at once.
  Quotes     live quotes for the whole universe every 30 seconds (2 requests) - for exit alerts and option premiums.
  Intraday   opening-range breakout, bull/bear flag, oversold bounce, VWAP reclaim/rejection - only on the bar that
             just closed (no look-ahead), the same code that the weekly Kite-history test checks.
  Normal     the system's own swing strategy (a3) on live prices, every 15 minutes (provisional until the close) and
             the confirmed evening tips.
  F&O        option BUYING only: for F&O stocks/indices with a strong setup, the near strike in the trade's direction
             (nearest monthly expiry with >= 3 days left; weekly for indices), live premium, liquidity check
             (open interest, spread), targets from the stock's targets repriced with the option's own implied
             volatility, stop-loss on the SPOT on a 75-minute candle close; skipped if the loss at the stop is more
             than the rank allows.
  RANK 1-10  back-tested edge of the setup + Time Machine (10,000 replays) + trend on daily bars + relative volume +
             chart-pattern confluence (the system's pattern library) + reward:risk + liquidity. Only rank >= 6 is sent.
  Risk       by rank (owner: "according to the setup quality"): stocks 1% / 1.5% / 2% of capital for rank 6 / 7-8 /
             9-10; options 2% / 3% / 5%.
Every sent tip is stored in journal/live_tips.csv and followed: targets, stop-loss (F&O: spot SL on 75-minute
candle closes, premium targets) and the 3:15 pm intraday square-off - each sent once as an exit alert.
Nothing is ever ordered by the system; the owner places every order in the Kite app.
"""
import json
import threading
import time
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from .config import DATA, JOURNAL, get_logger, load_settings

log = get_logger()
TIPS_F = JOURNAL / "live_tips.csv"
NFO_F = DATA / "kite_instruments_nfo.csv"
CB75 = [(10, 30), (11, 45), (13, 0), (14, 15), (15, 30)]        # 75-minute candle closes (IST)
WORD = {"ORB": "opening-range breakout", "FLAG": "flag breakout", "BOUNCE": "oversold bounce",
        "VWAP": "VWAP reclaim", "SWING": "swing setup"}


def now_ist():
    return pd.Timestamp.now(tz="Asia/Kolkata").tz_localize(None)


# ----------------------------------------------------------------------------- universe and instruments
def universe(n=400):
    """Most-traded stocks (latest liquidity ranking) + F&O underlyings + the two big indices."""
    syms = []
    try:
        u = pd.read_csv(DATA / "universe_history.csv")
        last = u[u["asof"] == u["asof"].max()].sort_values("rank")
        syms = [str(s) for s in last["symbol"].head(n)]
    except Exception:
        from .archive import intraday_universe
        syms = intraday_universe()
    fno = sorted(fno_underlyings())
    return list(dict.fromkeys(["NIFTY50", "BANKNIFTY"] + syms + [s for s in fno if s not in ("NIFTY", "BANKNIFTY")]))


def nfo():
    """Kite's NFO instrument list (all futures and options), refreshed once a day."""
    from . import kite
    if NFO_F.exists() and (time.time() - NFO_F.stat().st_mtime) < 20 * 3600:
        return pd.read_csv(NFO_F, parse_dates=["expiry"])
    import io
    r = kite._get("/instruments/NFO", timeout=90)
    df = pd.read_csv(io.StringIO(r.text))
    df = df[df["segment"] == "NFO-OPT"][["tradingsymbol", "name", "expiry", "strike", "lot_size", "instrument_type"]]
    df.to_csv(NFO_F, index=False)
    df["expiry"] = pd.to_datetime(df["expiry"])
    return df


def fno_underlyings():
    try:
        return set(nfo()["name"].astype(str))
    except Exception:
        return set()


# ----------------------------------------------------------------------------- ranking
def _setup_stats():
    try:
        return json.loads((DATA / "intraday_setups.json").read_text()).get("stats", {})
    except Exception:
        return {}


def daily_context(sym):
    """Daily trend, liquidity and the pattern library's verdict for one stock (cached for the day)."""
    from . import data_prices
    out = {"trend_long": 0.5, "trend_short": 0.5, "value_cr": None, "patterns": 0, "bear_candles": 0, "bull_candles": 0}
    try:
        df = data_prices.load(sym)
        if df is None or len(df) < 210:
            return out
        c = df["close"]
        s50, s200, px = c.rolling(50).mean().iloc[-1], c.rolling(200).mean().iloc[-1], float(c.iloc[-1])
        out["trend_long"] = 1.0 if px > s50 > s200 else 0.6 if px > s200 else 0.2
        out["trend_short"] = 1.0 if px < s50 < s200 else 0.6 if px < s200 else 0.2
        out["value_cr"] = float((df["close"] * df["volume"]).tail(60).median()) / 1e7
        from .chart_reader import own_patterns
        fired, candles = own_patterns(df)
        out["patterns"] = len(fired or [])
        out["bull_candles"] = sum(1 for x in candles or [] if x.startswith("bullish"))
        out["bear_candles"] = sum(1 for x in candles or [] if x.startswith("bearish"))
    except Exception as e:
        log.warning("daily context %s: %s", sym, type(e).__name__)
    return out


def rank(c, ctx, tm=None, stats=None):
    """1-10 from the parts below (each 0..1) - weights fixed in advance, not fitted."""
    stats = stats if stats is not None else _setup_stats()
    long_ = c["side"] == "buy"
    st = stats.get(c["setup"], {})
    if c["setup"] == "SWING":
        edge = 0.65                                  # the research-tested strategy (beat earlier versions, D77-D78)
    elif st:
        edge = float(np.clip(0.5 + (st.get("avg_net") or 0) / 400, 0, 1)) * (1.0 if st.get("allowed") else 0.6)
    else:
        edge = 0.45                                  # not yet tested on Kite history
    tm_p = 0.5 if not tm else float(np.clip(0.5 + (tm["target"] - tm["stop"]) / 100, 0, 1))
    trend = ctx["trend_long"] if long_ else ctx["trend_short"]
    vol = float(np.clip((c.get("rel_vol") or 1.0) / 2.0, 0, 1))
    pat = float(np.clip((ctx["patterns"] if long_ else 0) / 3 + (ctx["bull_candles"] if long_ else ctx["bear_candles"]) * 0.2
                        - (ctx["bear_candles"] if long_ else ctx["bull_candles"]) * 0.2, 0, 1))
    risk = abs(c["entry"] - c["stop"])
    rr = float(np.clip((abs(c["targets"][min(1, len(c["targets"]) - 1)] - c["entry"]) / risk) / 3 if risk else 0, 0, 1))
    v = ctx.get("value_cr")
    liq = 1.0 if v is None else 1.0 if v >= 50 else 0.7 if v >= 10 else 0.3
    score = 0.20 * edge + 0.20 * tm_p + 0.15 * trend + 0.15 * vol + 0.10 * pat + 0.10 * rr + 0.10 * liq
    return int(np.clip(round(1 + 9 * score), 1, 10)), {"edge": edge, "time_machine": tm_p, "trend": trend,
                                                       "volume": vol, "patterns": pat, "reward_risk": rr, "liquidity": liq}


def gates(c, ctx, tm, stats=None):
    """Hard quality gates BEFORE ranking (owner: 'only the best setups'). -> (passed, reason if not)."""
    stats = stats if stats is not None else _setup_stats()
    long_ = c["side"] == "buy"
    if (ctx["trend_long"] if long_ else ctx["trend_short"]) < 0.6:
        return False, "against the daily trend"
    if c["setup"] != "SWING" and (c.get("rel_vol") or 0) < 1.5:
        return False, "no volume behind the move"
    if tm and tm["target"] < tm["stop"]:
        return False, "Time Machine: the stop comes first more often"
    st = stats.get(c["setup"])
    if st and not st.get("allowed") and c["setup"] != "SWING":
        return "strict", "setup failed the Kite-history test"
    return True, ""


def risk_pct(r, kind):
    if kind == "FNO":
        return 5.0 if r >= 9 else 3.0 if r >= 7 else 2.0
    return 2.0 if r >= 9 else 1.5 if r >= 7 else 1.0


# ----------------------------------------------------------------------------- intraday setups on live candles
def vwap_signal(b):
    """Price closes back above VWAP after >= 6 bars below it, on above-average volume (long); mirror for short."""
    if len(b) < 10:
        return []
    tp = (b["high"] + b["low"] + b["close"]) / 3
    vw = (tp * b["volume"]).cumsum() / b["volume"].replace(0, np.nan).cumsum()
    last, prev = b.iloc[-1], b.iloc[-2]
    av = b["volume"].iloc[-21:-1].mean()
    below = (b["close"].iloc[-8:-1] < vw.iloc[-8:-1]).sum() >= 6
    above = (b["close"].iloc[-8:-1] > vw.iloc[-8:-1]).sum() >= 6
    out = []
    if below and prev["close"] < vw.iloc[-2] and last["close"] > vw.iloc[-1] and last["volume"] > av:
        stop = float(b["low"].iloc[-6:].min())
        e = float(last["close"])
        if e > stop:
            out.append({"setup": "VWAP", "side": "buy", "entry_time": b.index[-1], "entry": e, "stop": stop,
                        "target": e + 1.5 * (e - stop)})
    if above and prev["close"] > vw.iloc[-2] and last["close"] < vw.iloc[-1] and last["volume"] > av:
        stop = float(b["high"].iloc[-6:].max())
        e = float(last["close"])
        if stop > e:
            out.append({"setup": "VWAP", "side": "sell", "entry_time": b.index[-1], "entry": e, "stop": stop,
                        "target": e - 1.5 * (stop - e)})
    return out


def intraday_candidates(sym, bars, prev_close, now):
    """Setups that triggered on the bar that JUST closed (completed bars only)."""
    from .intraday_paper import signals
    today = bars[bars.index.normalize() == now.normalize()]
    today = today[today.index + pd.Timedelta(minutes=5) <= now]
    if len(today) < 4:
        return []
    out = []
    last_ts = today.index[-1]
    for sg in signals(today, prev_close) + vwap_signal(today):
        if pd.Timestamp(sg["entry_time"]) != last_ts:
            continue
        r = abs(sg["entry"] - sg["stop"])
        if r <= 0 or r / sg["entry"] < 0.002:
            continue
        sgn = 1 if sg["side"] == "buy" else -1
        sg["targets"] = [round(sg["entry"] + sgn * k * r, 2) for k in (1.0, 2.0, 3.0)]
        av = today["volume"].iloc[-21:-1].mean()
        sg["rel_vol"] = float(today["volume"].iloc[-1] / av) if av else 1.0
        sg["symbol"] = sym
        out.append(sg)
    return out


# ----------------------------------------------------------------------------- F&O (option buying)
def _days_to(expiry, now):
    return max(0.25, (pd.Timestamp(expiry) + pd.Timedelta(hours=15, minutes=30) - now).total_seconds() / 86400)


def option_trade(c, r, spot, now, capital, hold_days=1):
    """Best option to BUY for a stock/index setup c, within the rank's risk. -> dict or None."""
    from . import kite
    from .options_check import bs, implied_vol
    name = {"NIFTY50": "NIFTY", "BANKNIFTY": "BANKNIFTY"}.get(c["symbol"], c["symbol"])
    ins = nfo()
    kind = "CE" if c["side"] == "buy" else "PE"
    o = ins[(ins["name"] == name) & (ins["instrument_type"] == kind)]
    o = o[o["expiry"] >= now.normalize() + pd.Timedelta(days=3)]
    if not len(o):
        return None
    exp = o["expiry"].min()
    o = o[o["expiry"] == exp].sort_values("strike")
    strikes = o["strike"].values
    if not len(strikes):
        return None
    i0 = int(np.argmin(np.abs(strikes - spot)))
    order = [i0 - 1, i0, i0 + 1, i0 + 2] if kind == "CE" else [i0 + 1, i0, i0 - 1, i0 - 2]   # slightly ITM first
    limit = capital * risk_pct(r, "FNO") / 100
    for i in order:
        if i < 0 or i >= len(strikes):
            continue
        row = o.iloc[i]
        ts = str(row["tradingsymbol"])
        try:
            q = kite._get("/quote", params=[("i", f"NFO:{ts}")]).json()["data"].get(f"NFO:{ts}", {})
        except Exception:
            continue
        ltp = float(q.get("last_price") or 0)
        if ltp <= 0 or not q.get("oi"):
            continue
        dep = q.get("depth", {})
        bid = (dep.get("buy") or [{}])[0].get("price") or 0
        ask = (dep.get("sell") or [{}])[0].get("price") or 0
        if not bid or not ask or (ask - bid) / ltp > 0.03:
            continue                                              # too illiquid: wide spread
        t = _days_to(exp, now) / 365
        iv = implied_vol(ltp, spot, float(row["strike"]), t, kind)
        if not iv:
            continue
        t_after = max(1e-4, t - hold_days / 365)
        lot = int(row["lot_size"])
        prem_sl = bs(c["stop"], float(row["strike"]), t_after, iv, kind)
        loss = (ltp - prem_sl) * lot
        cost = ltp * lot
        if loss <= 0 or loss > limit or cost > capital * 0.5:
            continue
        tg = [bs(x, float(row["strike"]), t_after, iv, kind) for x in c["targets"]]
        tg.append(bs(c["targets"][-1] + (c["targets"][-1] - c["entry"]) * 0.5, float(row["strike"]), t_after, iv, kind))
        tg = [x for x in tg if x > ltp * 1.05]
        if len(tg) < 2:
            continue
        return {"contract": ts, "expiry": exp, "strike": float(row["strike"]), "kind": kind, "lot": lot,
                "premium": ltp, "premium_hi": ltp * 1.04, "targets": tg[:4], "spot_sl": c["stop"], "loss": loss,
                "cost": cost, "iv": iv}
    return None


# ----------------------------------------------------------------------------- messages (owner's formats)
def _n(x):
    x = float(x)
    return f"{x:,.0f}" if abs(x) >= 100 else f"{x:,.1f}".rstrip("0").rstrip(".") if abs(x) >= 10 else f"{x:,.2f}"


def fmt_fno(c, opt, r):
    up = opt["kind"] == "CE"
    mon = pd.Timestamp(opt["expiry"]).strftime("%b").upper()
    tg = "-".join(_n(x) for x in opt["targets"]) + "+"
    return (f"• F&O\n\n{'📈' if up else '📉'} {c['symbol'].replace('NIFTY50', 'NIFTY')}\n\n"
            f"🖲 {mon} {_n(opt['strike'])} {opt['kind']} {_n(opt['premium'])}-{_n(opt['premium_hi'])}\n\n"
            f"✅ Target-{tg}\n\n"
            f"⛔️ Stoploss-{_n(opt['spot_sl'])} SPOT (75 Min CB)\n\n"
            f"✨ Lot Size- {opt['lot']}\n\n"
            f"⭐ RANK - {r}/10 · Loss at SL ≈ ₹{opt['loss']:,.0f}/lot · {c.get('why', '')}")


def fmt_intraday(c, r, qty):
    act = "Buy" if c["side"] == "buy" else "Sell"
    return (f"• Intraday\n\n{act} #{c['symbol']} at {_n(c['entry'])} 👍\n\n"
            f"STRICT STOPLOSS {_n(c['stop'])} ❗️❗️\n\n"
            f"Target {'/'.join(_n(x) for x in c['targets'])}\n\n"
            f"INTRADAY TRADE ONLYYY 📊\n\n"
            f"⭐ RANK - {r}/10 · Qty {qty} · {WORD.get(c['setup'], c['setup'])}")


def fmt_normal(c, r, qty, rp, tomorrow=False):
    verb = "Buy tomorrow" if tomorrow else "Bought"
    return (f"• Normal trade\n\n{verb} #{c['symbol']} at {_n(c['entry'])} 📊\n\n"
            f"SL at {_n(c['stop'])} ❗️\n\n"
            f"Target {'/'.join(_n(x) for x in c['targets'])}\n\n"
            f"{rp:g}% Risk\n\n"
            f"⭐ RANK - {r}/10 · Qty {qty}")


# ----------------------------------------------------------------------------- tip store + exits
COLS = ["id", "time", "type", "symbol", "side", "entry", "stop", "targets", "rank", "qty", "contract", "lot",
        "premium", "opt_targets", "spot_sl", "status", "hit", "day"]


_LOCK = threading.RLock()       # the scan loop and the swing pass both write the tip file


def load_tips():
    return pd.read_csv(TIPS_F, dtype={"id": str}) if TIPS_F.exists() else pd.DataFrame(columns=COLS)


def already(sym, typ, day):
    t = load_tips()
    return bool(len(t) and ((t["symbol"] == sym) & (t["type"] == typ) & (t["day"] == day)).any())


def save_tip(row):
    with _LOCK:
        _save_tip(row)


def _save_tip(row):
    t = load_tips()
    row["id"] = f"{len(t) + 1:05d}"
    pd.concat([t, pd.DataFrame([row])], ignore_index=True).to_csv(TIPS_F, index=False)


def send(text, label="trade tip"):
    from . import telegram
    return telegram.send(load_settings(), text, label=label)


def exits(quotes, now, opt_quotes=None, candles=None):
    """Exit alerts for every open tip: targets (one by one), stop-loss, 3:15 pm intraday square-off."""
    with _LOCK:
        return _exits(quotes, now, opt_quotes, candles)


def _exits(quotes, now, opt_quotes=None, candles=None):
    t = load_tips()
    if not len(t):
        return []
    msgs = []
    for i, r in t[t["status"] == "open"].iterrows():
        sym = r["symbol"]
        hit = int(r["hit"] or 0) if pd.notna(r["hit"]) else 0
        if r["type"] == "FNO":
            q = (opt_quotes or {}).get(r["contract"])
            tg = [float(x) for x in str(r["opt_targets"]).split("/") if x]
            if q:
                while hit < len(tg) and q >= tg[hit]:
                    hit += 1
                    msgs.append(f"✅ {sym} {r['contract']} - Target {hit} hit ({_n(tg[hit - 1])}) "
                                f"{'- all targets done, book profit' if hit == len(tg) else '- book part, trail the rest'}")
            closed_75 = [(h, m) for h, m in CB75 if now.hour * 60 + now.minute >= h * 60 + m]
            if closed_75 and candles is not None and sym in candles:
                b = candles[sym]
                h, m = closed_75[-1]
                cut = now.normalize() + pd.Timedelta(hours=h, minutes=m)
                bb = b[(b.index < cut) & (b.index >= cut - pd.Timedelta(minutes=75))]
                if len(bb):
                    cl = float(bb["close"].iloc[-1])
                    sl = float(r["spot_sl"])
                    if (cl < sl) if r["side"] == "buy" else (cl > sl):
                        t.loc[i, "status"] = "stop"
                        msgs.append(f"⛔️ {sym} {r['contract']} - SL: 75-min candle closed at {_n(cl)} beyond {_n(sl)} "
                                    "SPOT. Exit the option.")
                        continue
            if hit >= len(tg) and tg:
                t.loc[i, "status"] = "done"
        else:
            q = quotes.get(sym)
            if not q:
                continue
            px, hi, lo = q["last"], q.get("high", q["last"]), q.get("low", q["last"])
            buy = r["side"] == "buy"
            tg = [float(x) for x in str(r["targets"]).split("/") if x]
            if (lo <= float(r["stop"])) if buy else (hi >= float(r["stop"])):
                t.loc[i, "status"] = "stop"
                msgs.append(f"⛔️ #{sym} - stop-loss {_n(r['stop'])} hit. Exit." +
                            (" (intraday)" if r["type"] == "INTRADAY" else ""))
                continue
            while hit < len(tg) and ((px >= tg[hit]) if buy else (px <= tg[hit])):
                hit += 1
                msgs.append(f"✅ #{sym} - Target {hit} hit ({_n(tg[hit - 1])})" +
                            (" - all targets done, book profit" if hit == len(tg) else " - book part, move SL to cost"))
            if hit >= len(tg):
                t.loc[i, "status"] = "done"
            elif r["type"] == "INTRADAY" and now.hour * 60 + now.minute >= 15 * 60 + 15:
                t.loc[i, "status"] = "squared"
                msgs.append(f"⏰ #{sym} - 3:15 pm: square off the intraday trade now (now {_n(px)}).")
        t.loc[i, "hit"] = hit
    t.to_csv(TIPS_F, index=False)
    for m in msgs:
        send(m, label="exit alert")
    return msgs


# ----------------------------------------------------------------------------- the engine
class Engine:
    def __init__(self):
        self.candles, self.prev, self.quotes, self.ctx = {}, {}, {}, {}
        self.stop_flag = False
        self.last_swing = 0.0
        self.sent = 0
        self.uni = []
        self.fno = set()

    def _ctx(self, sym):
        if sym not in self.ctx:
            self.ctx[sym] = daily_context(sym)
        return self.ctx[sym]

    def _tm(self, c, bars, bars_left):
        from .timemachine import simulate
        try:
            return simulate(bars, c["side"], c["entry"], c["stop"], c["targets"][0], bars_left, lookback=1500)
        except Exception:
            return None

    def consider_intraday(self, c, now, settings):
        day = str(now.date())
        if already(c["symbol"], "INTRADAY", day) and already(c["symbol"], "FNO", day):
            return
        cap = float(settings.get("capital", 45000))
        left = max(1, int(((now.normalize() + pd.Timedelta(hours=15, minutes=15)) - now).total_seconds() // 300))
        tm = self._tm(c, self.candles.get(c["symbol"]), left)
        ok, why = gates(c, self._ctx(c["symbol"]), tm)
        if not ok:
            return
        r, parts = rank(c, self._ctx(c["symbol"]), tm)
        if r < (9 if ok == "strict" else int(settings.get("min_rank", 8))):
            return
        c["why"] = WORD.get(c["setup"], c["setup"])
        if c["symbol"] not in ("NIFTY50", "BANKNIFTY") and not already(c["symbol"], "INTRADAY", day) \
                and now.hour * 60 + now.minute <= 14 * 60 + 30:
            per = abs(c["entry"] - c["stop"])
            qty = int(min(cap * risk_pct(r, "EQ") / 100 / per, cap / c["entry"]))
            if qty >= 1:
                send(fmt_intraday(c, r, qty))
                save_tip({"time": str(now)[:16], "type": "INTRADAY", "symbol": c["symbol"], "side": c["side"],
                          "entry": c["entry"], "stop": c["stop"], "targets": "/".join(f"{x:.2f}" for x in c["targets"]),
                          "rank": r, "qty": qty, "status": "open", "hit": 0, "day": day})
                self.sent += 1
        if (c["symbol"] in self.fno or c["symbol"] in ("NIFTY50", "BANKNIFTY")) and not already(c["symbol"], "FNO", day):
            self.consider_fno(c, r, now, settings, hold_days=1)

    def consider_fno(self, c, r, now, settings, hold_days=1):
        day = str(now.date())
        spot = (self.quotes.get(c["symbol"]) or {}).get("last") or c["entry"]
        try:
            opt = option_trade(c, r, spot, now, float(settings.get("capital", 45000)), hold_days)
        except Exception as e:
            log.warning("option build %s failed: %s", c["symbol"], type(e).__name__)
            opt = None
        if not opt:
            return
        send(fmt_fno(c, opt, r))
        save_tip({"time": str(now)[:16], "type": "FNO", "symbol": c["symbol"], "side": c["side"], "entry": c["entry"],
                  "stop": c["stop"], "targets": "/".join(f"{x:.2f}" for x in c["targets"]), "rank": r, "qty": 1,
                  "contract": opt["contract"], "lot": opt["lot"], "premium": round(opt["premium"], 2),
                  "opt_targets": "/".join(f"{x:.2f}" for x in opt["targets"]), "spot_sl": opt["spot_sl"],
                  "status": "open", "hit": 0, "day": day})
        self.sent += 1

    def swing_pass(self, now, settings):
        """The system's own swing strategy on live prices (provisional), as Normal trades."""
        from . import live_scan
        try:
            live_scan.run(send=False)
        except Exception as e:
            log.warning("engine swing pass failed: %s", type(e).__name__)
            return
        day = str(now.date())
        cap = float(settings.get("capital", 45000))
        for pl in live_scan.LAST_FORMING:
            sym = pl["symbol"]
            if already(sym, "NORMAL", day):
                continue
            c = {"symbol": sym, "side": "buy", "setup": "SWING", "entry": float(pl["ltp"]), "stop": float(pl["stop"]),
                 "targets": [float(pl["target1"]), float(pl.get("target2") or pl["target1"])], "rel_vol": 1.0}
            from . import data_prices
            tm = None
            try:
                from .timemachine import simulate
                tm = simulate(data_prices.load(sym), "buy", c["entry"], c["stop"], c["targets"][0],
                              int(load_settings().get("swing_hold_days", 25)))
            except Exception:
                pass
            ok, _w = gates(c, self._ctx(sym), tm)
            if not ok:
                continue
            r, _ = rank(c, self._ctx(sym), tm)
            if r < int(settings.get("min_rank", 8)):
                continue
            rp = risk_pct(r, "EQ")
            qty = int(min(cap * rp / 100 / max(1e-9, c["entry"] - c["stop"]), cap * 0.25 / c["entry"]))
            if qty < 1:
                continue
            send(fmt_normal(c, r, qty, rp))
            save_tip({"time": str(now)[:16], "type": "NORMAL", "symbol": sym, "side": "buy", "entry": c["entry"],
                      "stop": c["stop"], "targets": "/".join(f"{x:.2f}" for x in c["targets"]), "rank": r, "qty": qty,
                      "status": "open", "hit": 0, "day": day})
            self.sent += 1
            if sym in self.fno and r >= 7 and not already(sym, "FNO", day):
                c["why"] = "swing setup"
                self.consider_fno(c, r, now, settings, hold_days=5)

    def refresh_quotes(self):
        from . import kite
        q = kite.quotes(self.uni)
        if q:
            self.quotes.update(q)
            for s, v in q.items():
                if v.get("prev"):
                    self.prev.setdefault(s, v["prev"])
        opt = {}
        t = load_tips()
        if len(t):
            con = t.loc[(t["status"] == "open") & (t["type"] == "FNO"), "contract"].dropna().astype(str).tolist()
            if con:
                try:
                    d = kite._get("/quote/ltp", params=[("i", f"NFO:{x}") for x in con]).json()["data"]
                    opt = {x: float(d[f"NFO:{x}"]["last_price"]) for x in con if f"NFO:{x}" in d}
                except Exception:
                    pass
        return opt

    def run(self, until=None):
        """Main loop (background thread). Ends at 15:31 or when stop_flag is set."""
        from . import kite
        settings = load_settings()
        self.uni = universe()
        t = load_tips()
        if len(t):   # stocks of still-open tips are always watched (exit alerts)
            self.uni += [x for x in t.loc[t["status"] == "open", "symbol"].astype(str) if x not in self.uni]
        self.fno = fno_underlyings()
        log.info("Live engine: %d stocks in the universe, %d F&O underlyings, prices: %s", len(self.uni),
                 len(self.fno), "Zerodha" if kite.logged_in() else "Yahoo (not logged in)")
        i, last_q = 0, 0.0
        while not self.stop_flag:
            now = now_ist()
            if until is not None and now >= until:
                break
            m = now.hour * 60 + now.minute
            if m > 15 * 60 + 31:
                break
            if time.time() - last_q >= 30:
                last_q = time.time()
                try:
                    oq = self.refresh_quotes()
                    exits(self.quotes, now, oq, self.candles)
                except Exception as e:
                    log.warning("engine quotes/exits: %s", type(e).__name__)
            if m >= 9 * 60 + 20 and time.time() - self.last_swing >= 900:
                self.last_swing = time.time()
                threading.Thread(target=self.swing_pass, args=(now, settings), daemon=True).start()
            if not kite.logged_in():
                time.sleep(20)
                continue
            sym = self.uni[i % len(self.uni)]
            i += 1
            try:
                h = kite.historical(sym, "5minute", days=4)
                if h is not None and len(h):
                    h.index = pd.to_datetime(h.index)
                    h.index = h.index.tz_localize(None) if h.index.tz is not None else h.index
                    self.candles[sym] = h
                    days = sorted(set(h.index.normalize()))
                    if len(days) >= 2 and sym not in self.prev:
                        self.prev[sym] = float(h[h.index.normalize() == days[-2]]["close"].iloc[-1])
                    if 9 * 60 + 35 <= m <= 15 * 60 + 15:
                        for c in intraday_candidates(sym, h, self.prev.get(sym), now):
                            self.consider_intraday(c, now, settings)
            except Exception as e:
                log.warning("engine scan %s: %s", sym, type(e).__name__)
            time.sleep(0.4)
        log.info("Live engine stopped: %d tips sent today", self.sent)


_ENGINE = {"thread": None, "engine": None}


def ensure_running(now=None):
    """Start the engine thread on market days 09:14-15:30 if it is not running (called every minute by the daemon)."""
    now = now or now_ist()
    m = now.hour * 60 + now.minute
    if now.weekday() >= 5 or not (9 * 60 + 14 <= m <= 15 * 60 + 30):
        return False
    th = _ENGINE["thread"]
    if th is not None and th.is_alive():
        return True
    e = Engine()
    th = threading.Thread(target=e.run, daemon=True)
    _ENGINE.update(thread=th, engine=e)
    th.start()
    return True


def evening_tips(plans, day, settings=None):
    """The confirmed evening tips, sent as Normal trades in the owner's format (Buy tomorrow ...)."""
    s = settings or load_settings()
    cap = float(s.get("capital", 45000))
    out = 0
    for pl in plans:
        sym = pl["symbol"]
        if already(sym, "NORMAL", str(day)):
            continue
        entry = round((pl["entry_low"] + pl["entry_high"]) / 2, 2)
        c = {"symbol": sym, "side": "buy", "setup": "SWING", "entry": entry, "stop": float(pl["stop"]),
             "targets": [float(pl["target1"]), float(pl.get("target2") or pl["target1"])], "rel_vol": 1.0}
        tm = None
        try:
            from . import data_prices
            from .timemachine import simulate
            tm = simulate(data_prices.load(sym), "buy", entry, c["stop"], c["targets"][0], 25)
        except Exception:
            pass
        ctx = daily_context(sym)
        ok, _w = gates(c, ctx, tm)
        if not ok:
            continue
        r, _ = rank(c, ctx, tm)
        if r < int(s.get("min_rank", 8)):
            continue
        rp = risk_pct(r, "EQ")
        qty = int(min(cap * rp / 100 / max(1e-9, entry - c["stop"]), cap * 0.25 / entry))
        if qty < 1:
            continue
        send(fmt_normal(c, r, qty, rp, tomorrow=True))
        save_tip({"time": str(now_ist())[:16], "type": "NORMAL", "symbol": sym, "side": "buy", "entry": entry,
                  "stop": c["stop"], "targets": "/".join(f"{x:.2f}" for x in c["targets"]), "rank": r, "qty": qty,
                  "status": "open", "hit": 0, "day": str(day)})
        out += 1
    return out
