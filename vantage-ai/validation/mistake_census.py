"""Mistake census: the Learner's diagnosis (swing/learning.py CODES) applied to every losing VANTAGE trade of the
13-year test, so the Learner starts with strong evidence instead of waiting for live losses.
-> mistake_census.json, mistake_census_trades.csv"""
import json
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, "/home/user/shri-labh-jewellers/vantage-ai/validation")
sys.path.insert(0, "/home/user/shri-labh-jewellers/swing-system")
import improve as im  # noqa: E402
from improve import iv, OOS, COST  # noqa: E402
from swing.learning import CODES  # noqa: E402
import glob, os  # noqa: E402

E = {os.path.basename(f)[:-4]: pd.to_datetime(pd.read_csv(f)["date"], errors="coerce").dropna().values
     for f in glob.glob("/home/user/shri-labh-jewellers/swing-system/data/events/earnings/*.csv")}
nifty = iv.nifty()["close"]
out, rows = {}, []
for st, f, gen in (("top300", "trades_FINAL.csv", lambda: iv.universe(include_delisted=True)),
                   ("all", "improve_trades_U2.csv", im.all_stocks)):
    T = pd.read_csv(f, parse_dates=["signal", "entry_date", "exit_date"])
    data = {s: d for s, d, m, src in gen()}
    for t in T.itertuples():
        d = data.get(t.sym)
        if d is None or t.entry_date not in d.index:
            continue
        net = t.exit / t.entry - 1 - COST
        w = d.loc[t.entry_date:t.exit_date]
        best = w["high"].max() / t.entry - 1
        n = nifty[(nifty.index >= t.entry_date) & (nifty.index <= t.exit_date)]
        mkt = n.iloc[-1] / n.iloc[0] - 1 if len(n) >= 2 else 0
        res_in = t.sym in E and bool(((E[t.sym] > np.datetime64(t.entry_date)) & (E[t.sym] <= np.datetime64(t.exit_date))).any())
        code = ""
        if net <= 0:
            if "Stop" in str(t.why) and t.exit < t.init_stop * 0.995:
                code = "gap_through_stop"
            elif res_in and net <= -0.03:
                code = "results_shock"
            elif mkt <= -0.03:
                code = "market_fell"
            elif best >= 0.03:
                code = "gave_back"
            elif "Stop" in str(t.why) and t.days <= 3:
                code = "fast_stop"
            elif best < 0.01:
                code = "never_worked"
            else:
                code = "slow_bleed"
        rows.append({"set": st, "setup": t.setup, "signal": t.signal, "net": net, "best": best, "mkt": mkt, "code": code,
                     "days": t.days, "why": t.why})
C = pd.DataFrame(rows)
C.to_csv("mistake_census_trades.csv", index=False)
for (st, per), g in C.groupby(["set", np.where(C["signal"] < OOS, "development", "holdout")]):
    L = g[g["code"] != ""]
    out[f"{st} {per}"] = {"trades": int(len(g)), "losers": int(len(L)), "loss_share": round(len(L) / len(g) * 100, 1),
                          "causes": {CODES[k]: {"n": int(len(x)), "share_of_losers": round(len(x) / len(L) * 100, 1),
                                                "avg_loss_pct": round(x["net"].mean() * 100, 2),
                                                "share_of_all_money_lost": round(x["net"].sum() / L["net"].sum() * 100, 1)}
                                     for k, x in L.groupby("code")}}
json.dump(out, open("mistake_census.json", "w"), indent=1)
for k, v in out.items():
    print(f"\n{k}: {v['losers']} losers of {v['trades']} ({v['loss_share']}%)")
    for c, x in sorted(v["causes"].items(), key=lambda z: -z[1]["share_of_all_money_lost"]):
        print(f"   {x['share_of_all_money_lost']:5.1f}% of money lost | {x['n']:5d} trades | avg {x['avg_loss_pct']:+6.2f}% | {c}")
