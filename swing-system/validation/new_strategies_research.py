"""NEW TRADE-FINDING METHODS (owner 17 Nov: "find other smarter and best ways of finding trades... do tests").

Well-known, published swing methods with their TEXTBOOK settings (no parameter search on our data), tested with the
same independent simulator as BACKTEST_VALIDATION.md: point-in-time top-300, delisted stocks rebuilt from NSE files,
ETFs excluded, signal at the close -> entry at the NEXT OPEN, gap-adjusted stops, 0.35% costs per round trip.

PASS BAR - fixed BEFORE the first run (a method goes live only if it meets ALL of these):
  1. after costs, expectancy > 0 AND the 95% confidence interval's lower end > 0
  2. out-of-sample (Nov 2023 onwards, never looked at while choosing): expectancy > 0 on >= 100 trades
  3. beats the average stock held over the same days, after costs, in >= 60% of years
  4. profit factor >= 1.3
  5. still positive with 0.60% costs (slippage stress)

Methods:
  BRK52  52-week-high breakout on volume (O'Neil / Darvas): close above the highest high of the prior 250 days,
         volume >= 1.5x its 50-day average, close above the 200-day average. Exit: close below the 50-day average.
         Stop 3 ATR, max 60 days.
  TREND  Minervini trend template + 20-day breakout: close > 50d > 150d > 200d average, 200d rising for a month,
         >= 30% above the 52-week low, within 25% of the 52-week high, 6-month strength in the market's top 30%,
         close above the prior 20-day high. Exit: close below the 50-day average. Stop 3 ATR, max 60 days.
  PULL   Leader pullback: 6-month strength in the top 20%, above the 200-day average, the day's low touches the
         20-day EMA and the close is back above it on an up day. Exit: close below the 50-day average or 20 days.
         Stop 2.5 ATR.
  GAP    Gap-and-go (news/earnings drift proxy): opens >= 4% above the previous close on >= 3x average volume,
         closes above its open in the top 30% of the day's range, above the 200-day average. Hold 20 days, stop 3 ATR.
  TURTLE Turtle 55-day breakout: close above the prior 55-day high, above the 200-day average. Exit: close below
         the prior 20-day low. Stop 2 ATR (2N), max 120 days.
  VCP    Volatility contraction breakout: the last 20 days' range <= 12% of price, within 5% of the 52-week high,
         close > 50d > 200d average, close above the prior 20-day high on >= 1.5x volume. Exit: close below the
         50-day average. Stop 3 ATR, max 60 days.
Output: validation/new_strategies.json, validation/new_trades_<NAME>.csv
"""
import json
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd

ROOT = "/home/user/shri-labh-jewellers/swing-system"
sys.path.insert(0, ROOT)
sys.path.insert(0, f"{ROOT}/validation")
import independent_validation as iv  # noqa: E402

RS = None          # cross-sectional 6-month strength rank (0-1) of every stock vs the universe, per day


def _sma(x, n):
    return x.rolling(n).mean()


def _base(d):
    c, h, l, o, v = d["close"], d["high"], d["low"], d["open"], d["volume"]
    return c, h, l, o, v


def s_brk52(sym, d, m):
    c, h, l, o, v = _base(d)
    ent = (c > h.shift(1).rolling(250).max()) & (v >= 1.5 * _sma(v, 50).shift(1)) & (c > _sma(c, 200))
    return ent.values & m, (c < _sma(c, 50)).values, 3.0, 60


def s_trend(sym, d, m):
    c, h, l, o, v = _base(d)
    s50, s150, s200 = _sma(c, 50), _sma(c, 150), _sma(c, 200)
    rs = RS[sym].reindex(d.index) if sym in RS else pd.Series(np.nan, index=d.index)
    ent = ((c > s50) & (s50 > s150) & (s150 > s200) & (s200 > s200.shift(21)) & (c >= 1.3 * l.rolling(250).min())
           & (c >= 0.75 * h.rolling(250).max()) & (rs >= 0.7) & (c > h.shift(1).rolling(20).max()))
    return ent.values & m, (c < s50).values, 3.0, 60


def s_pull(sym, d, m):
    c, h, l, o, v = _base(d)
    e20 = c.ewm(span=20, adjust=False).mean()
    rs = RS[sym].reindex(d.index) if sym in RS else pd.Series(np.nan, index=d.index)
    ent = (rs >= 0.8) & (c > _sma(c, 200)) & (l <= e20) & (c > e20) & (c > o)
    return ent.values & m, (c < _sma(c, 50)).values, 2.5, 20


def s_gap(sym, d, m):
    c, h, l, o, v = _base(d)
    pc = c.shift(1)
    rng = (h - l).replace(0, np.nan)
    ent = ((o >= 1.04 * pc) & (v >= 3 * _sma(v, 50).shift(1)) & (c > o) & ((c - l) / rng >= 0.7)
           & (c > _sma(c, 200)))
    return ent.values & m, None, 3.0, 20


def s_turtle(sym, d, m):
    c, h, l, o, v = _base(d)
    ent = (c > h.shift(1).rolling(55).max()) & (c > _sma(c, 200))
    return ent.values & m, (c < l.shift(1).rolling(20).min()).values, 2.0, 120


def s_vcp(sym, d, m):
    c, h, l, o, v = _base(d)
    tight = (h.rolling(20).max().shift(1) - l.rolling(20).min().shift(1)) / c <= 0.12
    ent = (tight & (c >= 0.95 * h.rolling(250).max()) & (c > _sma(c, 50)) & (_sma(c, 50) > _sma(c, 200))
           & (c > h.shift(1).rolling(20).max()) & (v >= 1.5 * _sma(v, 50).shift(1)))
    return ent.values & m, (c < _sma(c, 50)).values, 3.0, 60


METHODS = {"BRK52": s_brk52, "TREND": s_trend, "PULL": s_pull, "GAP": s_gap, "TURTLE": s_turtle, "VCP": s_vcp}


def _one(args):
    name, sym, d, m, src = args
    try:
        ent, ex, stop, days = METHODS[name](sym, d, m)
        ent = np.asarray(ent, bool)
        return iv.simulate(sym, d, ent, None if ex is None else np.asarray(ex, bool), stop, days, src) if ent.any() else []
    except Exception as e:
        return [{"error": f"{sym}: {type(e).__name__}: {e}"}]


def verdict(r):
    a, oos, st = r["after_costs"], r["out_of_sample_2023_11_on"], r["cost_stress_0.60pct"]
    yrs = r["excess_vs_average_stock_by_year_pct"]
    beat = sum(1 for v in yrs.values() if v > 0) / max(1, len(yrs))
    checks = {
        "1 expectancy>0 and CI lower>0": a.get("trades", 0) > 0 and a["expectancy_ci95_pct"][0] > 0,
        "2 out-of-sample >0 on >=100 trades": oos.get("trades", 0) >= 100 and oos["expectancy_pct"] > 0,
        "3 beats average stock >=60% of years": beat >= 0.6,
        "4 profit factor >=1.3": (a.get("profit_factor") or 0) >= 1.3,
        "5 positive at 0.60% costs": st.get("trades", 0) > 0 and st["expectancy_pct"] > 0,
    }
    return all(checks.values()), checks, round(beat * 100)


if __name__ == "__main__":
    data = list(iv.universe(include_delisted=True))
    print(f"universe: {len(data)} stocks", file=sys.stderr)
    raw = pd.DataFrame({s: d["close"] for s, d, m, src in data}).sort_index()
    member = pd.DataFrame({s: pd.Series(m, index=d.index) for s, d, m, src in data}).reindex(raw.index).fillna(False).astype(bool)
    RS = (raw / raw.shift(126) - 1).where(member).rank(axis=1, pct=True)
    close_panel = (raw, member)
    nclose = iv.nifty()["close"]
    res = {}
    with Pool(4) as p:
        for name in METHODS:
            trades = []
            for r in p.imap_unordered(_one, [(name, s, d, m, src) for s, d, m, src in data], chunksize=4):
                trades += r
            errs = [t for t in trades if "error" in t]
            T = pd.DataFrame([t for t in trades if "error" not in t])
            T.to_csv(f"{ROOT}/validation/new_trades_{name}.csv", index=False)
            r = iv.report_strategy(T, close_panel, nclose)
            ok, checks, beat = verdict(r)
            r.update(errors=len(errs), PASS=ok, checks=checks, years_beating_average_pct=beat,
                     trades_per_year=round(len(T) / 13.9, 1))
            res[name] = r
            a = r["after_costs"]
            print(f"{name}: {'PASS' if ok else 'fail'} n={a.get('trades')} win={a.get('win_pct')} exp={a.get('expectancy_pct')} "
                  f"ci={a.get('expectancy_ci95_pct')} pf={a.get('profit_factor')} oos={r['out_of_sample_2023_11_on'].get('expectancy_pct')} "
                  f"beat={beat}% errs={len(errs)}", file=sys.stderr)
    res["_method"] = __doc__
    json.dump(res, open(f"{ROOT}/validation/new_strategies.json", "w"), indent=1, default=str)
