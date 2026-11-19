"""VANTAGE AI — validation of the EXACT indicator logic (replica.py = core.pine) on NSE data, 2013-2026.

Data / method (same as the swing system's BACKTEST_VALIDATION.md):
  * point-in-time top-300 NSE stocks by turnover (monthly, decided only from earlier data); 228 delisted / renamed
    stocks rebuilt from NSE's own daily files (no survivorship bias); ETFs excluded
  * BUY decided at the daily close -> filled at the NEXT open; stops fill at the stop or at the open if it gaps below
  * costs 0.35% per round trip (STT, exchange/SEBI/stamp/GST, slippage); stress test at 0.60%
  * a stock may only get a NEW signal while it is in that month's top-300 (open trades continue)
  * development period: 2013 - Oct 2023 · untouched holdout: Nov 2023 - Nov 2026

PRE-REGISTERED RULES (written before the first run; the defaults in core.pine were fixed before it too):
  PASS BAR for the indicator and for each entry type separately (all must hold, after costs):
    1. expectancy > 0 and the 95% confidence interval's lower end > 0
    2. holdout (Nov 2023+) expectancy > 0 on >= 100 trades
    3. beats the average top-300 stock held over the same days in >= 55% of years
    4. profit factor >= 1.3
    5. still positive at 0.60% costs
  DECISIONS:
    * an entry type that fails is switched OFF by default (the user can still switch it on)
    * the default exit mode stays "Combined" unless it fails the bar while another exit mode passes
    * NO other parameter is changed after seeing results (no curve fitting)
ADDENDUM (17 Nov, written BEFORE the run that includes them): entry types 3 "Dip-buy" (tiered dip-buy with Vix Fix /
WaveTrend / order block / MSB order block / swing-low hold confirmations, no entry while Squeeze is ON) and 4 "RCP"
(Rolling Candle Profile BUY within 10% of the 52-week high) use their own previously tested rules and exits. Each
entry type must pass the same bar on its own; a type that fails is OFF by default. The "likely %" shown on a BUY is
the historical share of similar signals (same type; dip-buy by tier; breakout by score band 70-79 / 80-89 / 90+)
that ended in profit after 0.35% costs in this run - a past frequency, not a guaranteed probability.
Run: python3 backtest.py  ->  results.json, trades_<mode>.csv
"""
import json
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd

SW = __import__("os").path.join(__import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__)))), "swing-system")
sys.path.insert(0, SW)
sys.path.insert(0, f"{SW}/validation")
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import independent_validation as iv  # noqa: E402
import replica  # noqa: E402

HERE = __import__("os").path.dirname(__import__("os").path.abspath(__file__))
BENCH = None
MODE = "Combined"
EXTRA = {}


def _one(args):
    sym, d, m, src = args
    try:
        tr = replica.run(d, BENCH, allow=m, p=dict(EXTRA, exitMode=MODE))
        for x in tr:
            x.update(sym=sym, src=src)
        return tr
    except Exception as e:
        return [{"error": f"{sym}: {type(e).__name__}: {e}"}]


def frame(trades):
    T = pd.DataFrame([t for t in trades if "error" not in t])
    if not len(T):
        return T
    T["gross"] = T["exit"] / T["entry"] - 1
    T["stop_pct"] = ((T["entry"] - T["init_stop"]) / T["entry"]).clip(lower=0.005)
    T["entry_date"] = pd.to_datetime(T["entry_date"])
    T["exit_date"] = pd.to_datetime(T["exit_date"])
    return T


def verdict(r, min_hold=100):
    a, ho, st = r["after_costs"], r["out_of_sample_2023_11_on"], r["cost_stress_0.60pct"]
    yrs = r["excess_vs_average_stock_by_year_pct"]
    beat = sum(1 for v in yrs.values() if v > 0) / max(1, len(yrs))
    chk = {"1 expectancy>0 & CI lower>0": a.get("trades", 0) > 1 and a["expectancy_ci95_pct"][0] > 0,
           "2 holdout>0 on >=100 trades": ho.get("trades", 0) >= min_hold and ho["expectancy_pct"] > 0,
           "3 beats avg stock >=55% of years": beat >= 0.55,
           "4 profit factor >=1.3": (a.get("profit_factor") or 0) >= 1.3,
           "5 positive at 0.60% costs": st.get("trades", 0) > 0 and st["expectancy_pct"] > 0}
    return all(chk.values()), chk, round(beat * 100)


def breakdowns(T, ranks):
    out = {}
    nif = iv.nifty()["close"]
    vol = nif.pct_change().rolling(20).std() * np.sqrt(252)
    q = vol.quantile([1 / 3, 2 / 3]).values
    v_at = vol.reindex(T["entry_date"]).values
    T = T.assign(vol_bucket=np.where(v_at <= q[0], "low volatility", np.where(v_at <= q[1], "medium volatility", "high volatility")))
    T = T.assign(cap=[("large-cap (top 100)" if ranks.get((s, str(pd.Timestamp(dt).to_period("M"))), 999) <= 100 else "mid-cap (101-300)")
                      for s, dt in zip(T["sym"], T["signal"])])
    for col in ("setup", "regime", "vol_bucket", "cap", "why"):
        out[col] = {k: iv.metrics(g, iv.COST) for k, g in T.groupby(col)}
    out["year"] = {int(k): iv.metrics(g, iv.COST) for k, g in T.groupby(T["entry_date"].dt.year)}
    return out


def calibration(T):
    """Historical win rate (after costs) of similar signals: by type; dip-buy by tier; breakout by score band."""
    T = T.copy()
    T["win"] = (T["gross"] - iv.COST) > 0
    T["band"] = np.where(T["score"] >= 90, "90+", np.where(T["score"] >= 80, "80-89", "70-79"))
    ho = T["entry_date"] >= iv.OOS
    out = {}
    def row(g):
        return {"n": int(len(g)), "win_pct": round(float(g["win"].mean() * 100)) if len(g) else None,
                "avg_pct": round(float((g["gross"] - iv.COST).mean() * 100), 2) if len(g) else None,
                "holdout_n": int((g["entry_date"] >= iv.OOS).sum()),
                "holdout_win_pct": round(float(g.loc[g["entry_date"] >= iv.OOS, "win"].mean() * 100)) if (g["entry_date"] >= iv.OOS).any() else None}
    for st, g in T.groupby("setup"):
        out[st] = row(g)
        if st == "Dip-buy":
            for tr_, gg in g.groupby("tier"):
                out[f"Dip-buy {tr_}"] = row(gg)
        if st in ("Breakout", "Pullback"):
            for b_, gg in g.groupby("band"):
                out[f"{st} {b_}"] = row(gg)
    _ = ho
    return out


def single_stocks(data_by, ranks_month):
    """Rule-based (no cherry-picking): the 5 largest and the stocks ranked 151-155 in the first month of 2014.
    Indicator with its own sizing (₹50,000, 1% risk, non-compounding, 0.35% costs) vs ₹50,000 bought and held."""
    out = {}
    first = sorted(ranks_month)[0]
    for label, rr in (("large", range(1, 6)), ("mid", range(151, 156))):
        for sym, rank in sorted(ranks_month[first].items(), key=lambda x: x[1]):
            if rank not in rr or sym not in data_by:
                continue
            d = data_by[sym]
            d = d[d.index >= "2013-01-01"]
            T = frame(replica.run(d, BENCH, p=dict(EXTRA, exitMode=MODE)))
            pnl = float(((T["exit"] - T["entry"]) * T["qty"] - 0.00175 * (T["exit"] + T["entry"]) * T["qty"]).sum()) if len(T) else 0.0
            s0 = d[d.index >= "2014-01-01"]
            bh = 50000 * (float(s0["close"].iloc[-1]) / float(s0["open"].iloc[0]) - 1)
            out[sym] = {"group": label, "trades": int(len(T)), "indicator_pnl_rs": round(pnl),
                        "buy_and_hold_pnl_rs": round(bh), "win_pct": round(float((T["exit"] > T["entry"]).mean() * 100), 1) if len(T) else None,
                        "max_capital_used_rs": round(float((T["entry"] * T["qty"]).max())) if len(T) else 0}
    return out


if __name__ == "__main__":
    BENCH = iv.nifty()["close"]
    data = list(iv.universe(include_delisted=True))
    print(f"universe: {len(data)} stocks", file=sys.stderr)
    u = pd.read_csv(f"{SW}/data/universe_history.csv", parse_dates=["asof"])
    ranks = {(r.symbol, str(r.asof.to_period("M"))): r.rank for r in u.itertuples()}
    ranks_month = {}
    for r in u.itertuples():
        ranks_month.setdefault(r.asof, {})[r.symbol] = r.rank
    raw = pd.DataFrame({s: d["close"] for s, d, m, src in data}).sort_index()
    member = pd.DataFrame({s: pd.Series(m, index=d.index) for s, d, m, src in data}).reindex(raw.index).fillna(False).astype(bool)
    panel = (raw, member)
    res = {"_method": __doc__}
    final = "--final" in sys.argv          # the published defaults (decided by the pre-registered rules above)
    if final:
        EXTRA = {"usePullback": False}
    for mode in (("Fixed risk/reward",) if final else ("Combined", "ATR trailing stop", "Fixed risk/reward")):
        MODE = mode
        trades = []
        with Pool(4) as p:
            for r in p.imap_unordered(_one, [(s, d, m, src) for s, d, m, src in data], chunksize=4):
                trades += r
        errs = [t for t in trades if "error" in t]
        T = frame(trades)
        T.to_csv(f"{HERE}/trades_{'FINAL' if final else mode.split()[0]}.csv", index=False)
        rep = iv.report_strategy(T, panel, BENCH)
        ok, chk, beat = verdict(rep)
        rep.update(PASS=ok, checks=chk, years_beating_avg_pct=beat, errors=len(errs), trades_per_year=round(len(T) / 13.9, 1))
        if mode == ("Fixed risk/reward" if final else "Combined"):
            rep["breakdowns"] = breakdowns(T, ranks)
            for st, g in T.groupby("setup"):
                r2 = iv.report_strategy(g, panel, BENCH)
                ok2, chk2, beat2 = verdict(r2)
                rep[f"entry_type_{st}"] = dict(after_costs=r2["after_costs"], holdout=r2["out_of_sample_2023_11_on"],
                                               PASS=ok2, checks=chk2, years_beating_avg_pct=beat2)
            rep["single_stocks"] = single_stocks({s: d for s, d, m, src in data}, ranks_month)
            rep["calibration"] = calibration(T)
        res[mode] = rep
        a = rep["after_costs"]
        print(f"{mode}: {'PASS' if ok else 'fail'} n={a.get('trades')} win={a.get('win_pct')} exp={a.get('expectancy_pct')} "
              f"ci={a.get('expectancy_ci95_pct')} pf={a.get('profit_factor')} holdout={rep['out_of_sample_2023_11_on'].get('expectancy_pct')} "
              f"beat={beat}% errs={len(errs)}", file=sys.stderr)
    json.dump(res, open(f"{HERE}/{'results_final' if final else 'results'}.json", "w"), indent=1, default=str)
