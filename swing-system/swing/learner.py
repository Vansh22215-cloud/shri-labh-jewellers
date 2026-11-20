"""The LEARNER (owner 20 Nov: "for every strategy we do, find all its trades and keep watching them: did they work,
how they worked, why they didn't, where they worked and why there and not here - and improve accordingly").

Inputs: every trade of a strategy - from its Kite test (data/tests/<name>.parquet) and from its live tips
(data/private/tips.csv, closed ones). Each trade carries its context at entry (time of day, weekday, month,
stock trend, market trend, VIX, gap, volume, volatility, turnover) and what happened while it was open
(best and worst move, how it ended, how long it took).

What it answers, per strategy (results/learner/<name>.md):
  1. Did it work?  win %, average after costs, test vs live side by side (is live behaving like the test?).
  2. WHERE it works and where it does not: every context, split into groups; a group is called out only if it
     has enough trades (>= 30) AND differs clearly from the strategy's average (beyond random noise: a 95%
     range around the group's average that does not include the overall average).
  3. WHY losers lost - each loss is put in one plain group:
        "wrong from the start"   - stopped within 2 candles, never up more than 0.3%
        "was right, gave it back" - was up at least 1R (the stop distance) before ending in a loss
        "slow bleed"             - ended by time / square-off / exit rule without reaching the stop
        "gap through the stop"   - the candle opened below the stop (loss bigger than planned)
        "normal stop"            - everything else that hit the stop
     and WHY winners won: target, exit rule, square-off/time in profit.
  4. Ideas to test next (never applied by itself): e.g. "skip trades when VIX > 25 (n=410, avg -0.6%)",
     "losses that were up 1R first are 38% of losses -> test a break-even stop". The owner decides; any
     change is tested on Kite data first, then goes live only with the owner's yes.
The Learner never changes a strategy, a stop, a quantity or a live setting by itself."""
import json

import numpy as np
import pandas as pd

from .config import DATA, PRIVATE, RESULTS, get_logger

log = get_logger()
OUT = RESULTS / "learner"
MIN_GROUP = 30
CONTEXTS = ["time_of_day", "weekday", "month", "year", "stock_trend", "market", "vix", "gap", "rel_volume",
            "volatility", "turnover"]


def loss_reason(r):
    if r["net_pct"] > 0:
        return {"target": "won: reached the target", "exit rule": "won: exit rule in profit"}.get(r["why"], "won: closed in profit")
    risk = abs(r["entry"] - r["stop"]) / r["entry"] * 100 if r["entry"] else 1.0
    if r["why"] == "stop-loss" and r["exit"] < r["stop"] - 1e-9:
        return "lost: gap through the stop"
    if r.get("best_pct", 0) >= risk:
        return "lost: was right, gave it back"
    if r["why"] == "stop-loss" and r["bars"] <= 2 and r.get("best_pct", 0) < 0.3:
        return "lost: wrong from the start"
    if r["why"] != "stop-loss":
        return "lost: slow bleed (no stop, no target)"
    return "lost: normal stop"


def groups(T, col, base_avg):
    """Per value of one context: n, win %, average, and whether it clearly differs from the overall average."""
    out = []
    for v, g in T.groupby(col, dropna=False):
        n = g["net_pct"]
        if len(n) < 5:
            continue
        se = n.std(ddof=1) / np.sqrt(len(n)) if len(n) > 1 else np.nan
        lo, hi = n.mean() - 1.96 * se, n.mean() + 1.96 * se
        clear = len(n) >= MIN_GROUP and se == se and (lo > base_avg or hi < base_avg)
        out.append({"context": col, "value": str(v), "trades": int(len(n)), "win_pct": round(float((n > 0).mean() * 100), 1),
                    "avg_net_pct": round(float(n.mean()), 3), "clear": bool(clear),
                    "better": bool(clear and lo > base_avg), "worse": bool(clear and hi < base_avg)})
    return out


def live_trades(name):
    f = PRIVATE / "tips.csv"
    try:
        L = pd.read_csv(f, parse_dates=["signal", "entry_time", "exit_time"])
    except Exception:
        return pd.DataFrame()
    return L[(L["strategy"] == name) & L["exit"].notna()].copy()


def analyse(name, T=None, live=None):
    """-> dict with everything the report shows."""
    if T is None:
        try:
            from .backtest import TESTS
            T = pd.read_parquet(TESTS / f"{name}.parquet")
        except Exception:
            T = pd.DataFrame()
    live = live_trades(name) if live is None else live
    out = {"name": name, "test_trades": int(len(T)), "live_trades": int(len(live))}
    for lab, X in (("test", T), ("live", live)):
        if len(X):
            n = X["net_pct"]
            out[lab] = {"trades": int(len(X)), "win_pct": round(float((n > 0).mean() * 100), 1),
                        "avg_net_pct": round(float(n.mean()), 3)}
    if not len(T):
        return out
    base = float(T["net_pct"].mean())
    G = []
    for c in CONTEXTS:
        if c in T.columns:
            G += groups(T, c, base)
    out["groups"] = G
    T = T.copy()
    T["reason"] = [loss_reason(r) for r in T.to_dict("records")]
    rs = T["reason"].value_counts()
    losses = T[T["net_pct"] <= 0]
    out["reasons"] = [{"reason": k, "trades": int(v), "share_pct": round(v / len(T) * 100, 1),
                       "avg_net_pct": round(float(T.loc[T["reason"] == k, "net_pct"].mean()), 3)} for k, v in rs.items()]
    ideas = []
    for g in sorted([g for g in G if g["worse"]], key=lambda g: g["avg_net_pct"])[:5]:
        ideas.append(f"Skip trades when {g['context'].replace('_', ' ')} = {g['value']}: {g['trades']:,} trades, "
                     f"average {g['avg_net_pct']:+.2f}% vs {base:+.2f}% overall.")
    for g in sorted([g for g in G if g["better"]], key=lambda g: -g["avg_net_pct"])[:3]:
        ideas.append(f"Works best when {g['context'].replace('_', ' ')} = {g['value']}: {g['trades']:,} trades, "
                     f"average {g['avg_net_pct']:+.2f}% - test trading only there.")
    if len(losses):
        gave = (T["reason"] == "lost: was right, gave it back").sum() / len(losses) * 100
        wrong = (T["reason"] == "lost: wrong from the start").sum() / len(losses) * 100
        if gave >= 25:
            ideas.append(f"{gave:.0f}% of losses were up at least the stop distance first - test a break-even stop "
                         "or a nearer target.")
        if wrong >= 40:
            ideas.append(f"{wrong:.0f}% of losses were wrong from the start - test a confirmation before entering "
                         "(e.g. the next candle).")
    if "live" in out and "test" in out and out["live"]["trades"] >= 20:
        d = out["live"]["avg_net_pct"] - out["test"]["avg_net_pct"]
        if abs(d) > 0.5:
            ideas.append(f"Live trades average {d:+.2f}% {'better' if d > 0 else 'worse'} than the test "
                         f"({out['live']['trades']} live trades) - check why before trusting the test.")
    out["ideas"] = ideas
    return out


def report(name, T=None, data=None):
    a = analyse(name, T)
    OUT.mkdir(parents=True, exist_ok=True)
    L = [f"# Learner: {name} ({pd.Timestamp.now(tz='Asia/Kolkata'):%d %b %Y %H:%M} IST)", ""]
    if data:
        from .backtest import data_line
        L += [f"**{data_line(data)}** Live trades: Kite prices.", ""]
    L += ["## 1. Did it work?", "", "| | Trades | Win % | Avg after costs |", "|---|---|---|---|"]
    for lab in ("test", "live"):
        if lab in a:
            L.append(f"| {'Kite test' if lab == 'test' else 'Live tips'} | {a[lab]['trades']:,} | {a[lab]['win_pct']} | "
                     f"{a[lab]['avg_net_pct']:+.2f}% |")
    if "groups" not in a:
        L += ["", "No test trades yet."]
    else:
        L += ["", "## 2. Where it works and where it does not", "",
              f"Only groups with at least {MIN_GROUP} trades that differ clearly from the average are marked.", "",
              "| Context | Group | Trades | Win % | Avg after costs | |", "|---|---|---|---|---|---|"]
        for g in a["groups"]:
            mark = "✅ better" if g["better"] else "⛔ worse" if g["worse"] else ""
            L.append(f"| {g['context'].replace('_', ' ')} | {g['value']} | {g['trades']:,} | {g['win_pct']} | "
                     f"{g['avg_net_pct']:+.2f}% | {mark} |")
        L += ["", "## 3. Why trades won or lost", "", "| How it ended | Trades | Share | Avg after costs |",
              "|---|---|---|---|"] + [f"| {r['reason']} | {r['trades']:,} | {r['share_pct']}% | {r['avg_net_pct']:+.2f}% |"
                                       for r in a["reasons"]]
        L += ["", "## 4. Ideas to test next (nothing changes without your yes)", ""] + \
             ([f"- {i}" for i in a["ideas"]] or ["- none clear yet"])
    (OUT / f"{name}.md").write_text("\n".join(L) + "\n")
    json.dump(a, open(OUT / f"{name}.json", "w"), indent=1, default=str)
    return L
