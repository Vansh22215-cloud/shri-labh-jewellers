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
_MISSING = {"n": 0}
MIN_READY = 0.6                 # Yahoo fallback: scan only when >= 60% of normal stocks have the day's candle


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


_REC = {}


def company_record(sym):
    """(signals, wins) of this company in the 13-year test (vantage-ai/validation/trades_FINAL.csv) - information
    only: the pre-registered test (CALIB_RESULTS.md) found a company's own past record does NOT predict its next one."""
    if not _REC:
        try:                                           # all NSE stocks with >= 2 years of prices (company_record.py)
            _REC.update({k: tuple(v) for k, v in json.load(open(REPLICA_DIR / "company_record.json")).items()})
        except Exception:
            pass
    if not _REC:
        # every stock's whole history (improve_trades_U.csv: all NSE stocks, not only while in the top 300) first,
        # then the top-300 test for stocks missing there (e.g. delisted)
        for f in ("trades_FINAL.csv", "improve_trades_U.csv"):
            try:
                T = pd.read_csv(REPLICA_DIR / f, usecols=["sym", "entry", "exit"])
                T["win"] = (T["exit"] / T["entry"] - 1 - 0.0035) > 0
                _REC.update({s: (int(len(g)), int(g["win"].sum())) for s, g in T.groupby("sym")})
            except Exception:
                pass
        _REC.setdefault("_", (0, 0))
    return _REC.get(sym, (0, 0))


def note_line(sym):
    """Owner 18 Nov: last line of every VANTAGE BUY - 'Note : X of X past Vantage signals won.' (this company's own
    signals in the 13-year test; information only, see CALIB_RESULTS.md)."""
    n, w = company_record(sym)
    return (f"\n\nNote : {w} of {n} past Vantage signals won." if n
            else "\n\nNote : No past Vantage signals for this company yet.")


def _cal_key(setup, tier, score):
    if setup == "Dip-buy":
        return f"Dip-buy {tier}"
    if setup == "Breakout":
        return "Breakout 90+" if score >= 90 else "Breakout 80-89" if score >= 80 else "Breakout 70-79"
    return setup


def likely(cal, setup, tier, score):
    k = _cal_key(setup, tier, score)
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
            if len(d) >= 519 and (day - d.index[-1]).days <= 6:
                _MISSING["n"] += 1                           # a normal stock whose candle for `day` is not out yet
            return None
        d.loc[day] = y.loc[day, ["open", "high", "low", "close", "volume"]].values
    d = d.sort_index().tail(BARS)
    if len(d) < 520:
        return None
    prev = d.index[-2]
    if (day - prev).days > 6:                              # a gap of more than a long weekend: stale history
        return None
    return d


class NotReady(Exception):
    """The day's prices are not published yet for most stocks (Yahoo can lag by hours) - try again later."""


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
    _MISSING["n"] = 0
    for s in symbols():
        d = history(s, day, bars.get(s))
        if d is not None:
            work.append((s, d))
    log.info("VANTAGE scan: %d stocks with usable data (%d without the day's candle yet)", len(work), _MISSING["n"])
    if not bars and len(work) < MIN_READY * (len(work) + _MISSING["n"]):
        raise NotReady(f"only {len(work)} of {len(work) + _MISSING['n']} stocks have the day's prices yet")
    with get_context("fork").Pool(procs, initializer=_init, initargs=(bench,)) as p:   # own process, no threads
        return p.map(_scan_one, work, chunksize=20)


def _load_signals():
    try:
        return pd.read_csv(SIGNALS_F, dtype=str)
    except Exception:
        return pd.DataFrame(columns=["sym", "signal", "setup", "tier", "score", "close", "stop", "likely", "status",
                                     "sent_at", "exit_date", "exit_why", "exit_price", "limit_test"])


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


def results_soon(sym, day, days=5):
    """D123 (owner-approved): the company's next results date if it falls within the next `days` trading days
    (weekdays), else None. Results dates come from data/events/earnings (announced in advance: SEBI requires
    5 days' notice of the board meeting)."""
    try:
        e = pd.to_datetime(pd.read_csv(DATA / "events" / "earnings" / f"{sym}.csv")["date"], errors="coerce").dropna()
    except Exception:
        return None
    day = pd.Timestamp(day).normalize()
    end = pd.bdate_range(day, periods=days + 1)[-1]
    nxt = e[(e > day) & (e <= end)]
    return nxt.min() if len(nxt) else None


def results_line(sym, day):
    r = results_soon(sym, day)
    if r is None:
        return "", 1.0
    n = len(pd.bdate_range(pd.Timestamp(day).normalize(), r)) - 1
    return (f"\n📅 Results on {r:%d %b} (in {n} trading day{'s' if n != 1 else ''}) - half quantity: signals just "
            f"before results earned about half as much in testing"), 0.5


def qty_line(entry, stop, settings=None, scale=1.0):
    """Owner 17 Nov: quantity in every BUY message - the system's own sizing (1% risk of the stated capital, at most
    25% of capital in one stock). Never a guessed capital: no line when capital is not set."""
    from . import safety
    s = settings or load_settings()
    ok, _why = safety.configured(s)
    if not ok:
        return ""
    cap = float(s["capital"])
    L = safety.limits(s)
    q = safety.size(entry, stop, s, float(L["risk_per_trade_pct"]) * scale)
    if q < 1:
        return (f"\n📦 Qty: 0 - one share does not fit your limits (₹{cap:,.0f} capital, "
                f"{L['risk_per_trade_pct']:g}% risk, max {L['max_order_pct']:g}% in one stock) - skip")
    return (f"\n📦 Qty: {q} shares ≈ ₹{q * entry:,.0f} · \n🛘 max loss ≈ ₹{q * (entry - stop):,.0f} "
            f"({float(L['risk_per_trade_pct']) * scale:g}% of ₹{cap:,.0f})")


def min_turnover(s):
    """D121 (owner-approved 17 Nov): BUY signals only for stocks trading >= Rs 2 crore a day on average (20 days).
    Pre-registered test: thinner stocks were clearly weaker in the 2023-26 holdout (PF 1.20 vs 1.48)."""
    return float(s.get("vantage_min_turnover_cr", 2)) * 1e7


def buy_message(sym, b, lk, n, thin, day=None):
    return (f"#VANTAGE INDICATOR\n\n#{sym}\n\n"
            f"🟢 BUY · {('Rolling Candle Profile' if b['setup'] == 'RCP' else b['setup'])}"
            f"{(' ' + b['tier']) if b.get('tier') else ''}" + (f" · likely win {lk}%" if lk else "") +
            f"\nBuy at the next market open ≈ ₹{_n(b['close'])} · "
            f"\n🛑 Stop-loss ₹{_n(b['stop'])}"
            + (f"\n🎯 Target ₹{_n(b['t2'])}" if b.get("t2") == b.get("t2") and b.get("t2") else "")
            + _res_and_qty(sym, b["close"], b["stop"], day)
            + ("\n⚠️ Thinly traded stock - check the bid/ask before buying" if thin else "")
            + note_line(sym))


def sell_message(sym, s, entry):
    res = (s["price"] / float(entry) - 1) * 100 if entry else None
    return (f"#VANTAGE INDICATOR\n\n#{sym}\n\n🔴 SELL (exit) · {s['why']}"
            + (f"\nResult ≈ {res:+.1f}% (from ₹{_n(float(entry))})" if res is not None else "")
            + ("" if s.get("intrabar") else "\nSell at the next market open."))


# ============================================================================== ADD TO WINNERS (round 13, owner: "Yes")
# 13-year test (vantage-ai/validation/IMPROVE13_RESULTS.md): a trend (Rolling Candle Profile) trade that is up >= 8% at
# the close of its 15th trading day keeps earning more per day than a new signal. The second lot is sized to the REAL
# stop-loss (the first lot's), so its loss stays within the 1% limit: +0.4 to +1.0 point of yearly growth in all four
# test cells with about the same worst fall (the tested 'stop distance from the new price' sizing gave +1-2 points but
# could lose ~3-4% of capital on the second lot - above the owner's 1% limit, so not used). Exactly as tested: checked once,
# on day 15 (the 16th bar after the signal day); the second lot is bought at the next open and exits with the first.
ADD_DAY, ADD_GAIN = 15, 0.08


def add_message(sym, price, entry, gain, q, orig_stop, cap, rl):
    return (f"#VANTAGE INDICATOR\n\n#{sym}\n\n"
            f"📈 ADD MORE · Rolling Candle Profile · up {gain * 100:.1f}% after {ADD_DAY} trading days"
            f"\nBuy another {q} shares at the next market open ≈ ₹{_n(price)} · "
            f"\n🛑 Stop-loss stays ₹{_n(orig_stop)} for both lots"
            f"\n📦 Second lot ≈ ₹{q * price:,.0f} · "
            f"\n🛘 max loss on it ≈ ₹{q * max(price - orig_stop, 0):,.0f} if the stop-loss is hit"
            + rl +
            "\nSell both lots together when the SELL comes (one message covers both)."
            f"\n\nNote : adding to trend trades that were up 8%+ after 15 days raised yearly growth by about 0.5-1% "
            f"in the 13-year test (₹{cap:,.0f} account), with the same 1% risk limit.")


def add_to_winners(day, bars, sig, s):
    """At the close scan: every open trend signal on its 15th trading day and up >= 8% gets one ADD MORE message."""
    from . import telegram, safety
    if not s.get("vantage_add_to_winners", True) or s.get("kill_switch") or safety.emergency_active():
        return 0
    ok, _ = safety.configured(s)
    if "added" not in sig.columns:
        sig["added"] = ""
    sent = 0
    for i, r in sig[(sig["status"] == "open") & (sig["setup"] == "RCP")].iterrows():
        if str(r.get("added", "")) not in ("", "nan"):
            continue
        d = history(r["sym"], day, bars.get(r["sym"]))
        if d is None:
            continue
        after = d.index[d.index > pd.Timestamp(r["signal"])]
        if len(after) != ADD_DAY + 1 or after[-1] != day:          # exactly the close of trading day 15
            continue
        entry, price = float(r["close"]), float(d["close"].iloc[-1])
        gain = price / entry - 1
        if gain < ADD_GAIN:
            continue
        stop0 = float(r["stop"])
        rl, scale = results_line(r["sym"], day)
        q = 0
        if ok:   # sized to the REAL stop (the first lot's): a stop-out of the second lot loses at most the 1% limit
            L = safety.limits(s)
            q = safety.size(price, stop0, s, float(L["risk_per_trade_pct"]) * scale)
        if q < 1:
            continue                                                # no capital set / one share does not fit: no message
        sig.loc[i, "added"] = f"{day.date()} {q} @ {price:.2f}"
        _save_signals(sig)                                          # record first ...
        telegram.send_reliable(s, add_message(r["sym"], price, entry, gain, q, stop0, float(s["capital"]), rl),
                               label="vantage indicator")
        sent += 1                                                   # ... then send
    return sent


def _held_elsewhere(sym, channel, day, b, s):
    """D139 (owner: no repeat tips): True (and the repeat is recorded for the Learner) when the stock already has an
    open tip - from the live engine, or (for live / 3:20 pm alerts) an open VANTAGE tip from an earlier day."""
    if not s.get("no_repeat_tips", True):
        return False
    from .registry import open_stocks, record_suppressed
    held = open_stocks().get(str(sym))
    if not held or (channel == "VANTAGE" and held == "VANTAGE"):
        return False                                      # same channel: its own once-per-signal rule applies
    record_suppressed(sym, channel, held, day, b.get("close"), b.get("stop"))
    return True


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
    try:
        res = scan(day, bars)
    except NotReady as e:
        summ["why"] = f"prices not ready: {e}"
        log.info("VANTAGE: %s - will retry", summ["why"])
        return summ
    errs = [tv for _, _, tv in res if isinstance(tv, str)]
    if res and len(errs) > 0.2 * len(res):                  # the logic itself is broken: never report "0 signals"
        from collections import Counter
        summ["why"] = f"scan errors on {len(errs)} of {len(res)} stocks: {Counter(errs).most_common(2)}"
        log.warning("VANTAGE: %s", summ["why"])
        try:
            from . import telegram
            telegram.send_reliable(s, "⚠️ VANTAGE scanner problem: " + summ["why"] + " - signals could not be checked "
                                      "today.", label="system problem")
        except Exception:
            pass
        return summ
    cal = calibration()
    confirmed = {sym for sym, st, tv in res if isinstance(st, dict) and st.get("buy") and not isinstance(tv, str)}
    live_today = close_followups(day, confirmed, s)          # ❌ for live alerts that did not hold
    called = close_call_followups(day, confirmed, s)         # buy-now alerts: ✅ below, or ❌ sell at the next open
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
        if buy and not kill and tv >= min_turnover(s):
            key = (sym, str(pd.Timestamp(buy["signal"]).date()))
            if ((sig["sym"] == key[0]) & (sig["signal"] == key[1])).any():
                continue                                    # already sent (re-run) - never twice
            if _held_elsewhere(sym, "VANTAGE", day, buy, s):
                continue                                    # D139: open tip from another channel - not repeated
            lk, n = likely(cal, buy["setup"], buy.get("tier", ""), buy.get("score", 0))
            lim = buy["close"] - 0.25 * float(buy.get("atr") or 0)   # D122 forward test (R2): would a limit fill?
            row = {"sym": sym, "signal": key[1], "setup": buy["setup"], "tier": buy.get("tier", ""), "score": buy["score"],
                   "close": f"{buy['close']:.2f}", "stop": f"{buy['stop']:.2f}", "likely": lk, "status": "open",
                   "limit_test": f"{lim:.2f}" if buy.get("atr") else "",
                   "sent_at": str(now)[:16], "exit_date": "", "exit_why": "", "exit_price": ""}
            sig = pd.concat([sig, pd.DataFrame([row]).astype(str)], ignore_index=True)
            _save_signals(sig)                              # ... then send
            msg = buy_message(sym, buy, lk, n, tv < 1e7, day)
            if called.get(sym):
                msg = msg.replace(f"#{sym}\n\n", f"#{sym}\n\n✅ CONFIRMED - if you bought before the close, you are in. "
                                                  "Missed it? Buy at the next open:\n", 1)
            elif live_today.get(sym):
                msg = msg.replace(f"#{sym}\n\n", f"#{sym}\n\n✅ CONFIRMED at the close (today's live signal held)\n", 1)
            telegram.send_reliable(s, msg, label="vantage indicator")
            sent_b += 1
    try:
        adds = add_to_winners(day, bars, sig, s)
    except Exception as e:
        adds = 0
        log.warning("VANTAGE add-to-winners failed: %s", type(e).__name__)
    summ.update(ok=True, source="Kite" if bars else "Yahoo", stocks=len(res), buys=sent_b, sells=sent_s, adds=adds)
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


def _res_and_qty(sym, entry, stop, day):
    rl, scale = results_line(sym, day) if day is not None else ("", 1.0)
    return rl + qty_line(entry, stop, scale=scale)


def live_buy_message(sym, b, lk, n, price, t, thin):
    kind = "Rolling Candle Profile" if b["setup"] == "RCP" else b["setup"]
    return (f"#VANTAGE INDICATOR\n\n#{sym}\n\n"
            f"⚡ LIVE BUY signal · {kind}{(' ' + b['tier']) if b.get('tier') else ''}"
            + (f" · likely win {lk}% if it holds to the close" if lk else "") +
            f"\nPrice now ₹{_n(price)} ({t:%H:%M}) · "
            f"\n🛑 Stop-loss ₹{_n(b['stop'])}"
            + _res_and_qty(sym, price, b["stop"], t)
            + ("\n⚠️ Thinly traded stock - check the bid/ask" if thin else "") +
            "\n⏳ Forming candle: I'll confirm ✅ or cancel ❌ right after the 3:30 pm close."
            + note_line(sym))


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
        if not b or isinstance(tv, str) or tv < min_turnover(s):
            continue
        if ((live["day"] == day) & (live["sym"] == sym)).any():
            continue                                          # one live alert per stock per day
        if _held_elsewhere(sym, "VANTAGE live", day, b, s):
            continue                                          # D139: open tip from any channel - not repeated
        lk, n = likely(cal, b["setup"], b.get("tier", ""), b.get("score", 0))
        row = {"day": day, "sym": sym, "setup": b["setup"], "tier": b.get("tier", ""), "time": f"{t:%H:%M}",
               "price": f"{b['close']:.2f}", "stop": f"{b['stop']:.2f}", "outcome": ""}
        live = pd.concat([live, pd.DataFrame([row]).astype(str)], ignore_index=True)
        tmp = LIVE_F.with_suffix(".tmp")
        live.to_csv(tmp, index=False)
        tmp.replace(LIVE_F)                                   # record first ...
        telegram.send_reliable(s, live_buy_message(sym, b, lk, n, b["close"], t, tv < 1e7), label="vantage indicator")
        sent += 1                                             # ... then send
    calls = close_call(scanner.day, t, res, s, cal)
    return {"ok": True, "candidates": len(res), "live_buys": sent, "stops": stops, "close_calls": calls,
            "time": f"{t:%H:%M:%S}"}


# ============================================================================== BUY BEFORE THE CLOSE (round 3, C1)
# 13-year test (vantage-ai/validation/IMPROVE3_RESULTS.md): buying at the signal day's close instead of the next
# morning's open earned more per trade (recent years +3.24% vs +2.91%) and won more often (44.2% vs 42.5%) - the
# overnight jump is avoided. So at ~3:20 pm every stock whose BUY signal is on gets one "buy now, before the close"
# alert; the 3:40 pm scan confirms it or says to sell at the next open if it did not hold.
CALL_F = PRIVATE / "vantage_closecall.csv"
CALL_FROM, CALL_TO = 15 * 60 + 15, 15 * 60 + 29


def _load_calls():
    try:
        return pd.read_csv(CALL_F, dtype=str)
    except Exception:
        return pd.DataFrame(columns=["day", "sym", "time", "price", "stop", "outcome"])


def close_call_message(sym, b, lk, n, price, t, thin):
    kind = "Rolling Candle Profile" if b["setup"] == "RCP" else b["setup"]
    return (f"#VANTAGE INDICATOR\n\n#{sym}\n\n"
            f"🔔 BUY NOW - before the 3:30 pm close · {kind}{(' ' + b['tier']) if b.get('tier') else ''}"
            + (f" · likely win {lk}%" if lk else "") +
            f"\nPrice now ₹{_n(price)} ({t:%H:%M}) · "
            f"\n🛑 Stop-loss ₹{_n(b['stop'])}"
            + _res_and_qty(sym, price, b["stop"], t)
            + ("\n⚠️ Thinly traded stock - check the bid/ask" if thin else "") +
            "\nBuying now (not tomorrow morning) earned more in the 13-year test. I'll confirm ✅ after the close."
            + note_line(sym))


def close_call(day, t, res, s, cal):
    """Once per stock per day, between 3:15 and 3:29 pm: every stock with a BUY signal on gets the buy-now alert."""
    from . import telegram, safety
    if not s.get("vantage_close_call", True) or t is None or not (CALL_FROM <= t.hour * 60 + t.minute <= CALL_TO):
        return 0
    if s.get("kill_switch") or safety.emergency_active():
        return 0
    calls, d, sent = _load_calls(), str(day.date()), 0
    for sym, st, tv in res:
        b = st.get("buy") if isinstance(st, dict) else None
        if not b or isinstance(tv, str) or tv < min_turnover(s):
            continue
        if ((calls["day"] == d) & (calls["sym"] == sym)).any():
            continue
        if _held_elsewhere(sym, "VANTAGE 3:20 pm", d, b, s):
            continue                                          # D139: open tip from any channel - not repeated
        lk, n = likely(cal, b["setup"], b.get("tier", ""), b.get("score", 0))
        row = {"day": d, "sym": sym, "time": f"{t:%H:%M}", "price": f"{b['close']:.2f}", "stop": f"{b['stop']:.2f}",
               "outcome": ""}
        calls = pd.concat([calls, pd.DataFrame([row]).astype(str)], ignore_index=True)
        tmp = CALL_F.with_suffix(".tmp")
        calls.to_csv(tmp, index=False)
        tmp.replace(CALL_F)                                   # record first ...
        telegram.send_reliable(s, close_call_message(sym, b, lk, n, b["close"], t, tv < 1e7), label="vantage indicator")
        sent += 1                                             # ... then send
    return sent


def close_call_followups(day, confirmed, s=None):
    """At the close scan: buy-now alerts that held -> {sym: True}; those that did not -> ❌ sell at the next open."""
    from . import telegram
    s = s or load_settings()
    calls = _load_calls()
    m = (calls["day"] == str(day.date())) & (calls["outcome"].fillna("").isin(["", "nan"]))
    out = {}
    for i, r in calls[m].iterrows():
        out[r["sym"]] = r["sym"] in confirmed
        calls.loc[i, "outcome"] = "confirmed" if out[r["sym"]] else "cancelled"
    if out:
        tmp = CALL_F.with_suffix(".tmp")
        calls.to_csv(tmp, index=False)
        tmp.replace(CALL_F)
    for sym, ok in out.items():
        if not ok:
            telegram.send_reliable(s, f"#VANTAGE INDICATOR\n\n#{sym}\n\n❌ The 3:20 pm buy signal did not hold at the "
                                      "close. If you bought it, sell at the next market open.", label="vantage indicator")
    return out


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
