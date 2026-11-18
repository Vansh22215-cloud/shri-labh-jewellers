"""Per-signal likely-win % (CALIB_PREREGISTRATION.md).
python3 calib.py test   -> calib_results.json (PASS / FAIL on the holdout)
python3 calib.py fit    -> calib_model.json (final model on all trades, used by the live scanner)
"""
import json
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/user/shri-labh-jewellers/vantage-ai/validation")
from improve import iv, HERE, OOS, COST  # noqa: E402

FEATS = ["stop_pct", "own_rate", "dist52", "ret20", "rs126", "vol_ratio", "log_turn", "score",
         "t_rcp", "t_brk", "t_dipA", "t_dipB", "t_dipC", "reg_bull", "reg_bear"]
SHRINK = 10


def kind(setup, tier):
    return "RCP" if setup == "RCP" else "Breakout" if setup == "Breakout" else f"Dip-buy {tier}"


def price_feats(d, k):
    """Features of one stock on bar k (signal day). Same function is used live (swing/vantage.py)."""
    w = d.iloc[max(0, k - 260):k + 1]
    c, h, v = w["close"].values, w["high"].values, w["volume"].values
    out = {"dist52": float(c[-1] / h[-252:].max() - 1),
           "ret20": float(c[-1] / c[-21] - 1) if len(c) > 21 else 0.0,
           "vol_ratio": float(np.log(max(v[-1], 1) / max(v[-51:-1].mean(), 1))) if len(v) > 51 else 0.0,
           "log_turn": float(np.log10(max((c[-20:] * v[-20:]).mean(), 1)))}
    return out


def own_rate(sym_trades, day, base):
    """Company's own record: signals that CLOSED before `day`, shrunk toward the type's average."""
    past = sym_trades[sym_trades["exit_date"] < day]
    n, w = len(past), int(past["win"].sum())
    return (w + SHRINK * base) / (n + SHRINK), n, w


def build():
    T = pd.read_csv(f"{HERE}/trades_FINAL.csv", parse_dates=["signal", "entry_date", "exit_date"])
    T["win"] = (T["exit"] / T["entry"] - 1 - COST) > 0
    T["kind"] = [kind(s, t) for s, t in zip(T["setup"], T["tier"].fillna(""))]
    T["stop_pct"] = ((T["entry"] - T["init_stop"]) / T["entry"]).clip(0.005, 0.6)
    data = {s: d for s, d, m, src in iv.universe(include_delisted=True)}
    close = pd.DataFrame({s: d["close"] for s, d in data.items()}).sort_index()
    rs = (close / close.shift(126) - 1).rank(axis=1, pct=True)
    rows = []
    for t in T.itertuples():
        d = data.get(t.sym)
        f = {}
        if d is not None and t.signal in d.index:
            f = price_feats(d, d.index.get_loc(t.signal))
        f["rs126"] = float(rs.at[t.signal, t.sym]) if t.signal in rs.index and t.sym in rs.columns and \
            pd.notna(rs.at[t.signal, t.sym]) else 0.5
        rows.append(f)
    F = pd.DataFrame(rows, index=T.index)
    T = pd.concat([T, F], axis=1)
    return T


def add_own(T, base):
    """own_rate with `base` = type averages (dict) - computed from the training period only."""
    rates, ns = [], []
    by = {s: g for s, g in T.groupby("sym")}
    for t in T.itertuples():
        r, n, _ = own_rate(by[t.sym], t.signal, base[t.kind])
        rates.append(r)
        ns.append(n)
    T = T.copy()
    T["own_rate"], T["own_n"] = rates, ns
    return T


def design(T):
    X = pd.DataFrame({k: T[k] for k in ("stop_pct", "own_rate", "dist52", "ret20", "rs126", "vol_ratio", "log_turn")})
    X["score"] = T["score"].fillna(0)
    for name, k in (("t_rcp", "RCP"), ("t_brk", "Breakout"), ("t_dipA", "Dip-buy A"), ("t_dipB", "Dip-buy B"),
                    ("t_dipC", "Dip-buy C")):
        X[name] = (T["kind"] == k).astype(float)
    X["reg_bull"] = (T["regime"] == "BULLISH").astype(float)
    X["reg_bear"] = (T["regime"] == "BEARISH").astype(float)
    return X[FEATS].fillna(0.0)


def fit(T):
    from sklearn.linear_model import LogisticRegression
    X = design(T)
    mu, sd = X.mean(), X.std().replace(0, 1)
    m = LogisticRegression(C=1.0, max_iter=2000).fit((X - mu) / sd, T["win"])
    return {"feats": FEATS, "mu": mu.tolist(), "sd": sd.tolist(), "coef": m.coef_[0].tolist(),
            "intercept": float(m.intercept_[0]), "shrink": SHRINK}


def predict(model, X):
    z = ((X[model["feats"]] - np.array(model["mu"])) / np.array(model["sd"])) @ np.array(model["coef"]) + model["intercept"]
    return 1 / (1 + np.exp(-z))


def test():
    T = build()
    dev = T[T["signal"] < OOS]
    base = dev.groupby("kind")["win"].mean().to_dict()
    T = add_own(T, base)
    dev, ho = T[T["signal"] < OOS], T[T["signal"] >= OOS]
    model = fit(dev)
    p = predict(model, design(ho))
    flat = ho["kind"].map(base).values
    y = ho["win"].astype(float).values
    q = pd.qcut(p, 5, labels=False, duplicates="drop")
    groups = []
    for g in sorted(set(q)):
        msk = q == g
        groups.append({"n": int(msk.sum()), "predicted": round(float(p[msk].mean() * 100), 1),
                       "actual": round(float(y[msk].mean() * 100), 1)})
    calib_ok = all(abs(g["predicted"] - g["actual"]) <= 6 for g in groups)
    spread = groups[-1]["actual"] - groups[0]["actual"]
    brier, brier_flat = float(np.mean((p - y) ** 2)), float(np.mean((flat - y) ** 2))
    rcp = ho["kind"].values == "RCP"
    qr = pd.qcut(p[rcp], 5, labels=False, duplicates="drop")
    rcp_groups = [{"n": int((qr == g).sum()), "predicted": round(float(p[rcp][qr == g].mean() * 100), 1),
                   "actual": round(float(y[rcp][qr == g].mean() * 100), 1),
                   "avg_result_pct": round(float((ho[rcp]["exit"] / ho[rcp]["entry"] - 1 - COST).values[qr == g].mean() * 100), 2)}
                  for g in sorted(set(qr))]
    out = {"PASS": bool(calib_ok and spread >= 12 and brier < brier_flat), "calibration_ok": calib_ok,
           "spread_points": round(spread, 1), "brier": round(brier, 4), "brier_flat": round(brier_flat, 4),
           "holdout_groups": groups, "holdout_rcp_groups": rcp_groups,
           "coef": dict(zip(FEATS, [round(c, 3) for c in model["coef"]]))}
    json.dump(out, open(f"{HERE}/calib_results.json", "w"), indent=1)
    print(json.dumps(out, indent=1))


def final():
    T = build()
    base = T.groupby("kind")["win"].mean().to_dict()
    T = add_own(T, base)
    model = fit(T)
    model["base"] = base
    model["trained_on"] = int(len(T))
    json.dump(model, open(f"{HERE}/calib_model.json", "w"), indent=1)
    # each company's own record (signals closed so far) for the live messages
    rec = {s: [int(len(g)), int(g["win"].sum())] for s, g in T.groupby("sym")}
    json.dump(rec, open(f"{HERE}/calib_company_record.json", "w"))
    print("model saved", len(T), "trades,", len(rec), "companies")


if __name__ == "__main__":
    {"test": test, "fit": final}[sys.argv[1]]()
