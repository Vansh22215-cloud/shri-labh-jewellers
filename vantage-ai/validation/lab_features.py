"""AUTO-LAB step 1 (owner 19 Nov: "learn from everything ... situation, time, stock, history"):
for every VANTAGE trade of the 13-year test (both trade sets), describe the situation AT THE SIGNAL CLOSE using only
data known then (no look-ahead): the stock, its history, the market, the time. -> lab_features.csv.gz"""
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/user/shri-labh-jewellers/vantage-ai/validation")
from improve import HERE, SW, all_stocks  # noqa: E402

SETS = {"top300": "trades_FINAL.csv", "all": "improve_trades_U2.csv"}
T = pd.concat([pd.read_csv(f"{HERE}/{f}", parse_dates=["signal", "entry_date", "exit_date"]).assign(set=k)
               for k, f in SETS.items()], ignore_index=True)
NEED = set(T["sym"])


def stock_features(d):
    c, h, lo, v = d["close"], d["high"], d["low"], d["volume"]
    raw = d["raw_close"]
    tr = pd.concat([h - lo, (h - c.shift()).abs(), (lo - c.shift()).abs()], axis=1).max(axis=1)
    return pd.DataFrame({
        "turnover_cr": (raw * v).rolling(20).median() / 1e7,
        "from_52w_high": c / c.rolling(252, min_periods=120).max() - 1,
        "ret_6m": c / c.shift(126) - 1,
        "ret_1m": c / c.shift(21) - 1,
        "ret_1w": c / c.shift(5) - 1,
        "vol_surge": v / v.rolling(50).median().shift(1),
        "atr_pct": tr.rolling(14).mean() / c,
        "range_10d": (h.rolling(10).max() - lo.rolling(10).min()) / c,
        "vs_200d": c / c.rolling(200).mean() - 1,
        "signal_day_move": c / c.shift() - 1,
        "price_rs": raw,
        "up_days_10": (c.diff() > 0).rolling(10).sum(),
    })


def one(args):
    sym, d, _, src = args
    if sym not in NEED:
        return None
    F = stock_features(d)
    F["sym"] = sym
    return F.reset_index(names="signal")


def market():
    from swing import data_prices
    n = data_prices.benchmark()
    c = n["close"] if "close" in n else n.iloc[:, 0]
    M = pd.DataFrame({"nifty_1m": c / c.shift(21) - 1, "nifty_vs_200d": c / c.rolling(200).mean() - 1,
                      "nifty_vol_20d": c.pct_change().rolling(20).std() * np.sqrt(252)})
    S = pd.read_csv(f"{HERE}/situation_days.csv", parse_dates=["date"]).set_index("date")["key"]
    k = S.astype(str).str.split(" \\| ", expand=True)
    M = M.join(pd.DataFrame({"mkt_trend": k[0], "mkt_mood": k[1], "mkt_breadth": k[2]}, index=S.index), how="left")
    M.index.name = "signal"
    return M.reset_index()


def results_near():
    """days from the signal to the company's next results date (known dates only, ~500 companies)."""
    try:
        E = pd.read_csv(f"{HERE}/improve8_results_events.csv", parse_dates=["date"])[["sym", "date"]]
    except Exception:
        return None
    return E.sort_values("date")


if __name__ == "__main__":
    with Pool(4) as p:
        parts = [x for x in p.imap_unordered(one, all_stocks(), chunksize=8) if x is not None]
    F = pd.concat(parts, ignore_index=True)
    X = T.merge(F, on=["sym", "signal"], how="left").merge(market(), on="signal", how="left")
    # time
    X["weekday"] = X["signal"].dt.day_name().str[:3]
    X["month"] = X["signal"].dt.month
    X["day_of_month"] = X["signal"].dt.day
    # sector (NIFTY 500 list; others unknown)
    sec = pd.read_csv(f"{SW}/data/events/nifty500.csv")
    X["sector"] = X["sym"].map(dict(zip(sec["Symbol"].astype(str), sec["Industry"].astype(str)))).fillna("unknown")
    # results within the next 10 trading days (where dates are known)
    E = results_near()
    if E is not None:
        X = X.sort_values("signal")
        m = pd.merge_asof(X[["signal", "sym"]].reset_index(), E.rename(columns={"date": "res"}), left_on="signal",
                          right_on="res", by="sym", direction="forward")
        gap = (m.set_index("index")["res"] - m.set_index("index")["signal"]).dt.days
        known = X["sym"].isin(set(E["sym"]))
        X["results_soon"] = np.where(~known, "unknown", np.where(gap.reindex(X.index) <= 14, "yes", "no"))
    # how the stock's own earlier VANTAGE trades did (history), using only trades closed before this signal
    X = X.sort_values("signal").reset_index(drop=True)
    X["net"] = X["exit"] / X["entry"] - 1 - 0.0035
    past = []
    for (st, sym), g in X.groupby(["set", "sym"]):
        idx, sig, ex, net = g.index.values, g["signal"].values, g["exit_date"].values, g["net"].values
        for i in range(len(g)):
            m = ex[:i] < sig[i]
            past.append((idx[i], m.sum(), (net[:i][m] > 0).mean() if m.any() else np.nan))
    P = pd.DataFrame(past, columns=["i", "stock_past_trades", "stock_past_win"]).set_index("i")
    X = X.join(P)
    X.to_csv(f"{HERE}/lab_features.csv.gz", index=False)
    print(len(X), "trades;", X.isna().mean().round(3).to_dict())
