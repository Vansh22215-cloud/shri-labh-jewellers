"""INDEPENDENT BACKTEST VALIDATION (audit 17 Nov 2026) -> validation/independent_validation.json + BACKTEST_VALIDATION.md

Re-tests every live strategy with ONE independent trade simulator, stricter than the original research:
  * point-in-time top-300 universe (monthly, from NSE bhavcopies, data before each month only)
  * SURVIVORSHIP: delisted / merged / collapsed stocks added back from NSE's own daily files
    (data/delisted_prices.csv.gz, see survivorship_data.py) - results are shown with AND without them
  * signal on day t's close -> entry at day t+1's OPEN (the price the owner can actually get)
  * stop-loss: if a day OPENS below the stop the fill is that open (gap), otherwise the stop price
  * costs 0.35% round trip (delivery STT 0.1%+0.1%, exchange/SEBI/stamp/GST ~0.05%, slippage ~0.1%) and a stress
    case at 0.60%
  * every trade kept: no filtering of losers, no parameter search in this file
Metrics per strategy: trades, win rate, average win / loss, expectancy, profit factor, max drawdown and longest
losing streak of a 1%-risk-per-trade account, best / worst year, by market regime, before / after costs, versus the
average stock and Nifty over the same holding days, 95% confidence interval, development vs out-of-sample.
"""
import json
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd

ROOT = "/home/user/shri-labh-jewellers/swing-system"
sys.path.insert(0, ROOT)
from swing import data_prices  # noqa: E402

COST, COST_STRESS, OOS = 0.0035, 0.0060, "2023-11-01"
DELISTED_F = f"{ROOT}/data/delisted_prices.csv.gz"


def _delisted():
    try:
        d = pd.read_csv(DELISTED_F, parse_dates=["date"])
        return {s: g.set_index("date").sort_index() for s, g in d.groupby("symbol")}
    except Exception:
        return {}


def universe(include_delisted=True):
    u = pd.read_csv(f"{ROOT}/data/universe_history.csv", parse_dates=["asof"])
    u = u[u["rank"] <= 300]
    members = {a: set(g["symbol"]) for a, g in u.groupby("asof")}
    months = sorted(members)
    dl = _delisted() if include_delisted else {}
    for sym in sorted(set(u["symbol"])):
        d0 = data_prices.load(sym)
        src = "yahoo"
        if (d0 is None or not len(d0)) and sym in dl:
            d0, src = dl[sym], "nse"
        if d0 is None or len(d0) < 260:
            continue
        if "adj_close" not in d0:
            d0 = d0.assign(adj_close=d0["close"])
        f = (d0["adj_close"] / d0["close"]).fillna(1.0)
        d = pd.DataFrame({"open": d0["open"] * f, "high": d0["high"] * f, "low": d0["low"] * f,
                          "close": d0["adj_close"], "volume": d0["volume"]}).dropna()
        d = d[(d.index >= "2012-01-01") & (d[["open", "high", "low", "close"]] > 0).all(axis=1)]
        if len(d) < 260:
            continue
        m = np.zeros(len(d), bool)
        for i, a in enumerate(months):
            b = months[i + 1] if i + 1 < len(months) else pd.Timestamp("2100-01-01")
            if sym in members[a]:
                m |= (d.index >= a) & (d.index < b)
        yield sym, d, m, src


def atr(d, n=14):
    c = d["close"]
    tr = pd.concat([d["high"] - d["low"], (d["high"] - c.shift()).abs(), (d["low"] - c.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean().values


def simulate(sym, d, entries, exit_rule, stop_atr, max_days, src):
    """entries / exit_rule: bool arrays on the signal day. Returns list of trade dicts."""
    o, h, l, c = (d[k].values for k in ("open", "high", "low", "close"))
    a = atr(d)
    out, i, n = [], 0, len(d)
    while i < n - 2:
        if not entries[i] or not np.isfinite(a[i]):
            i += 1
            continue
        e = o[i + 1]
        stop = e - stop_atr * a[i]
        if stop <= 0:
            i += 1
            continue
        j, px, why = i + 1, None, None
        while j < n:
            if o[j] <= stop and j > i + 1:
                px, why = o[j], "gap through stop"
                break
            if l[j] <= stop:
                px, why = min(stop, o[j]), "stop"
                break
            if j + 1 < n and ((exit_rule is not None and exit_rule[j]) or j - (i + 1) >= max_days - 1):
                px, why = o[j + 1], "rule" if exit_rule is not None and exit_rule[j] else "time"
                j += 1
                break
            j += 1
        if px is None:
            break
        out.append({"sym": sym, "signal": d.index[i], "entry_date": d.index[i + 1], "exit_date": d.index[min(j, n - 1)],
                    "entry": e, "exit": px, "gross": px / e - 1, "stop_pct": (e - stop) / e, "why": why, "src": src,
                    "days": int(min(j, n - 1) - (i + 1))})
        i = j
    return out


# ----------------------------------------------------------------------------- strategies (production rules)
_NIFTY = None


def nifty():
    global _NIFTY
    if _NIFTY is None:
        n = data_prices.load("NIFTY50")["close"]
        from swing.high_prob import rsi
        _NIFTY = pd.DataFrame({"close": n, "up200": n > n.rolling(200).mean(), "rsi2": rsi(n)})
    return _NIFTY


def strat_dip(sym, d, m, src):
    from swing.confirmations import msb_order_block, squeeze_on, swing_low_hold, vix_fix_spike, wavetrend_oversold
    from swing.high_prob import rsi
    from swing.orderflow import order_block_touches
    c = d["close"]
    N = nifty().reindex(d.index)
    sig = ((c >= 1.10 * c.rolling(200).mean()) & (rsi(c) < 2)).values & N["up200"].fillna(False).values \
        & (N["rsi2"].values < 20) & m
    if not sig.any():
        return []
    o, h, l, cv = (d[k].values for k in ("open", "high", "low", "close"))
    fear = vix_fix_spike(h, l, cv)
    sqz = squeeze_on(h, l, cv)
    ob = pd.Series(order_block_touches(d)[0]).rolling(3, min_periods=1).max().fillna(0).astype(bool).values
    zone = ob | wavetrend_oversold(h, l, cv) | msb_order_block(o, h, l, cv) | swing_low_hold(o, h, l, cv)
    tiered = sig & ~sqz & (fear | zone)
    ex = (c > c.rolling(5).mean()).values
    return simulate(sym, d, tiered, ex, 4.0, 10, src)


def strat_pos(sym, d, m, src):
    from swing.rolling_profile import signals
    s = signals(d[["open", "high", "low", "close", "volume"]], "price")
    c = d["close"]
    ent = s["buy"].values & (c >= 0.9 * c.rolling(250).max()).values & m
    return simulate(sym, d, ent, s["sell"].values, 5.0, 60, src) if ent.any() else []


STRATS = {"DIP": strat_dip, "POS": strat_pos}


def _one(args):
    name, sym, d, m, src = args
    try:
        return STRATS[name](sym, d, m, src)
    except Exception as e:
        return [{"error": f"{sym}: {type(e).__name__}: {e}"}]


# ----------------------------------------------------------------------------- AI + discovered (panel based)
def ai_and_disc_trades(data):
    """AI: walk-forward predictions (validation/ml_preds.parquet, each year predicted by a model trained only on
    earlier data); top-5 every day, next open, 10-day hold, 4 ATR stop. DISC S1: its exact rule, fresh signals."""
    out = {"AI": [], "DISC_S1": []}
    try:
        pr = pd.read_parquet(f"{ROOT}/validation/ml_preds.parquet")
    except Exception:
        pr = None
    by = {s: (d, m, src) for s, d, m, src in data}
    if pr is not None:
        top = pr.sort_values(["date", "pred"], ascending=[True, False]).groupby("date").head(5)
        picks = top.groupby("sym")["date"].apply(set).to_dict()
        for sym, dates in picks.items():
            if sym not in by:
                continue
            d, m, src = by[sym]
            ent = d.index.isin(list(dates)) & m
            out["AI"] += simulate(sym, d, ent, None, 4.0, 10, src)
    try:
        from swing.ml_ranker import _finish, _market, features
        rows = []
        for sym, (d, m, src) in by.items():
            f = features(d)[m]
            f["sym"] = sym
            rows.append(f)
        P = pd.concat(rows)
        P.index.name = "date"
        P, X = _finish(P.reset_index(), _market())
        rule = (X["d200"] > 0.8) & (X["rngpos"] < 0.2) & (X["rsi14"] > 0.8)
        hits = P.loc[rule.values, ["date", "sym"]]
        for sym, g in hits.groupby("sym"):
            d, m, src = by[sym]
            ent = d.index.isin(set(g["date"]))
            prev = np.r_[False, ent[:-1]]
            out["DISC_S1"] += simulate(sym, d, ent & ~prev & m, None, 4.0, 20, src)
    except Exception as e:
        print("DISC failed:", e, file=sys.stderr)
    return out


# ----------------------------------------------------------------------------- metrics
def drift_and_bench(trades, data_close, nifty_close):
    """Average-stock and Nifty return over each trade's exact holding window (same entry/exit days)."""
    avg = data_close.mean(axis=1)
    out_a, out_n = [], []
    for t in trades.itertuples():
        try:
            out_a.append(avg.loc[t.exit_date] / avg.loc[t.entry_date] - 1)
        except KeyError:
            out_a.append(np.nan)
        try:
            out_n.append(nifty_close.asof(t.exit_date) / nifty_close.asof(t.entry_date) - 1)
        except Exception:
            out_n.append(np.nan)
    return np.array(out_a), np.array(out_n)


def metrics(T, cost):
    if not len(T):
        return {"trades": 0}
    r = T["gross"] - cost
    R = r / T["stop_pct"].clip(lower=0.005)                     # result in units of the 1%-risk stop distance
    eq = (R * 0.01).groupby(T["exit_date"]).sum().sort_index().cumsum()   # account at 1% risk per trade
    dd = float((eq - eq.cummax()).min() * 100)
    streak = best = 0
    for v in r.loc[T["exit_date"].sort_values().index]:
        streak = streak + 1 if v <= 0 else 0
        best = max(best, streak)
    wins, losses = r[r > 0], r[r <= 0]
    yr = r.groupby(T["entry_date"].dt.year).mean() * 100
    se = r.std(ddof=1) / np.sqrt(len(r)) if len(r) > 1 else np.nan
    return {"trades": int(len(r)), "win_pct": round(float((r > 0).mean() * 100), 1),
            "avg_win_pct": round(float(wins.mean() * 100), 2) if len(wins) else None,
            "avg_loss_pct": round(float(losses.mean() * 100), 2) if len(losses) else None,
            "expectancy_pct": round(float(r.mean() * 100), 2),
            "expectancy_ci95_pct": [round(float((r.mean() - 1.96 * se) * 100), 2), round(float((r.mean() + 1.96 * se) * 100), 2)],
            "profit_factor": round(float(wins.sum() / -losses.sum()), 2) if len(losses) and losses.sum() < 0 else None,
            "max_drawdown_pct_at_1pct_risk": round(dd, 1), "longest_losing_streak": int(best),
            "best_year": [int(yr.idxmax()), round(float(yr.max()), 2)], "worst_year": [int(yr.idxmin()), round(float(yr.min()), 2)],
            "losing_years": int((yr < 0).sum()), "years": int(len(yr)),
            "avg_days_held": round(float(T["days"].mean()), 1),
            "gap_through_stop_pct": round(float((T["why"] == "gap through stop").mean() * 100), 1)}


def report_strategy(T, close_panel, nclose):
    if not len(T):
        return {"trades": 0}
    T = T.copy()
    T["entry_date"] = pd.to_datetime(T["entry_date"])
    T["exit_date"] = pd.to_datetime(T["exit_date"])
    a, nb = drift_and_bench(T, close_panel, nclose)
    T["vs_avg_stock"], T["vs_nifty"] = T["gross"] - a, T["gross"] - nb
    up = nifty()["up200"].reindex(T["entry_date"]).fillna(False).values
    out = {"after_costs": metrics(T, COST), "before_costs": metrics(T, 0.0), "cost_stress_0.60pct": metrics(T, COST_STRESS),
           "development_before_2023_11": metrics(T[T["entry_date"] < OOS], COST),
           "out_of_sample_2023_11_on": metrics(T[T["entry_date"] >= OOS], COST),
           "regime_nifty_above_200d": metrics(T[up], COST), "regime_nifty_below_200d": metrics(T[~up], COST),
           "excess_vs_average_stock_pct": round(float(np.nanmean(T["vs_avg_stock"]) * 100), 2),
           "excess_vs_nifty_pct": round(float(np.nanmean(T["vs_nifty"]) * 100), 2),
           "trades_from_delisted_stocks": int((T["src"] == "nse").sum())}
    return out


if __name__ == "__main__":
    data = list(universe(include_delisted=True))
    print(f"universe loaded: {len(data)} stocks ({sum(1 for x in data if x[3] == 'nse')} rebuilt from NSE files)",
          file=sys.stderr)
    close_panel = pd.DataFrame({s: d["close"] for s, d, m, src in data}).where(
        pd.DataFrame({s: pd.Series(m, index=d.index) for s, d, m, src in data}))
    nclose = nifty()["close"]
    res = {}
    with Pool(4) as p:
        for name in STRATS:
            trades = []
            for r in p.imap_unordered(_one, [(name, s, d, m, src) for s, d, m, src in data], chunksize=4):
                trades += r
            errs = [t for t in trades if "error" in t]
            T = pd.DataFrame([t for t in trades if "error" not in t])
            T.to_csv(f"{ROOT}/validation/independent_trades_{name}.csv", index=False)
            res[name] = report_strategy(T, close_panel, nclose)
            res[name]["errors"] = len(errs)
            res[name]["without_delisted"] = metrics(T[T["src"] != "nse"].assign(
                entry_date=lambda x: pd.to_datetime(x["entry_date"]), exit_date=lambda x: pd.to_datetime(x["exit_date"])),
                COST) if len(T) else {}
            print(name, json.dumps(res[name]["after_costs"]), file=sys.stderr)
    extra = ai_and_disc_trades(data)
    for name, tr in extra.items():
        T = pd.DataFrame(tr)
        T.to_csv(f"{ROOT}/validation/independent_trades_{name}.csv", index=False)
        res[name] = report_strategy(T, close_panel, nclose)
        print(name, json.dumps(res[name].get("after_costs")), file=sys.stderr)
    res["_method"] = __doc__
    json.dump(res, open(f"{ROOT}/validation/independent_validation.json", "w"), indent=1, default=str)
    print(json.dumps({k: v.get("after_costs") for k, v in res.items() if k != "_method"}, indent=1))
