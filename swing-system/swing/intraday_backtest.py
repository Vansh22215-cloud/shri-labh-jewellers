"""Test the three intraday setups on Kite's own 5-minute history (owner's Connect plan) - the fixed rule that decides
which setups may keep sending live intraday tips (DECISIONS D94).

Data: Kite 5-minute candles, the last ~200 trading days, for the ~100 most-traded NSE stocks (Kite gives up to 100 days
per request). For every day and stock, the SAME code as the live scanner (intraday_paper.signals / the same exit
rules: stop first if stop and target fall in one bar, everything closed at 15:20) is run on that day's bars only - a
setup can only use bars up to its trigger (no look-ahead). Sized to lose Rs 450 at the stop, Zerodha intraday charges
included.

Rule written BEFORE the results are seen (not tuned afterwards): a setup may send live tips only if it has at least 40
trades AND makes money after charges (average net per trade > 0) in BOTH the older half and the newer half of the
history. Re-run every week (a weekday after the close, while the Kite login is valid) on fresh data, so a setup that stops working stops sending tips by itself.
"""
import json
import time

import pandas as pd

from .config import get_logger
from . import intraday_paper as ip
from .setups import WORDS as SETUP_WORDS

log = get_logger()
MIN_TRADES = 40


def history(sym, days=200):
    """~`days` calendar days of Kite 5-minute candles (two requests of up to 100 days)."""
    from . import kite
    from datetime import datetime, timedelta
    parts = []
    end = datetime.now(kite.IST)
    for _ in range(max(1, days // 95)):
        start = end - timedelta(days=95)
        try:
            ins = kite.instruments()
            row = ins[ins["tradingsymbol"] == sym]
            if not len(row):
                return None
            tok = int(row["instrument_token"].iloc[0])
            r = kite._get(f"/instruments/historical/{tok}/5minute",
                          params={"from": start.strftime("%Y-%m-%d %H:%M:%S"), "to": end.strftime("%Y-%m-%d %H:%M:%S")},
                          timeout=60)
            c = r.json()["data"]["candles"]
            if c:
                df = pd.DataFrame([x[:6] for x in c], columns=["date", "open", "high", "low", "close", "volume"])
                df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
                parts.append(df.set_index("date"))
        except Exception as e:
            log.warning("intraday history %s failed: %s", sym, type(e).__name__)
        end = start
        time.sleep(0.4)
    if not parts:
        return None
    return pd.concat(parts).sort_index().loc[lambda d: ~d.index.duplicated()]


def simulate_day(day_bars, prev_close, atr_series=None, nifty_day=None, trend_up=None):
    """All setup trades of one stock-day, with exits, after charges - with the SAME rules as the live engine:
    noise-proof stop (>= 1 ATR), trigger bar volume >= 1.5x, with the daily trend, Nifty on the trade's side of its
    open. -> list of dicts."""
    out = []
    from .setups import all_signals, noise_proof
    vol_avg = day_bars["volume"].rolling(20, min_periods=5).mean().shift(1)
    for sg in all_signals(day_bars, prev_close):
        ts = sg["entry_time"]
        if atr_series is not None:
            a = atr_series.get(ts) if hasattr(atr_series, "get") else None
            sg = noise_proof(sg, float(a) if a is not None else None)
            if sg is None:
                continue
        v_ok = day_bars.at[ts, "volume"] >= 1.5 * (vol_avg.get(ts) or float("inf"))
        if atr_series is not None and not v_ok:
            continue
        if trend_up is not None and (sg["side"] == "buy") != bool(trend_up):
            continue
        if nifty_day is not None and len(nifty_day):
            nb = nifty_day[nifty_day.index <= ts]
            if len(nb):
                up = float(nb["close"].iloc[-1]) >= float(nifty_day["open"].iloc[0])
                if (sg["side"] == "buy") != up:
                    continue
        risk_ps = abs(sg["entry"] - sg["stop"])
        if risk_ps <= 0:
            continue
        qty = int(min(ip.RISK_RS / risk_ps, 45000 / sg["entry"]))
        if qty < 1:
            continue
        after = day_bars[day_bars.index > sg["entry_time"]]
        buy = sg["side"] == "buy"
        px, how = None, None
        for ts, x in after.iterrows():
            if ts.hour * 60 + ts.minute >= 15 * 60 + 20:
                break
            if (x["low"] <= sg["stop"]) if buy else (x["high"] >= sg["stop"]):
                px, how = sg["stop"], "stop"; break
            if (x["high"] >= sg["target"]) if buy else (x["low"] <= sg["target"]):
                px, how = sg["target"], "target"; break
        if px is None:
            last = after[after.index.map(lambda t: t.hour * 60 + t.minute < 15 * 60 + 20)]
            if not len(last):
                continue
            px, how = float(last["close"].iloc[-1]), "close"
        pnl = (px - sg["entry"]) * qty * (1 if buy else -1)
        out.append({"day": str(day_bars.index[0].date()), "setup": sg["setup"], "side": sg["side"], "how": how,
                    "net": pnl - ip._charges(sg["entry"], px, qty)})
    return out


def run(symbols=None, days=200, max_symbols=100):
    """Back-test all setups; writes data/intraday_setups.json with the allowed setups. Returns the summary text."""
    from . import kite
    if not kite.logged_in():
        return None
    if symbols is None:
        from .archive import intraday_universe
        symbols = intraday_universe()[:max_symbols]
    from .setups import atr
    from . import data_prices
    trades = []
    nifty = history("NIFTY 50", days)
    nifty_by_day = {d: g for d, g in nifty.groupby(nifty.index.date)} if nifty is not None else {}
    for s in symbols:
        h = history(s, days)
        if h is None or not len(h):
            continue
        a_all = atr(h)
        closes = h.groupby(h.index.date)["close"].last()
        prev = closes.shift(1)
        dly = data_prices.load(s)
        s200 = dly["close"].rolling(200).mean() if dly is not None and len(dly) > 200 else None
        for d, g in h.groupby(h.index.date):
            if len(g) < 20:
                continue
            trend = None
            if s200 is not None:
                past = dly.index[dly.index < pd.Timestamp(d)]
                if len(past) and pd.notna(s200.loc[past[-1]]):
                    trend = bool(dly["close"].loc[past[-1]] > s200.loc[past[-1]])
            for t in simulate_day(g, prev.get(d), a_all, nifty_by_day.get(d), trend):
                t["symbol"] = s
                trades.append(t)
    return decide(pd.DataFrame(trades), len(symbols))


def decide(tr, n_symbols=0):
    """The fixed rule -> allowed setups + plain summary; saved to data/intraday_setups.json."""
    lines, allowed, stats = [], [], {}
    if len(tr):
        days = sorted(tr["day"].unique())
        mid = days[len(days) // 2]
        for st, g in tr.groupby("setup"):
            a, b = g[g["day"] < mid], g[g["day"] >= mid]
            ok = len(g) >= MIN_TRADES and len(a) and len(b) and a["net"].mean() > 0 and b["net"].mean() > 0
            stats[st] = {"trades": int(len(g)), "win_pct": round((g["net"] > 0).mean() * 100, 1),
                         "avg_net": round(g["net"].mean(), 1), "older_avg": round(a["net"].mean(), 1) if len(a) else None,
                         "newer_avg": round(b["net"].mean(), 1) if len(b) else None, "allowed": bool(ok)}
            if ok:
                allowed.append(st)
            lines.append(f"{'✅' if ok else '❌'} {SETUP_WORDS.get(st, st)}: {len(g)} trades, {stats[st]['win_pct']:.0f}% "
                         f"won, average ₹{stats[st]['avg_net']:+,.0f} per trade after charges (older half "
                         f"₹{stats[st]['older_avg'] or 0:+,.0f}, newer half ₹{stats[st]['newer_avg'] or 0:+,.0f})")
    from .setups import RULES_VERSION
    ip.SETUPS_F.write_text(json.dumps({"allowed": allowed, "stats": stats, "tested": str(pd.Timestamp.now().date()),
                                       "rules_version": RULES_VERSION,
                                       "symbols": n_symbols, "rule": f">= {MIN_TRADES} trades and profit after charges "
                                                                     "in both halves"}, indent=1))
    head = (f"🧪 <b>Intraday setups tested on Kite history</b> ({n_symbols} stocks, last ~200 days of 5-minute bars, "
            "Zerodha charges included)")
    tail = ("From tomorrow, live intraday tips only from: " + ", ".join(SETUP_WORDS.get(a, a) for a in allowed) + "."
            if allowed else "None passed - so NO live intraday tips from tomorrow (paper tracking continues). "
            "It re-tests every week; a setup that starts passing switches on by itself.")
    return "\n".join([head] + lines + [tail, "<i>Past results don't guarantee future ones. Research, not advice.</i>"])
