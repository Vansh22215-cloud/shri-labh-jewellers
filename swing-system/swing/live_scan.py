"""HOURLY market scan during trading hours -> structured Telegram message.

Each run (10:20, 11:20 ... 15:20 IST):
  1. Live snapshot (5-minute data so far today) for the ~500 most-traded NSE stocks + Nifty + your trades.
  2. Your open trades (my_trades.csv): live price vs stop / targets -> clear action alerts.
  3. Last evening's tips: is the price still inside the buy zone?
  4. NEW signals forming today, using the SAME strategy code as the backtest on a provisional
     "today so far" bar. They are only final at the close: the 6:40 pm report confirms them.
  5. Stocks closest to a buy signal (watchlist).
Every idea has a full plan and a risk score out of 10 (swing/risk_score.py).
"""
import html
import time
from datetime import datetime

import numpy as np
import pandas as pd
import yfinance as yf

from . import data_prices, engine, fundamentals, journal, risk_score, telegram, universe, health
from .config import DISCLAIMER, get_logger, load_settings, load_state, load_strategy, save_state
from .strategy import position_size, trade_plan

log = get_logger()
E = html.escape


def snapshot(symbols):
    """Today's open/high/low/last/volume so far, from 5-minute bars."""
    out = {k: {} for k in ("open", "high", "low", "close", "volume")}
    last_ts = None
    for i in range(0, len(symbols), 250):
        chunk = symbols[i:i + 250]
        tick = {data_prices.yahoo_ticker(s): s for s in chunk}
        try:
            raw = yf.download(list(tick), period="1d", interval="5m", group_by="ticker", progress=False, threads=True)
        except Exception as e:
            log.warning("live snapshot failed: %s", e)
            continue
        for t, s in tick.items():
            try:
                df = (raw[t] if len(tick) > 1 else raw).dropna(subset=["Close"])
            except KeyError:
                continue
            if df.empty:
                continue
            ts = df.index[-1].tz_convert("Asia/Kolkata").tz_localize(None)
            if ts.normalize() != pd.Timestamp.now(tz="Asia/Kolkata").tz_localize(None).normalize():
                continue
            last_ts = max(last_ts, ts) if last_ts is not None else ts
            out["open"][s] = float(df["Open"].iloc[0]); out["high"][s] = float(df["High"].max())
            out["low"][s] = float(df["Low"].min()); out["close"][s] = float(df["Close"].iloc[-1])
            out["volume"][s] = float(df["Volume"].sum())
    return {k: pd.Series(v, dtype=float) for k, v in out.items()}, last_ts


def _card(i, pl):
    rs = pl["risk"]
    bar = "🟩" * (10 - rs) + "🟥" * rs
    lines = [f"<b>{i}. {E(pl['symbol'])}</b>  <i>{E(pl.get('name') or '')}</i>",
             f"<b>Signal:</b> {E(pl['setup'])}  |  <b>Score</b> {pl['score']:.0f}/100",
             f"<b>Risk:</b> {rs}/10 {risk_score.label(rs)}  {bar}",
             f"<pre>Price now   ₹{pl['ltp']:,.2f}\nBuy zone    ₹{pl['entry_low']:,.2f} – ₹{pl['entry_high']:,.2f}\n"
             f"Stop-loss   ₹{pl['stop']:,.2f}  ({pl['stop_pct']:.1f}%)\nTarget 1    ₹{pl['target1']:,.2f}  (sell half)\n"
             f"Target 2    ₹{pl['target2']:,.2f}\nQuantity    {pl['qty']} sh  (≈₹{pl['qty'] * pl['ltp']:,.0f})\n"
             f"Max loss    ≈₹{pl['risk_rupees']:,.0f}\nHold        up to {pl['max_hold']} trading days</pre>",
             "<b>Why:</b> " + E("; ".join(pl["reasons"][:4])),
             "<b>Risk factors:</b> " + E("; ".join(pl["risk_reasons"]) or "none flagged")]
    return "\n".join(lines)


def run(send=True):
    settings = load_settings()
    capital = float(settings["capital"])
    from .nightly import gate_status
    live = settings.get("live_strategy", "v1")
    validated = gate_status(live).get("passed", False)
    sname = live if validated or settings.get("tips_mode") != "aggressive" else settings.get("aggressive_strategy", "a1")
    p = load_strategy(sname)
    now = pd.Timestamp.now(tz="Asia/Kolkata").tz_localize(None)

    hist = universe.load_history()
    from .tipcheck import equity_list
    eq = equity_list()
    names = dict(zip(eq["SYMBOL"], eq["NAME OF COMPANY"]))   # NSE equity list = company shares only (no ETFs)
    cur = [s for s in hist[hist["asof"] == hist["asof"].max()]["symbol"] if s in names]
    q = health.load_quarantine()
    my = journal.load_my_trades()
    tips = journal.load_tips()
    recent_tips = tips[(tips["kind"] == "tip") & tips["status"].isin(["pending", "open"])]
    syms = sorted({s for s in cur if s not in q} | set(my["symbol"]) | set(recent_tips["symbol"]))
    snap, last_ts = snapshot(syms + ["NIFTY50"])
    if last_ts is None or "NIFTY50" not in snap["close"]:
        msg = "Market closed today (no live prices). Next scan on the next trading day."
        log.info(msg)
        return msg
    nifty_now = float(snap["close"].pop("NIFTY50"))
    for k in ("open", "high", "low", "volume"):
        snap[k] = snap[k].drop("NIFTY50", errors="ignore")
    bar = {"date": now.normalize(), **snap, "nifty": nifty_now}
    P, sig, nifty, industry, cov, _ = engine.build(p, extra_bar=bar)
    d = P["close"].index[-1]
    member = sig["member"].loc[d]
    c = P["close"].loc[d]
    prev = P["close"].iloc[-2]
    market_ok = bool(sig["market_regime_ok"].loc[d])
    regime = bool(sig["regime_ok"].loc[d])
    n_prev = float(nifty.iloc[-2])
    adv = int(((c > prev) & member).sum()); dec = int(((c < prev) & member).sum())

    def plan_for(s, setup):
        close, a = float(c[s]), float(sig["atr"].at[d, s])
        lv = trade_plan(close, a, p)
        qty = position_size(capital, capital, close, lv["stop"], p)
        if qty < 1:
            return None
        tv = float((P["raw_close"][s] * P["volume"][s]).tail(60).median()) / 1e7
        s200 = sig["sma200"][s]
        rd = fundamentals.next_results_date(s, d)
        rdays = (rd - d).days if rd is not None else None
        ext = (close / float(sig["sma50"].at[d, s]) - 1) * 100
        rs_val, rs_why = risk_score.score(a / close * 100, tv, bool(close > s200.loc[d] and s200.loc[d] > s200.iloc[-21]),
                                          market_ok, rdays, ext, validated)
        reasons = [f"stronger than {sig['rs_rank'].at[d, s] * 100:.0f}% of top-500 stocks over 6 months",
                   "short-term trend just turned up while long-term trend is up" if "cross" in setup else setup,
                   f"next results {rd.date()}" if rd is not None else "results date unknown"]
        if (close - lv["stop"]) / close < 0.01:
            return None   # no real price movement (fund/ETF-like) - not a trade
        try:
            from .intel_fno import line as fno_line
            fl = fno_line(s)
            if fl:
                reasons.append(fl)
                if "SHORT BUILD-UP" in fl or "LONG UNWINDING" in fl:
                    rs_why.append("F&O shows selling (short build-up/long unwinding)")
        except Exception:
            pass
        return {"symbol": s, "name": names.get(s, ""), "setup": setup, "score": float(sig["score"].at[d, s]), "ltp": close, **lv, "qty": qty,
                "risk_rupees": qty * (close - lv["stop"]), "stop_pct": (close - lv["stop"]) / close * 100,
                "max_hold": p["max_hold_days"], "risk": rs_val, "risk_reasons": rs_why, "reasons": reasons}

    # NEW signals forming today (provisional)
    st = load_state()
    sent = set(st.get("scan_sent", {}).get(str(d.date()), []))
    forming = []
    if regime:
        el = sig["eligible"].loc[d]
        cands = [x for x in sig["score"].loc[d, el[el].index].sort_values(ascending=False).index if x in names]
        for s in cands[:8]:
            pl = plan_for(s, sig["setup"].at[d, s])
            if pl:
                pl["new"] = s not in sent
                forming.append(pl)
    # watchlist: closest to a moving-average-cross buy signal (uptrend, 20 EMA just below 50 SMA and rising)
    ema20, sma50 = sig["ema20"].loc[d], sig["sma50"].loc[d]
    gap = (sma50 / ema20 - 1) * 100
    near = member & c.index.isin(list(names)) & (c > sig["sma200"].loc[d]) & (gap > 0) & (gap < 1.0) & (ema20 > sig["ema20"].iloc[-2])
    watch = gap[near].sort_values().head(5)

    # your trades
    my_lines = []
    for _, t in my.iterrows():
        s = t["symbol"]
        if s not in snap["close"]:
            continue
        ltp, buy, stop = float(snap["close"][s]), float(t["buy_price"]), float(t["stop"])
        r = buy - stop
        t1, t2 = buy + p["target1_r"] * r, buy + p["target2_r"] * r
        pnl = (ltp - buy) * float(t["qty"])
        if snap["low"][s] <= stop:
            act = "🚨 <b>STOP-LOSS HIT</b> - your GTT should have sold. If not, SELL now."
        elif snap["high"][s] >= t2:
            act = "🎯 <b>TARGET 2 HIT</b> - sell remaining shares."
        elif snap["high"][s] >= t1:
            act = f"🎯 <b>TARGET 1 HIT</b> - sell half; move stop-loss up to ₹{buy:,.2f}."
        elif ltp - stop < 0.25 * r:
            act = "⚠️ Close to stop-loss - keep the GTT in place, don't average down."
        else:
            act = "✅ Hold. Nothing to do."
        my_lines.append(f"<b>{E(s)}</b>  {int(t['qty'])} sh @ ₹{buy:,.2f}\n<pre>Now ₹{ltp:,.2f} ({(ltp / buy - 1) * 100:+.2f}%)  "
                        f"P&amp;L ₹{pnl:+,.0f}\nStop ₹{stop:,.2f} | T1 ₹{t1:,.2f} | T2 ₹{t2:,.2f}</pre>{act}")

    # last evening's tips: still buyable?
    tip_lines = []
    for _, t in recent_tips.iterrows():
        s = t["symbol"]
        if s in snap["close"] and t["status"] == "pending":
            ltp = float(snap["close"][s])
            ok = t["entry_low"] <= ltp <= t["entry_high"]
            tip_lines.append(f"• <b>{E(s)}</b> ₹{ltp:,.2f} - " + ("✅ still inside buy zone" if ok else
                             ("❌ above buy zone - don't chase" if ltp > t["entry_high"] else "⚠️ below buy zone")))

    hdr = (f"📊 <b>MARKET SCAN</b>  {last_ts:%d %b %Y, %I:%M %p}\n"
           f"<pre>Nifty 50   {nifty_now:,.0f}  ({(nifty_now / n_prev - 1) * 100:+.2f}% today)\n"
           f"Breadth    {adv} up / {dec} down (top 500)\n"
           f"Market     {'HEALTHY' if market_ok else 'WEAK (below 200-day avg)'}\n"
           f"Strategy   {E(sname)} {'(validated)' if validated else '(NOT validated - aggressive mode)'}</pre>")
    bs = p.get("backtest_stats") or {}
    if bs.get("avg_win_rs"):
        hdr += (f"\n📐 <b>Per trade (13-yr test, after charges):</b> {bs['win_rate_pct']:.0f}% winners, avg win "
                f"₹{bs['avg_win_rs']:,}, avg loss ₹{-bs['avg_loss_rs']:,}, avg hold {bs['avg_days_held']:.0f} days, "
                f"~{bs['trades_per_month']} trades/month. Losing streaks of up to {bs['max_losing_streak']} happen.")
    from .research import today_line
    rl = today_line()
    from .intel_positioning import today_line as fii_line
    if fii_line():
        hdr += "\n🏦 <b>Big money:</b> " + E(fii_line())
    if rl:
        hdr += "\n🧭 <b>Market dynamics:</b> " + E(rl)
    blocks = [hdr]
    blocks.append("💼 <b>YOUR TRADES</b>\n" + ("\n".join(my_lines) if my_lines else "No open trades recorded."))
    if tip_lines:
        blocks.append("🌙 <b>LAST EVENING'S TIPS</b>\n" + "\n".join(tip_lines))
    if forming:
        blocks.append(f"🆕 <b>BUY SIGNALS FORMING TODAY</b> ({len(forming)})\n<i>Provisional until the close. "
                      "Final list comes at 6:40 pm; buy tomorrow at the open inside the buy zone. "
                      "Take at most 4 trades in total.</i>")
        for i, pl in enumerate(forming, 1):
            blocks.append(("🔔 NEW\n" if pl["new"] else "") + _card(i, pl))
    else:
        blocks.append("🆕 <b>BUY SIGNALS</b>\nNone right now" + ("" if regime else " (market filter says WEAK)") + ".")
    if len(watch):
        blocks.append("👀 <b>CLOSEST TO A BUY SIGNAL</b>\n" + "\n".join(
            f"• {E(s)} ₹{c[s]:,.2f} - 20-day avg {g:.2f}% below crossing up" for s, g in watch.items()))
    blocks.append(f"<i>{E(DISCLAIMER)}</i>")
    text = "\n\n⁣".join(blocks)
    st.setdefault("scan_sent", {})[str(d.date())] = sorted(sent | {pl["symbol"] for pl in forming})
    st["scan_sent"] = {k: v for k, v in st["scan_sent"].items() if k >= str((d - pd.Timedelta(days=7)).date())}
    st["last_scan"] = str(datetime.now())
    save_state(st)
    if send:
        res = telegram.send(settings, text, html=True)
        log.info("Hourly scan sent: %s (%d forming, %d trades)", res, len(forming), len(my_lines))
    return text
