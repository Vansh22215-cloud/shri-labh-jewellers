"""Round 9 (IMPROVE9_PREREGISTRATION.md): event signals from NSE disclosures.
python3 improve9.py -> improve9_results.json + improve9_events_*.csv"""
import glob
import json
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/user/shri-labh-jewellers/vantage-ai/validation")
from improve import iv, HERE, OOS, COST, SW  # noqa: E402
from improve8 import load as load_trades, SETS, g  # noqa: E402

H = f"{SW}/data/events/history"
_PX = {}


def px(sym):
    if sym not in _PX:
        from swing import data_prices
        d = data_prices.load(sym)
        if d is None or len(d) < 60:
            _PX[sym] = None
        else:
            f = (d["adj_close"] / d["close"]).fillna(1.0) if "adj_close" in d else 1.0
            _PX[sym] = pd.DataFrame({"o": d["open"] * f, "c": d["close"] * f, "turn": (d["close"] * d["volume"]).rolling(20).mean()})
    return _PX[sym]


def read(kind):
    parts = []
    for f in sorted(glob.glob(f"{H}/{kind}/*.csv")):
        try:
            parts.append(pd.read_csv(f))
        except Exception:
            pass
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def event_trades(E, hold=5):
    """E: sym, day (event public date). Entry next bar open, exit open `hold` bars later; liquidity >= Rs 2 cr."""
    rows = []
    for sym, grp in E.sort_values("day").groupby("sym"):
        d = px(sym)
        if d is None:
            continue
        idx, busy = d.index, pd.Timestamp.min
        for day in grp["day"]:
            k = idx.searchsorted(day, side="right")             # first bar after the event day
            if k + hold >= len(idx) or k < 1 or idx[k] <= busy:
                continue
            if not (d["turn"].iloc[k - 1] >= 2e7):
                continue
            e, x = d["o"].iloc[k], d["o"].iloc[k + hold]
            if e > 0 and x > 0:
                rows.append({"sym": sym, "day": day, "entry_date": idx[k], "net": x / e - 1 - COST})
                busy = idx[k + hold]
    return pd.DataFrame(rows)


def verdict(T, min_ho=40):
    dev, ho = T[T["day"] < OOS], T[T["day"] >= OOS]
    sd, sh = g(dev), g(ho)
    ok = (sh.get("n", 0) >= min_ho and sh["per_trade"] >= 1.0 and (sh["pf"] or 0) >= 1.3 and (sd.get("pf") or 0) >= 1.3
          and sd["per_trade"] > 0)
    return {"PASS": bool(ok), "dev": sd, "holdout": sh,
            "by_year": {int(y): g(x) for y, x in T.groupby(T["day"].dt.year)}}


def promoter_events():
    I = read("insider")
    I = I[I["personCategory"].isin(["Promoters", "Promoter Group"]) & (I["acqMode"] == "Market Purchase")
          & (I["tdpTransactionType"] == "Buy")].copy()
    I["val"] = pd.to_numeric(I["secVal"], errors="coerce")
    I = I[I["val"] >= 1e6]
    I["day"] = pd.to_datetime(I["date"], errors="coerce", dayfirst=True).dt.normalize()
    return I.dropna(subset=["day"]).rename(columns={"symbol": "sym"})[["sym", "day"]].drop_duplicates()


def pledge_events():
    I = read("insider")
    I = I[I["personCategory"].isin(["Promoters", "Promoter Group"]) & (I["acqMode"] == "Pledge Creation")].copy()
    I["day"] = pd.to_datetime(I["date"], errors="coerce", dayfirst=True).dt.normalize()
    return I.dropna(subset=["day"]).rename(columns={"symbol": "sym"})[["sym", "day"]].drop_duplicates()


def bulk_events():
    B = read("bulk")
    B.columns = [c.strip() for c in B.columns]
    B = B.rename(columns={"Date": "date", "Symbol": "sym", "Client Name": "client", "Buy / Sell": "side",
                          "Quantity Traded": "qty", "Trade Price / Wght. Avg. Price": "price"})
    for c in ("sym", "client", "side"):
        B[c] = B[c].astype(str).str.strip()
    B["qty"] = pd.to_numeric(B["qty"].astype(str).str.replace(",", ""), errors="coerce")
    B["price"] = pd.to_numeric(B["price"].astype(str).str.replace(",", ""), errors="coerce")
    B["day"] = pd.to_datetime(B["date"].astype(str).str.strip(), format="%d-%b-%Y", errors="coerce")
    sells = set(zip(B.loc[B["side"] == "SELL", "day"], B.loc[B["side"] == "SELL", "sym"], B.loc[B["side"] == "SELL", "client"]))
    buy = B[(B["side"] == "BUY") & (B["qty"] * B["price"] >= 1e7)]
    buy = buy[[(d, s, c) not in sells for d, s, c in zip(buy["day"], buy["sym"], buy["client"])]]
    return buy.dropna(subset=["day"])[["sym", "day"]].drop_duplicates()


def buyback_events():
    Y = read("buyback")
    Y["t"] = pd.to_datetime(Y["an_dt"], errors="coerce", dayfirst=True)
    txt = (Y["desc"].astype(str) + " " + Y["text"].astype(str)).str.lower()
    keep = Y["desc"].isin(["Buyback", "Public Announcement - Buyback of Shares"]) | \
        ((Y["desc"] == "Outcome of Board Meeting") & txt.str.contains("buy") & txt.str.contains("back"))
    Y = Y[keep].dropna(subset=["t"]).sort_values("t")
    Y["day"] = Y["t"].dt.normalize()                                 # entry is always the next bar (see event_trades)
    out, last = [], {}
    for s, dday in zip(Y["symbol"], Y["day"]):
        if s in last and (dday - last[s]).days < 60:
            continue
        last[s] = dday
        out.append({"sym": s, "day": dday})
    return pd.DataFrame(out)


def index_trades():
    D = pd.read_csv(f"{HERE}/index_changes.csv", parse_dates=["announce_date", "effective_date"])
    big = {"NIFTY 50", "NIFTY NEXT 50", "NIFTY 100", "NIFTY 200", "NIFTY 500", "NIFTY MIDCAP 150", "NIFTY SMALLCAP 250"}
    D = D[(D["action"] == "include") & D["index"].str.upper().str.strip().isin(big) & D["effective_date"].notna()]
    D = D.drop_duplicates(["symbol", "announce_date"])
    rows = []
    for r in D.itertuples():
        d = px(r.symbol)
        if d is None:
            continue
        idx = d.index
        k = idx.searchsorted(r.announce_date, side="right")
        x = idx.searchsorted(r.effective_date) - 1                     # last bar before the effective date
        if k >= len(idx) or x <= k or x >= len(idx) or not (d["turn"].iloc[k - 1] >= 2e7):
            continue
        e, c = d["o"].iloc[k], d["c"].iloc[x]
        rows.append({"sym": r.symbol, "day": r.announce_date, "index": r.index, "days": int(x - k + 1), "net": c / e - 1 - COST})
    return pd.DataFrame(rows)


def boost(E, window, name, worse=False):
    cal = iv.nifty()["close"].index
    pos = pd.Series(np.arange(len(cal)), index=cal)
    ev = {s: np.sort(pos.reindex(x["day"]).dropna().values) for s, x in E.groupby("sym")}
    out, ok = {}, True
    for k, f in SETS.items():
        T = load_trades(f)
        p = pos.reindex(T["signal"]).values
        flag = []
        for s, q in zip(T["sym"], p):
            a = ev.get(s)
            flag.append(bool(a is not None and np.isfinite(q) and ((q - a > 0) & (q - a <= window)).any()))
        T["flag"] = flag
        out[k] = {}
        for per, m in (("dev", T["signal"] < OOS), ("holdout", T["signal"] >= OOS)):
            a, b = g(T[m & T["flag"]]), g(T[m & ~T["flag"]])
            out[k][per] = {name: a, "others": b}
            diff = (b["per_trade"] - a["per_trade"]) if worse else (a.get("per_trade", -99) - b["per_trade"])
            ok &= a.get("n", 0) >= 50 and diff >= 1.0
    out["PASS"] = bool(ok)
    return out


def main():
    R = {}
    for key, fn in (("4_promoter_buying", promoter_events), ("5_bulk_deal_buy", bulk_events), ("9_buyback", buyback_events)):
        E = fn()
        T = event_trades(E)
        T.to_csv(f"{HERE}/improve9_events_{key}.csv", index=False)
        R[key] = dict(events=int(len(E)), **verdict(T))
        print(key, R[key]["PASS"], R[key]["dev"], R[key]["holdout"], flush=True)
        if key in ("4_promoter_buying", "5_bulk_deal_buy"):
            R[key + "_boost"] = boost(E, 20 if key.startswith("4") else 10, "with_event")
            print(key, "boost", R[key + "_boost"]["PASS"], flush=True)
    T = index_trades()
    T.to_csv(f"{HERE}/improve9_events_8_index.csv", index=False)
    R["8_index_inclusion"] = verdict(T, min_ho=60)
    print("8", R["8_index_inclusion"]["PASS"], R["8_index_inclusion"]["dev"], R["8_index_inclusion"]["holdout"], flush=True)
    R["10_pledge_warning"] = boost(pledge_events(), 60, "after_pledge", worse=True)
    print("10", R["10_pledge_warning"]["PASS"], flush=True)
    json.dump(R, open(f"{HERE}/improve9_results.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
