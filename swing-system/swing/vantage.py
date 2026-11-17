"""VANTAGE INDICATOR scanner (owner 17 Nov): the exact VANTAGE AI logic (vantage-ai/validation/replica.py = the Pine
core, tested on 13 years of NSE data) run on EVERY NSE equity right after the daily close; each new BUY - and later
the SELL for every BUY it sent - goes to Telegram:

    #VANTAGE INDICATOR

    #TITAN

    🟢 BUY · Dip-buy A · likely win 80% ...

When: 3:40 pm on trading days with today's candle from Kite (exact, minutes after the close). Not logged in to Kite
-> retried at 6:50 pm with Yahoo's daily candle. A stock is skipped (never guessed) when its price history is stale.
Every signal is recorded BEFORE it is sent (data/private/vantage_signals.csv) and sent once.
"""
import json
import sys
from multiprocessing import get_context

import numpy as np
import pandas as pd

from .config import DATA, PRIVATE, ROOT, get_logger, load_settings

log = get_logger()
REPLICA_DIR = ROOT.parent / "vantage-ai" / "validation"
SIGNALS_F = PRIVATE / "vantage_signals.csv"
LAST_F = DATA / "vantage_last.json"
BARS = 900                      # 260 warm-up + 52-week high + state convergence (positions last <= 60 days)
_BENCH = None


def _replica():
    if str(REPLICA_DIR) not in sys.path:
        sys.path.insert(0, str(REPLICA_DIR))
    import replica
    return replica


def calibration():
    """Likely-win % per signal type, from the 13-year test (the same numbers the TradingView indicator shows)."""
    try:
        cal = json.load(open(REPLICA_DIR / "results_final.json"))["Fixed risk/reward"]["calibration"]
    except Exception:
        cal = {}
    return cal


def likely(cal, setup, tier, score):
    if setup == "Dip-buy":
        k = f"Dip-buy {tier}"
    elif setup == "Breakout":
        k = "Breakout 90+" if score >= 90 else "Breakout 80-89" if score >= 80 else "Breakout 70-79"
    else:
        k = setup
    v = cal.get(k) or cal.get(setup) or {}
    return v.get("win_pct"), v.get("n")


def symbols():
    """Every NSE equity (EQ / BE series)."""
    from .tipcheck import equity_list
    eq = equity_list()
    ser = "SERIES" if "SERIES" in eq.columns else " SERIES"
    return sorted({str(s).strip() for s in eq.loc[eq[ser].astype(str).str.strip().isin(["EQ", "BE"]), "SYMBOL"]})


def today_bars(syms, day):
    """Today's daily candle for every symbol from Kite quotes (open/high/low/last/volume) - {} if not logged in."""
    from . import kite
    if not kite.logged_in():
        return {}
    q = kite.quotes(syms)
    out = {}
    for s, v in q.items():
        try:
            if v.get("volume", 0) > 0 and v["last"] > 0:
                out[s] = {"open": v["open"], "high": max(v["high"], v["last"]), "low": min(v["low"], v["last"]),
                          "close": v["last"], "volume": float(v["volume"])}
        except Exception:
            continue
    return out


def history(sym, day, bar):
    """Daily OHLCV up to and including `day` (today's candle from Kite when given). None = unusable (stale/short)."""
    from . import data_prices
    d = data_prices.load(sym)
    if d is None or not len(d):
        return None
    d = d[["open", "high", "low", "close", "volume"]].copy()
    d = d[d.index < day]                                   # today's row always comes from the freshest source
    if bar:
        d.loc[day] = [bar["open"], bar["high"], bar["low"], bar["close"], bar["volume"]]
    else:
        y = data_prices.load(sym)
        if y is None or day not in y.index:
            return None
        d.loc[day] = y.loc[day, ["open", "high", "low", "close", "volume"]].values
    d = d.sort_index().tail(BARS)
    if len(d) < 520:
        return None
    prev = d.index[-2]
    if (day - prev).days > 6:                              # a gap of more than a long weekend: stale history
        return None
    return d


def _scan_one(args):
    sym, d = args
    try:
        st = {}
        _replica().run(d, _BENCH, state=st)
        tv = float((d["close"] * d["volume"]).tail(20).mean())
        return sym, st, tv
    except Exception as e:
        return sym, {}, f"{type(e).__name__}"


def _init(bench):
    global _BENCH
    _BENCH = bench


def scan(day, bars, procs=4):
    """-> list of (sym, buy, sell, avg turnover) for every stock with usable data."""
    from . import data_prices
    bench = data_prices.load("NIFTY50")["close"]
    if bench.index[-1] < day:                              # NIFTY's own candle for today (needed by the rules)
        nb = bars.get("NIFTY50")
        if nb:
            bench = pd.concat([bench, pd.Series([nb["close"]], index=[day])])
    work = []
    for s in symbols():
        d = history(s, day, bars.get(s))
        if d is not None:
            work.append((s, d))
    log.info("VANTAGE scan: %d stocks with usable data", len(work))
    with get_context("fork").Pool(procs, initializer=_init, initargs=(bench,)) as p:   # own process, no threads
        return p.map(_scan_one, work, chunksize=20)


def _load_signals():
    try:
        return pd.read_csv(SIGNALS_F, dtype=str)
    except Exception:
        return pd.DataFrame(columns=["sym", "signal", "setup", "tier", "score", "close", "stop", "likely", "status",
                                     "sent_at", "exit_date", "exit_why", "exit_price"])


def _save_signals(t):
    tmp = SIGNALS_F.with_suffix(".tmp")
    t.to_csv(tmp, index=False)
    tmp.replace(SIGNALS_F)


def _last_close(sym, day):
    from . import data_prices
    d = data_prices.load(sym)
    return float(d["close"].iloc[-1]) if d is not None and len(d) else float("nan")


def _n(x):
    return f"{x:,.2f}"


def buy_message(sym, b, lk, n, thin):
    return (f"#VANTAGE INDICATOR\n\n#{sym}\n\n"
            f"🟢 BUY · {('Rolling Candle Profile' if b['setup'] == 'RCP' else b['setup'])}"
            f"{(' ' + b['tier']) if b.get('tier') else ''}" + (f" · likely win {lk}% ({n} past NSE signals)" if lk else "") +
            f"\nBuy at the next market open ≈ ₹{_n(b['close'])} · Stop-loss ₹{_n(b['stop'])}"
            + (f" · Target ₹{_n(b['t2'])}" if b.get("t2") == b.get("t2") and b.get("t2") else "")
            + ("\n⚠️ Thinly traded stock - check the bid/ask before buying" if thin else ""))


def sell_message(sym, s, entry):
    res = (s["price"] / float(entry) - 1) * 100 if entry else None
    return (f"#VANTAGE INDICATOR\n\n#{sym}\n\n🔴 SELL (exit) · {s['why']}"
            + (f"\nResult ≈ {res:+.1f}% (from ₹{_n(float(entry))})" if res is not None else "")
            + ("" if s.get("intrabar") else "\nSell at the next market open."))


def run(day=None, source="auto"):
    """The whole job. -> dict summary. Writes vantage_last.json (ok=True only when today's candle was available)."""
    from . import telegram, health
    s = load_settings()
    now = pd.Timestamp.now(tz="Asia/Kolkata").tz_localize(None)
    day = pd.Timestamp(day or now.normalize())
    summ = {"day": str(day.date()), "ok": False}
    if not s.get("vantage_scanner", True):
        summ["why"] = "switched off"
        return summ
    try:
        if not health.traded_today():
            summ.update(ok=True, why="market closed today")
            LAST_F.write_text(json.dumps(summ))
            return summ
    except Exception:
        pass
    syms = symbols()
    from . import data_prices
    try:                                                    # every NSE equity's history up to yesterday (new ones in full)
        data_prices.update(syms + ["NIFTY50"])
    except Exception as e:
        log.warning("VANTAGE: price update failed: %s", type(e).__name__)
    bars = today_bars(syms + ["NIFTY50"], day) if source in ("auto", "kite") else {}
    if not bars and source == "kite":
        summ["why"] = "Kite not logged in"
        return summ
    res = scan(day, bars)
    cal = calibration()
    confirmed = {sym for sym, st, tv in res if isinstance(st, dict) and st.get("buy") and not isinstance(tv, str)}
    live_today = close_followups(day, confirmed, s)          # ❌ for live alerts that did not hold
    sig = _load_signals()
    sent_b = sent_s = 0
    from . import safety
    kill = bool(s.get("kill_switch")) or bool(safety.emergency_active())
    for sym, st, tv in res:
        if isinstance(tv, str):
            continue
        buy, sell = st.get("buy"), st.get("sell")
        open_rows = sig[(sig["sym"] == sym) & (sig["status"] == "open")]
        if not sell and len(open_rows) and not st.get("in_position", True) and not buy:
            # safety net: the exit happened on a day this stock could not be scanned -> tell the owner now
            sell = {"why": "exit signal (it came on a day the stock could not be scanned)",
                    "price": float(_last_close(sym, day)), "intrabar": False}
        if sell and len(open_rows):
            i = open_rows.index[-1]
            if str(sig.loc[i, "exit_date"]) in ("", "nan"):
                sig.loc[i, ["status", "exit_date", "exit_why", "exit_price"]] = ["closed", str(day.date()), sell["why"],
                                                                                 f"{sell['price']:.2f}"]
                _save_signals(sig)                          # record first ...
                telegram.send_reliable(s, sell_message(sym, sell, sig.loc[i, "close"]), label="vantage indicator")
                sent_s += 1
        if buy and not kill:
            key = (sym, str(pd.Timestamp(buy["signal"]).date()))
            if ((sig["sym"] == key[0]) & (sig["signal"] == key[1])).any():
                continue                                    # already sent (re-run) - never twice
            lk, n = likely(cal, buy["setup"], buy.get("tier", ""), buy.get("score", 0))
            row = {"sym": sym, "signal": key[1], "setup": buy["setup"], "tier": buy.get("tier", ""), "score": buy["score"],
                   "close": f"{buy['close']:.2f}", "stop": f"{buy['stop']:.2f}", "likely": lk, "status": "open",
                   "sent_at": str(now)[:16], "exit_date": "", "exit_why": "", "exit_price": ""}
            sig = pd.concat([sig, pd.DataFrame([row]).astype(str)], ignore_index=True)
            _save_signals(sig)                              # ... then send
            msg = buy_message(sym, buy, lk, n, tv < 1e7)
            if live_today.get(sym):
                msg = msg.replace(f"#{sym}\n\n", f"#{sym}\n\n✅ CONFIRMED at the close (today's live signal held)\n", 1)
            telegram.send_reliable(s, msg, label="vantage indicator")
            sent_b += 1
    summ.update(ok=True, source="Kite" if bars else "Yahoo", stocks=len(res), buys=sent_b, sells=sent_s)
    LAST_F.write_text(json.dumps(summ))
    log.info("VANTAGE scan %s: %d stocks, %d BUY and %d SELL sent (%s)", summ["day"], len(res), sent_b, sent_s,
             summ["source"])
    return summ


def due_evening(day_str):
    """The 6:50 pm retry runs only if the 3:40 pm scan did not complete today."""
    try:
        j = json.loads(LAST_F.read_text())
        return not (j.get("day") == day_str and j.get("ok"))
    except Exception:
        return True


# ============================================================================== LIVE (during market hours, D120)
# Owner: "Market is going on ... if any stock among all NSE stocks gets a signal, I get an instant message."
# Every ~3 minutes the same VANTAGE logic runs on every NSE stock with TODAY'S CANDLE SO FAR (Kite: open, high, low,
# last price, volume). A signal on a forming candle can still disappear before 3:30 pm, so each live alert gets a
# ✅ CONFIRMED / ❌ CANCELLED follow-up at the close (the tested results apply to confirmed signals). Stop-losses of
# BUYs already sent are checked on every cycle and alerted instantly.
SNAP_F = DATA / "live_quotes.json"
LIVE_F = PRIVATE / "vantage_live.csv"


def write_snapshot(quotes):
    """Called by the live engine (~every 20 s): {sym: [open, high, low, last, volume]} + time."""
    now = pd.Timestamp.now(tz="Asia/Kolkata").tz_localize(None)
    d = {"time": str(now)[:19], "q": {s: [v.get("open"), v.get("high"), v.get("low"), v.get("last"), v.get("volume")]
                                      for s, v in quotes.items() if v.get("last")}}
    tmp = SNAP_F.with_suffix(".tmp")
    tmp.write_text(json.dumps(d))
    tmp.replace(SNAP_F)


def read_snapshot(max_age_s=180):
    """-> (time, {sym: bar}) or (None, {}) when missing / older than max_age_s (never act on stale prices)."""
    try:
        d = json.loads(SNAP_F.read_text())
        t = pd.Timestamp(d["time"])
        now = pd.Timestamp.now(tz="Asia/Kolkata").tz_localize(None)
        if (now - t).total_seconds() > max_age_s:
            return None, {}
        out = {}
        for s, (o, h, l, c, v) in d["q"].items():
            # an index has no volume (NIFTY50 must stay - every rule needs it); a stock with no trade today is skipped
            if c and o and c > 0 and o > 0 and (v or s == "NIFTY50"):
                v = v or 0
                out[s] = {"open": float(o), "high": max(float(h), float(c)), "low": min(float(l), float(c)),
                          "close": float(c), "volume": float(v)}
        return t, out
    except Exception:
        return None, {}


class LiveScanner:
    """Long-lived (one process for the trading day): histories are loaded once, each cycle only adds today's bar."""

    def __init__(self, day=None):
        from . import data_prices
        self.day = pd.Timestamp(day or pd.Timestamp.now(tz="Asia/Kolkata").tz_localize(None).normalize())
        self.hist, self.pre = {}, {}
        for s in symbols():
            d = data_prices.load(s)
            if d is None or len(d) < 519:
                continue
            d = d[["open", "high", "low", "close", "volume"]]
            d = d[d.index < self.day].tail(BARS - 1)
            if len(d) < 519 or (self.day - d.index[-1]).days > 6:
                continue                                    # stale history: skipped, never guessed
            self.hist[s] = d
            c = d["close"]
            # necessary conditions of the 3 BUY types (dip: >= 1.1 x SMA200; RCP: within 10% of the 250-day closing
            # high; breakout: above the prior 50-day high) -> a stock below all three cannot signal today
            # (3% slack on the 200-day average: today's average can be a little lower than yesterday's)
            self.pre[s] = (1.10 * 0.97 * float(c.tail(200).mean()), 0.9 * float(c.tail(249).max()),
                           float(d["high"].tail(50).max()))
        b = data_prices.load("NIFTY50")["close"]
        self.bench = b[b.index < self.day]
        log.info("VANTAGE live: %d stocks ready", len(self.hist))

    def candidates(self, bars):
        out = []
        for s, (dip, rcp, brk) in self.pre.items():
            b = bars.get(s)
            if b and (b["close"] >= min(dip, rcp) or b["close"] > brk):
                out.append(s)
        return out

    def cycle(self, procs=3):
        """One live pass. -> (snapshot time, list of (sym, state, avg turnover))."""
        t, bars = read_snapshot()
        if t is None or "NIFTY50" not in bars:
            return None, []
        bench = pd.concat([self.bench, pd.Series([bars["NIFTY50"]["close"]], index=[self.day])])
        work = []
        for s in self.candidates(bars):
            d = self.hist[s].copy()
            b = bars[s]
            d.loc[self.day] = [b["open"], b["high"], b["low"], b["close"], b["volume"]]
            work.append((s, d))
        if not work:
            return t, []
        with get_context("fork").Pool(procs, initializer=_init, initargs=(bench,)) as p:
            return t, p.map(_scan_one, work, chunksize=10)


def _load_live():
    try:
        return pd.read_csv(LIVE_F, dtype=str)
    except Exception:
        return pd.DataFrame(columns=["day", "sym", "setup", "tier", "time", "price", "stop", "outcome"])


def live_buy_message(sym, b, lk, n, price, t, thin):
    kind = "Rolling Candle Profile" if b["setup"] == "RCP" else b["setup"]
    return (f"#VANTAGE INDICATOR\n\n#{sym}\n\n"
            f"⚡ LIVE BUY signal · {kind}{(' ' + b['tier']) if b.get('tier') else ''}"
            + (f" · likely win {lk}% if it holds to the close" if lk else "") +
            f"\nPrice now ₹{_n(price)} ({t:%H:%M}) · Stop-loss ₹{_n(b['stop'])}"
            + ("\n⚠️ Thinly traded stock - check the bid/ask" if thin else "") +
            "\n⏳ Forming candle: I'll confirm ✅ or cancel ❌ right after the 3:30 pm close.")


def live_step(scanner, s=None):
    """One live cycle: instant stop-loss alerts for BUYs already sent, then new live BUY alerts (once per stock/day)."""
    from . import telegram, safety
    s = s or load_settings()
    t, res = scanner.cycle()
    if t is None:
        return {"ok": False, "why": "no fresh live prices (Kite not logged in or engine not running)"}
    _, bars = read_snapshot()
    sig = _load_signals()
    stops = 0
    for i, r in sig[sig["status"] == "open"].iterrows():          # instant stop-loss alerts
        b = bars.get(r["sym"])
        try:
            stop = float(r["stop"])
        except Exception:
            continue
        if b and b["low"] <= stop and pd.Timestamp(r["signal"]) < scanner.day:
            sig.loc[i, ["status", "exit_date", "exit_why", "exit_price"]] = ["closed", str(scanner.day.date()),
                                                                             "Stop-loss (live)", f"{b['close']:.2f}"]
            _save_signals(sig)
            telegram.send_reliable(s, sell_message(r["sym"], {"why": "Stop-loss hit (live) - exit now",
                                                              "price": b["close"], "intrabar": True}, r["close"]),
                                   label="vantage indicator")
            stops += 1
    if s.get("kill_switch") or safety.emergency_active():
        return {"ok": True, "live_buys": 0, "stops": stops, "why": "kill switch / safety stop"}
    live = _load_live()
    cal = calibration()
    day = str(scanner.day.date())
    sent = 0
    for sym, st, tv in res:
        b = st.get("buy") if isinstance(st, dict) else None
        if not b or isinstance(tv, str):
            continue
        if ((live["day"] == day) & (live["sym"] == sym)).any():
            continue                                          # one live alert per stock per day
        lk, n = likely(cal, b["setup"], b.get("tier", ""), b.get("score", 0))
        row = {"day": day, "sym": sym, "setup": b["setup"], "tier": b.get("tier", ""), "time": f"{t:%H:%M}",
               "price": f"{b['close']:.2f}", "stop": f"{b['stop']:.2f}", "outcome": ""}
        live = pd.concat([live, pd.DataFrame([row]).astype(str)], ignore_index=True)
        tmp = LIVE_F.with_suffix(".tmp")
        live.to_csv(tmp, index=False)
        tmp.replace(LIVE_F)                                   # record first ...
        telegram.send_reliable(s, live_buy_message(sym, b, lk, n, b["close"], t, tv < 1e7), label="vantage indicator")
        sent += 1                                             # ... then send
    return {"ok": True, "candidates": len(res), "live_buys": sent, "stops": stops, "time": f"{t:%H:%M:%S}"}


def close_followups(day, confirmed, s=None):
    """At the close scan: every live alert of the day gets ✅ CONFIRMED (the normal BUY follows as the tracked signal)
    or ❌ CANCELLED. confirmed = set of symbols with a BUY on the closed candle."""
    from . import telegram
    s = s or load_settings()
    live = _load_live()
    m = (live["day"] == str(day.date())) & (live["outcome"].fillna("").isin(["", "nan"]))
    out = []
    for i, r in live[m].iterrows():
        ok = r["sym"] in confirmed
        live.loc[i, "outcome"] = "confirmed" if ok else "cancelled"
        out.append((r["sym"], ok))
    if out:
        tmp = LIVE_F.with_suffix(".tmp")
        live.to_csv(tmp, index=False)
        tmp.replace(LIVE_F)
    for sym, ok in out:
        if not ok:
            telegram.send_reliable(s, f"#VANTAGE INDICATOR\n\n#{sym}\n\n❌ CANCELLED - today's live signal did not "
                                      "hold until the close (not a valid signal). If you bought it, you are outside the "
                                      "system: keep your stop-loss or exit.", label="vantage indicator")
    return dict(out)
