"""Tip checker: judge a stock tip (e.g. forwarded from a Telegram channel) in seconds.

What it does (research, not advice):
  1. PARSE the message: stock, buy/sell, entry price or zone, stop-loss, targets, intraday or swing.
  2. LIVE price check: has the price already run past the entry, or fallen through the stop?
  3. BASE RATE from THIS stock's own last 5 years of daily prices: from any day's close, how often did
     the price reach the target distance BEFORE the stop distance within the holding window?
     (If both happen on the same day we assume the stop came first - conservative.)
  4. COSTS: the win rate needed to break even after Zerodha charges + slippage.
  5. RED FLAGS: no stop-loss, illiquid/small stock (typical pump-and-dump), surveillance series,
     results due, weak trend, stop too tight/wide, weak market.
  6. Every checked tip is saved to journal/forwarded_tips.csv and its real outcome is tracked,
     so we learn which tip sources are any good.
"""
import io
import math
import re
import time
from datetime import date

import numpy as np
import pandas as pd
import requests

from . import costs, data_prices, fundamentals
from .config import DATA, DISCLAIMER, EVENTS, JOURNAL, get_logger

log = get_logger()
TIPS_F = DATA / "forwarded_tips.csv"   # personal (channel names, messages): not in the public repo
STOPWORDS = {"BUY", "SELL", "SL", "TGT", "CMP", "NSE", "BSE", "TARGET", "TARGETS", "STOP", "LOSS", "ABOVE",
             "BELOW", "NEAR", "AT", "ON", "FOR", "THE", "AND", "OR", "INTRADAY", "SWING", "BTST", "STBT", "CALL",
             "ENTRY", "EXIT", "RANGE", "ZONE", "HOLD", "LONG", "SHORT", "TERM", "DAYS", "WEEK", "WEEKS", "ADD",
             "TO", "IN", "OF", "UP", "NEW", "BOOK", "PROFIT", "RS", "INR", "LTP", "PRICE", "TRADE", "STOCK",
             "TODAY", "TOMORROW", "NIFTY", "BANKNIFTY", "FUT", "CE", "PE", "OPTION", "OPTIONS", "AROUND", "ONLY",
             "IS", "A", "AN", "WITH", "STRONG", "BREAKOUT", "CHART", "VIEW", "POSITIONAL", "SAFE", "SURE", "SHOT",
             "JACKPOT", "MULTIBAGGER", "T1", "T2", "T3", "TG", "SLOSS", "STOPLOSS", "BUYING", "GOOD", "BEST"}


# ----------------------------------------------------------------------------- symbols
def equity_list():
    f = EVENTS / "equity_list.csv"
    if not f.exists() or (time.time() - f.stat().st_mtime) > 7 * 86400:
        try:
            r = requests.get("https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv",
                             headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
            r.raise_for_status()
            pd.read_csv(io.BytesIO(r.content)).to_csv(f, index=False)
        except Exception as e:
            log.warning("NSE equity list download failed: %s", e)
    df = pd.read_csv(f)
    df.columns = [c.strip() for c in df.columns]
    return df


def _norm_name(n):
    n = re.sub(r"[^A-Z0-9 ]", " ", str(n).upper())
    n = re.sub(r"\b(LIMITED|LTD|INDIA|THE|COMPANY|CORPORATION|CORP|INDUSTRIES|IND)\b", " ", n)
    return re.sub(r"\s+", " ", n).strip()


NUM = r"(\d[\d,]*(?:\.\d+)?)"


def _num(s):
    return float(s.replace(",", ""))


def parse(text, eq=None):
    """Extract a structured tip from free text. Missing fields are None."""
    eq = equity_list() if eq is None else eq
    syms = set(eq["SYMBOL"].astype(str))
    t = text.upper().replace("₹", " ").replace("RS.", " ").replace("@", " AT ")
    t = re.sub(r"[🔥🎯🚀✅📈📉💰⭐️👉➡️]", " ", t)
    tip = {"raw": text.strip()[:500], "symbol": None, "side": "buy", "entry_low": None, "entry_high": None,
           "stop": None, "targets": [], "horizon": "swing"}
    if re.search(r"\b(SELL|SHORT|STBT)\b", t) and not re.search(r"\bBUY\b", t):
        tip["side"] = "sell"
    if re.search(r"\b(INTRADAY|INTRA ?DAY|SCALP)\b", t):
        tip["horizon"] = "intraday"
    elif re.search(r"\b(BTST|STBT)\b", t):
        tip["horizon"] = "btst"
    elif re.search(r"\b(POSITIONAL|LONG ?TERM|INVEST)\b", t):
        tip["horizon"] = "positional"
    # symbol: hashtag, then word after BUY/SELL, then any known symbol, then company name
    words = [w for w in re.findall(r"#?[A-Z0-9][A-Z0-9&\-]{1,19}", t) if re.search(r"[A-Z]", w)]
    cands = [w.lstrip("#") for w in words if w.lstrip("#") in syms and w.lstrip("#") not in STOPWORDS]
    tagged = [w.lstrip("#") for w in words if w.startswith("#") and w.lstrip("#") in syms]
    after = re.findall(r"\b(?:BUY|SELL|SHORT)\s+#?([A-Z0-9][A-Z0-9&\-]{1,19})", t)
    after = [a for a in after if a in syms]
    for group in (tagged, after, cands):
        if group:
            tip["symbol"] = group[0]
            break
    if tip["symbol"] is None:
        norm_t = " " + _norm_name(t) + " "
        best = None
        for s, n in zip(eq["SYMBOL"], eq["NAME OF COMPANY"]):
            nn = _norm_name(n)
            if len(nn) >= 4 and f" {nn} " in norm_t and (best is None or len(nn) > len(best[1])):
                best = (s, nn)
        if best:
            tip["symbol"] = best[0]
    # stop-loss
    m = re.search(r"\b(?:SL|S\.L\.?|STOP ?LOSS|STOPLOSS|STOP)\b\s*[:\-=]?\s*(?:AT|BELOW|ABOVE)?\s*" + NUM, t)
    if m:
        tip["stop"] = _num(m.group(1))
    # targets: numbers after TGT/TARGET/T1.. (several, separated by / , - and)
    for m in re.finditer(r"\b(?:TGT|TARGETS?|TG|T\d)\b\s*[:\-=]?\s*((?:\d[\d,]*(?:\.\d+)?\s*(?:/|,|-|AND|&|\+|\s)\s*)*\d[\d,]*(?:\.\d+)?)", t):
        for x in re.findall(NUM, m.group(1)):
            v = _num(x)
            if v not in tip["targets"]:
                tip["targets"].append(v)
    # entry: number(s) after BUY/ENTRY/ABOVE/NEAR/AT/CMP/AROUND/RANGE/ZONE
    # the gap between keyword and number may not cross another keyword (TGT/SL) and may not hit the symbol's digits
    sym_t = t.replace(tip["symbol"], " SYMBOL ") if tip["symbol"] else t
    m = re.search(r"\b(?:BUY|SELL|SHORT|ENTRY|ABOVE|BELOW|NEAR|AT|CMP|AROUND|RANGE|ZONE)\b"
                  r"(?:(?!TGT|TARGET|\bSL\b|STOP|\bT\d)[^0-9]){0,25}?"
                  + NUM + r"(?:\s*(?:-|TO|–)\s*" + NUM + r")?", sym_t)
    if m:
        a = _num(m.group(1))
        b = _num(m.group(2)) if m.group(2) else a
        tip["entry_low"], tip["entry_high"] = min(a, b), max(a, b)
    # drop "numbers" that are clearly not prices (e.g. a target list swallowed the stop)
    if tip["stop"] in tip["targets"]:
        tip["targets"].remove(tip["stop"])
    return tip


# ----------------------------------------------------------------------------- evaluation
def live_price(symbol):
    try:
        import yfinance as yf
        fi = yf.Ticker(data_prices.yahoo_ticker(symbol)).fast_info
        p = float(fi["last_price"])
        if p > 0 and math.isfinite(p):
            return p
    except Exception as e:
        log.debug("live price failed %s: %s", symbol, e)
    return None


def history(symbol):
    df = data_prices.load(symbol)
    if df is None or (pd.Timestamp.today() - df.index[-1]).days > 5:
        data_prices.download_full([symbol], start=str((pd.Timestamp.today() - pd.DateOffset(years=6)).date()))
        df = data_prices.load(symbol)
    return df


def base_rate(df, up_pct, down_pct, horizon_days, side="buy", years=5):
    """Share of past days on which price moved +up_pct before -down_pct (buy) within horizon_days.
    Same-day touches of both count as a LOSS (conservative). Returns (win, loss, neither, n)."""
    df = df[df.index >= df.index[-1] - pd.DateOffset(years=years)]
    c, h, l = df["close"].values, df["high"].values, df["low"].values
    n = len(c) - horizon_days - 1
    if n < 100:
        return None
    win = loss = 0
    for i in range(n):
        base = c[i]
        up, dn = base * (1 + up_pct), base * (1 - down_pct)
        for k in range(i + 1, i + 1 + horizon_days):
            if side == "buy":
                hit_dn, hit_up = l[k] <= dn, h[k] >= up
            else:
                hit_dn, hit_up = h[k] >= base * (1 + down_pct), l[k] <= base * (1 - up_pct)
            if hit_dn:
                loss += 1
                break
            if hit_up:
                win += 1
                break
    return win / n, loss / n, 1 - (win + loss) / n, n


def evaluate(tip, capital=45000.0):
    """Return (verdict, list of reasons, details dict)."""
    reasons, flags, details = [], [], {}
    sym = tip.get("symbol")
    if not sym:
        return "UNKNOWN", ["I could not find an NSE stock symbol in this message. Try e.g. 'BUY TATASTEEL 150 SL 145 TGT 160'."], {}
    eq = equity_list()
    row = eq[eq["SYMBOL"] == sym]
    series = str(row[" SERIES"].iloc[0] if " SERIES" in row else row["SERIES"].iloc[0]).strip() if len(row) else "?"
    df = history(sym)
    if df is None or len(df) < 150:
        return "AVOID", [f"{sym}: not enough reliable price history (new or illiquid stock)."], {}
    a = data_prices.adjusted(df)
    last_close = float(df["close"].iloc[-1])
    ltp = live_price(sym) or last_close
    details["ltp"] = round(ltp, 2)
    side = tip.get("side", "buy")
    sgn = 1 if side == "buy" else -1
    entry = tip.get("entry_high") or tip.get("entry_low") or ltp
    if tip.get("entry_low") and tip.get("entry_high"):
        entry = (tip["entry_low"] + tip["entry_high"]) / 2
    # sanity: entry must be near the real price (catches wrong symbol or old tips)
    if abs(entry / ltp - 1) > 0.10:
        reasons.append(f"Entry {entry:g} is far from today's price {ltp:.2f} - wrong stock, very old tip, or a typo.")
        flags.append("AVOID")
    tr = np.maximum(df["high"] - df["low"], np.maximum((df["high"] - df["close"].shift()).abs(),
                                                       (df["low"] - df["close"].shift()).abs()))
    atr = float(tr.rolling(14).mean().iloc[-1])
    details["atr"] = round(atr, 2)
    # liquidity & surveillance (pump-and-dump protection)
    tv = float((df["close"] * df["volume"]).tail(60).median())
    details["median_daily_value_cr"] = round(tv / 1e7, 1)
    if tv < 5e7:
        reasons.append(f"Very illiquid: only ~Rs {tv/1e7:.1f} crore traded a day. Tips on small, thinly traded stocks "
                       "are the classic Telegram pump-and-dump (SEBI has acted against such channels).")
        flags.append("AVOID")
    elif tv < 5e8:
        reasons.append(f"Small/less liquid stock (~Rs {tv/1e7:.0f} crore a day): bigger gaps and slippage.")
        flags.append("CAUTION")
    if series not in ("EQ", "?"):
        reasons.append(f"Trades in the '{series}' series (trade-to-trade / surveillance) - higher risk.")
        flags.append("AVOID")
    # stop-loss
    stop = tip.get("stop")
    if stop is None:
        stop = entry - sgn * 2 * atr
        reasons.append(f"No stop-loss given. A tip without a stop is a red flag. If you take it, use about {stop:.2f} (2x daily range).")
        flags.append("CAUTION")
    risk = (entry - stop) * sgn
    if risk <= 0:
        return "AVOID", [f"The stop-loss {stop:g} is on the wrong side of the entry {entry:g}."], details
    if (ltp - stop) * sgn <= 0:
        reasons.append(f"Price {ltp:.2f} is already beyond the stop-loss {stop:g}: the tip has already failed.")
        flags.append("AVOID")
    stop_atr = risk / atr
    details["stop_atr"] = round(stop_atr, 2)
    horizon = {"intraday": 1, "btst": 2, "swing": 10, "positional": 40}[tip.get("horizon", "swing")]
    if tip.get("horizon") == "intraday" and stop_atr < 0.3:
        reasons.append("Stop is extremely tight even for intraday - likely to be hit by normal noise.")
        flags.append("CAUTION")
    elif tip.get("horizon") != "intraday" and stop_atr < 0.7:
        reasons.append(f"Stop is very tight ({stop_atr:.1f}x the normal daily move) - normal noise will likely hit it.")
        flags.append("CAUTION")
    if stop_atr > 5:
        reasons.append(f"Stop is very wide ({risk / entry * 100:.1f}% away) - a big loss if it fails.")
        flags.append("CAUTION")
    targets = [x for x in tip.get("targets", []) if (x - entry) * sgn > 0]
    if not targets:
        targets = [entry + sgn * 1.5 * risk]
        reasons.append("No valid target given; using 1.5x the risk as a reference target.")
    t1 = targets[0]
    reward = (t1 - entry) * sgn
    rr = reward / risk
    details.update({"entry": round(entry, 2), "stop": round(stop, 2), "target": round(t1, 2), "rr": round(rr, 2)})
    # already ran away?
    run = (ltp - entry) * sgn / entry * 100
    if run > 1.5:
        reasons.append(f"Price {ltp:.2f} has already moved {run:.1f}% past the entry - chasing it worsens the odds.")
        flags.append("CAUTION")
    # costs: per-share rupees for a round trip
    if tip.get("horizon") == "intraday":
        from .intraday import mis_costs
        cost_ps = mis_costs(entry * 100, entry * 100) / 100 + 2 * 0.0005 * entry
    else:
        cost_ps = (costs.buy_cost(entry * 100) + costs.sell_cost(entry * 100)) / 100 + 2 * costs.SLIPPAGE_PCT * entry
    need = (risk + cost_ps) / (reward + risk)        # win rate needed to break even after costs
    details["breakeven_win_pct"] = round(need * 100, 1)
    br = base_rate(df, reward / entry, risk / entry, horizon, side)
    if br:
        win, loss, neither, n = br
        decided = win + loss
        p = win / decided if decided > 0 else 0
        details.update({"hist_target_first_pct": round(p * 100, 1), "hist_samples": n,
                        "hist_unresolved_pct": round(neither * 100, 1)})
        ev_r = (p * (reward - cost_ps) - (1 - p) * (risk + cost_ps)) / risk
        details["expected_r"] = round(ev_r, 2)
        reasons.insert(0, f"History (last 5 yrs of {sym}): a move to the target before the stop happened "
                          f"{p*100:.0f}% of the time (within {horizon} trading day{'s' if horizon > 1 else ''}); "
                          f"after charges you need {need*100:.0f}% to break even.")
        if p < need - 0.05:
            flags.append("AVOID")
        elif p < need + 0.05:
            flags.append("CAUTION")
    # trend & market
    s50, s200 = a["close"].rolling(50).mean().iloc[-1], a["close"].rolling(200).mean().iloc[-1]
    cl = a["close"].iloc[-1]
    if side == "buy" and cl < s200:
        reasons.append("Stock is below its 200-day average (long-term downtrend) - buying against the trend.")
        flags.append("CAUTION")
    if side == "buy" and cl > s50 > s200:
        reasons.append("Trend is up (above rising 50- and 200-day averages).")
    nifty = data_prices.load("NIFTY50")
    if nifty is not None and side == "buy":
        nc = nifty["close"]
        if nc.iloc[-1] < nc.rolling(200).mean().iloc[-1]:
            reasons.append("Overall market (Nifty) is below its 200-day average - most stocks struggle then.")
            flags.append("CAUTION")
    # results
    try:
        rd = fundamentals.next_results_date(sym)
        if rd is not None and (rd - pd.Timestamp.today().normalize()).days <= 7:
            reasons.append(f"Results due {rd.date()}: big gap risk.")
            flags.append("CAUTION")
    except Exception:
        pass
    try:   # news headlines about the stock (ROADMAP I4)
        from .intel_news import fetch as _nf, line as _nl
        _nf()
        nl = _nl(sym, row["NAME OF COMPANY"].iloc[0] if len(row) else "")
        if nl:
            reasons.append(nl)
            if "RED FLAG" in nl:
                flags.append("CAUTION")
    except Exception:
        pass
    qty = int(max(0, min(capital * 0.01 / risk, capital * 0.25 / entry)))
    details["qty_1pct_risk"] = qty
    verdict = "AVOID" if "AVOID" in flags else ("RISKY" if flags.count("CAUTION") >= 1 else "GOOD")
    if verdict == "GOOD" and (not br or rr < 1.2):
        verdict = "RISKY"
    return verdict, reasons, details


def format_reply(tip, verdict, reasons, d):
    icon = {"GOOD": "🟢", "RISKY": "🟡", "AVOID": "🔴", "UNKNOWN": "⚪"}[verdict]
    lines = [f"{icon} {verdict}: {tip.get('symbol') or '?'} ({tip.get('side', 'buy').upper()}, {tip.get('horizon')})"]
    if d.get("entry"):
        lines.append(f"Price now {d.get('ltp')} | entry {d['entry']} | stop {d['stop']} | target {d['target']} | reward:risk {d['rr']}")
    if d.get("hist_target_first_pct") is not None:
        lines.append(f"Odds from history: {d['hist_target_first_pct']}% vs {d['breakeven_win_pct']}% needed; "
                     f"expected {d.get('expected_r'):+} R per trade after charges")
    lines += [f"• {r}" for r in reasons[:7]]
    if d.get("qty_1pct_risk"):
        lines.append(f"If you still take it: max {d['qty_1pct_risk']} shares (risking 1% of your capital).")
    lines.append(DISCLAIMER)
    return "\n".join(lines)


def check_text(text, source="", capital=45000.0):
    from . import options_check
    o = options_check.parse_option(text)
    if o and o.get("symbol"):
        verdict, reasons, d = options_check.evaluate_option(o, capital)
        save({"symbol": o["symbol"], "side": f"{o['strike']:g} {o['kind']}", "horizon": "option",
              "raw": o["raw"]}, verdict, {"entry": d.get("premium"), "stop": o.get("stop"),
                                           "target": (o.get("targets") or [None])[0], "ltp": d.get("spot"),
                                           "hist_target_first_pct": d.get("hist_pct"),
                                           "breakeven_win_pct": d.get("need_pct"), "expected_r": d.get("expected_r")},
             source, outcome="n/a (option - outcome not tracked yet)")
        return options_check.format_option_reply(o, verdict, reasons, d)
    tip = parse(text)
    verdict, reasons, d = evaluate(tip, capital)
    save(tip, verdict, d, source)
    return format_reply(tip, verdict, reasons, d)


def save(tip, verdict, d, source, outcome=None):
    row = {"checked": str(pd.Timestamp.now().round("s")), "source": source, "symbol": tip.get("symbol"),
           "side": tip.get("side"), "horizon": tip.get("horizon"), "verdict": verdict,
           "entry": d.get("entry"), "stop": d.get("stop"), "target": d.get("target"), "ltp": d.get("ltp"),
           "hist_pct": d.get("hist_target_first_pct"), "need_pct": d.get("breakeven_win_pct"),
           "expected_r": d.get("expected_r"),
           "outcome": outcome or ("open" if tip.get("symbol") else "n/a"),
           "raw": tip.get("raw", "").replace("\n", " ")[:300]}
    df = pd.read_csv(TIPS_F) if TIPS_F.exists() else pd.DataFrame()
    pd.concat([df, pd.DataFrame([row])], ignore_index=True).to_csv(TIPS_F, index=False)


def update_outcomes():
    """Did each forwarded tip hit its target or its stop first? (daily bars, stop-first if both)."""
    if not TIPS_F.exists():
        return pd.DataFrame()
    df = pd.read_csv(TIPS_F)
    for i, r in df.iterrows():
        if r.get("outcome") != "open" or pd.isna(r.get("entry")):
            continue
        h = data_prices.load(r["symbol"])
        if h is None:
            continue
        since = h[h.index > pd.Timestamp(r["checked"]).normalize()]
        horizon = {"intraday": 1, "btst": 2, "swing": 10, "positional": 40}.get(r["horizon"], 10)
        sgn = 1 if r["side"] == "buy" else -1
        for k, (d, bar) in enumerate(since.iterrows()):
            hit_stop = (bar["low"] <= r["stop"]) if sgn == 1 else (bar["high"] >= r["stop"])
            hit_tgt = (bar["high"] >= r["target"]) if sgn == 1 else (bar["low"] <= r["target"])
            if hit_stop:
                df.at[i, "outcome"] = "stop"; break
            if hit_tgt:
                df.at[i, "outcome"] = "target"; break
            if k + 1 >= horizon:
                df.at[i, "outcome"] = "expired"; break
    df.to_csv(TIPS_F, index=False)
    return df


def source_scorecard():
    """How have forwarded tips done, by source and by our verdict?"""
    if not TIPS_F.exists():
        return {}
    df = update_outcomes()
    done = df[df["outcome"].isin(["target", "stop", "expired"])]
    if len(done) == 0:
        return {}
    by = lambda col: {k: {"tips": int(len(g)), "target_hit_pct": round((g["outcome"] == "target").mean() * 100, 1),
                          "stop_hit_pct": round((g["outcome"] == "stop").mean() * 100, 1)}
                      for k, g in done.groupby(col)}
    return {"by_source": by("source"), "by_verdict": by("verdict")}
