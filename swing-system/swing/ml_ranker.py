"""AI PICKS (D110) - a market-wide machine-learning ranker (same features and model as
validation/ml_ranker_research.py, which tested it strictly walk-forward 2016-2026).

Every evening each stock of the 300 most-traded gets ~35 features (momentum 1d-1y, mean reversion, trend,
volatility, volume, 52-week position, strength vs the market, Vix Fix, WaveTrend, squeeze, market regime). A
gradient-boosted model, retrained every week on all history, scores which stocks should beat the others over the
next 10 trading days. The top picks are sent as 'AI pick' tips: buy at the next open, sell after 10 trading days
(alert), wide 4 x ATR safety stop.
Walk-forward test, net of 0.35% costs: top-5 picks +0.82% per 10 days vs +0.34% for the average stock; beat the
average in 8 of 11 years; untouched last 3 years +0.94% vs +0.30%. Only ~52% of picks end in profit - the edge is
in the average, not the hit rate (ranked 6/10, risk 1%).
"""
import pickle
import time

import numpy as np
import pandas as pd

from .config import DATA, get_logger, load_settings

log = get_logger()
MODEL_F = DATA / "ml_model.pkl"
H, STOP_ATR, RANK, RISK_PCT = 10, 4.0, 6, 1.0
# independent re-test (BACKTEST_VALIDATION.md, 17 Nov 2026): the original "8 of 11 years" compared the picks after
# costs with the average stock before extra trading costs; honest after-cost comparison below
STATS = {"pick_avg": 0.73, "edge_before_costs": 0.48, "years_better": "6 of 11", "holdout_pick": 0.84, "win": 53.3}
STOCK = ["r1", "r5", "r20", "r60", "r120", "r250", "r250_20", "rsi2", "rsi14", "d20", "d50", "d200", "s50_200",
         "atr_pct", "vol20", "vol60", "vol_ratio", "vratio", "turnover", "hi52", "lo52", "wvf", "wt1", "sqz", "gap",
         "rngpos", "dn_days", "rs_r20", "rs_r60"]
MARKET = ["n_r5", "n_r20", "n_rsi2", "n_up200", "n_vol20", "breadth"]


def _ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False).mean().values


def _rsi(c, n):
    d = np.diff(c, prepend=c[0])
    up = pd.Series(np.clip(d, 0, None)).ewm(alpha=1 / n, adjust=False).mean().values
    dn = pd.Series(np.clip(-d, 0, None)).ewm(alpha=1 / n, adjust=False).mean().values
    return 100 - 100 / (1 + up / np.where(dn == 0, np.nan, dn))


def features(d):
    """d = adjusted daily bars (open/high/low/close/volume). -> DataFrame of stock features (+ fwd target)."""
    o, h, l, c, v = (d[k].values.astype(float) for k in ("open", "high", "low", "close", "volume"))
    s = pd.Series(c)
    lr = lambda k: np.log(c / s.shift(k).values)
    sma = lambda k: s.rolling(k).mean().values
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    atr = pd.Series(tr).ewm(alpha=1 / 14, adjust=False).mean().values
    ret = s.pct_change().values
    vol20, vol60 = pd.Series(ret).rolling(20).std().values, pd.Series(ret).rolling(60).std().values
    hi, lo = s.rolling(250).max().values, s.rolling(250).min().values
    hc = s.rolling(22).max().values
    ap = (h + l + c) / 3
    esa = _ema(ap, 10)
    dd = _ema(np.abs(ap - esa), 10)
    wt1 = _ema(np.nan_to_num((ap - esa) / (0.015 * np.where(dd == 0, np.nan, dd))), 21)
    basis, dev = sma(20), 2 * s.rolling(20).std(ddof=0).values
    rng = pd.Series(tr).rolling(20).mean().values
    with np.errstate(all="ignore"):
        f = pd.DataFrame({
            "r1": lr(1), "r5": lr(5), "r20": lr(20), "r60": lr(60), "r120": lr(120), "r250": lr(250),
            "r250_20": lr(250) - lr(20), "rsi2": _rsi(c, 2), "rsi14": _rsi(c, 14),
            "d20": c / sma(20) - 1, "d50": c / sma(50) - 1, "d200": c / sma(200) - 1,
            "s50_200": sma(50) / sma(200) - 1, "atr_pct": atr / c, "vol20": vol20, "vol60": vol60,
            "vol_ratio": vol20 / vol60,
            "vratio": pd.Series(v).rolling(5).mean().values / pd.Series(v).rolling(60).mean().values,
            "turnover": np.log1p(pd.Series(c * v).rolling(20).median().values), "hi52": c / hi - 1, "lo52": c / lo - 1,
            "wvf": (hc - l) / hc, "wt1": wt1,
            "sqz": ((basis - dev > basis - 1.5 * rng) & (basis + dev < basis + 1.5 * rng)).astype(float),
            "gap": o / np.r_[np.nan, c[:-1]] - 1, "rngpos": (c - l) / np.where(h - l == 0, np.nan, h - l),
            "dn_days": pd.Series((np.diff(c, prepend=c[0]) < 0).astype(float)).rolling(5).sum().values,
            "atr": atr,
        }, index=d.index)
    f["fwd"] = np.r_[o[1 + H:] / o[1:-H] - 1, np.full(H + 1, np.nan)][:len(c)] if len(c) > H + 1 else np.nan
    for k in (5, 20):                        # D112: other holding periods for the strategy discovery engine
        f[f"fwd{k}"] = np.r_[o[1 + k:] / o[1:-k] - 1, np.full(k + 1, np.nan)][:len(c)] if len(c) > k + 1 else np.nan
    return f


def _market():
    from . import data_prices
    nf = data_prices.load("NIFTY50")["close"]
    return pd.DataFrame({"n_r5": np.log(nf / nf.shift(5)), "n_r20": np.log(nf / nf.shift(20)),
                         "n_rsi2": pd.Series(_rsi(nf.values, 2), index=nf.index),
                         "n_up200": (nf > nf.rolling(200).mean()).astype(float),
                         "n_vol20": nf.pct_change().rolling(20).std()})


def _adjusted(sym):
    from . import data_prices
    d0 = data_prices.load(sym)
    if d0 is None or len(d0) < 300:
        return None
    f = (d0["adj_close"] / d0["close"]).fillna(1.0) if "adj_close" in d0 else 1.0
    d = pd.DataFrame({"open": d0["open"] * f, "high": d0["high"] * f, "low": d0["low"] * f,
                      "close": d0["adj_close"] if "adj_close" in d0 else d0["close"], "volume": d0["volume"],
                      "raw_close": d0["close"]}).dropna()
    return d if len(d) >= 300 else None


def _finish(P, mk):
    P = P.merge(mk, left_on="date", right_index=True, how="left")
    P["breadth"] = P.groupby("date")["d50"].transform(lambda x: (x > 0).mean())
    P["rs_r20"] = P["r20"] - P["n_r20"]
    P["rs_r60"] = P["r60"] - P.groupby("date")["r60"].transform("median")
    P = P.replace([np.inf, -np.inf], np.nan)
    X = P.groupby("date")[STOCK].rank(pct=True)
    X[MARKET] = P[MARKET]
    return P, X


def panel():
    """Training panel: point-in-time top-300 members, 2012+."""
    from .config import DATA as D
    u = pd.read_csv(D / "universe_history.csv")
    u["asof"] = pd.to_datetime(u["asof"])
    u = u[u["rank"] <= 300]
    members = {a: set(g["symbol"]) for a, g in u.groupby("asof")}
    months = sorted(members)
    parts = []
    for sym in sorted(set(u["symbol"])):
        d = _adjusted(sym)
        if d is None:
            continue
        d = d[d.index >= "2012-01-01"]
        m = np.zeros(len(d), bool)
        for i, a in enumerate(months):
            b = months[i + 1] if i + 1 < len(months) else pd.Timestamp("2100-01-01")
            if sym in members[a]:
                m |= (d.index >= a) & (d.index < b)
        f = features(d)
        f = f[m & (np.arange(len(d)) >= 260)]
        if len(f):
            f["sym"] = sym
            parts.append(f)
    P = pd.concat(parts)
    P.index.name = "date"
    return _finish(P.reset_index(), _market())


MODELS_DIR = DATA / "ml_models"
MIN_VAL_IC = 0.02           # the walk-forward test averaged 0.053; below 0.02 the model is not trusted


def _fit(X, y):
    from sklearn.ensemble import HistGradientBoostingRegressor
    mdl = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, max_leaf_nodes=31, min_samples_leaf=800,
                                        l2_regularization=1.0, random_state=0)
    mdl.fit(X, y)
    return mdl


def train():
    """Weekly retrain WITH A GATE (audit 17 Nov): first a check model is trained on data that ends 15 trading days
    before the last ~12 months and must still rank stocks usefully on those unseen months (mean daily rank
    correlation >= MIN_VAL_IC). Only then the production model (all data) replaces the current one; the previous
    versions are kept for rollback. A failed gate keeps the current model and tells the owner."""
    t0 = time.time()
    P, X = panel()
    y = P.groupby("date")["fwd"].rank(pct=True)
    dates = pd.Series(sorted(P["date"].unique()))
    labelled = dates[dates <= P.loc[y.notna(), "date"].max()]
    val_start = labelled.iloc[max(0, len(labelled) - 250)]
    cut = dates.iloc[max(0, dates.searchsorted(val_start) - 15)]
    tr = y.notna() & (P["date"] < cut) & (P["date"].dt.dayofyear % 2 == 0)
    va = y.notna() & (P["date"] >= val_start)
    chk = _fit(X[tr], y[tr])
    pv = pd.Series(chk.predict(X[va]), index=P.index[va])
    ic = P.loc[va].assign(p=pv).groupby("date").apply(lambda g: g["p"].corr(g["fwd"], method="spearman")).mean()
    ok_rows = y.notna() & (P["date"].dt.dayofyear % 2 == 0)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    meta = {"trained": str(pd.Timestamp.now().date()), "rows": int(ok_rows.sum()), "val_ic": round(float(ic), 4),
            "val_from": str(pd.Timestamp(val_start).date())}
    if not (ic == ic) or ic < MIN_VAL_IC:
        log.warning("AI picks: new model REJECTED (validation rank-correlation %.3f < %.2f) - current model kept",
                    ic, MIN_VAL_IC)
        try:
            from . import telegram
            telegram.send(load_settings(), f"⚠️ AI picks: this week's retrained model failed its validation "
                                           f"(rank-correlation {ic:.3f} on the last 12 unseen months, needs "
                                           f"{MIN_VAL_IC}). The previous model stays in use.", label="autopilot")
        except Exception:
            pass
        cur = _load_model_file()
        if cur:
            cur["trained"] = meta["trained"]          # do not retry every evening; the next try is next week
            cur.setdefault("history", []).append(dict(meta, accepted=False))
            MODEL_F.write_bytes(pickle.dumps(cur))
            return cur["model"]
        return None
    mdl = _fit(X[ok_rows], y[ok_rows])
    rec = dict(meta, model=mdl, accepted=True)
    MODEL_F.write_bytes(pickle.dumps(rec))
    (MODELS_DIR / f"model_{meta['trained']}.pkl").write_bytes(pickle.dumps(rec))
    for old in sorted(MODELS_DIR.glob("model_*.pkl"))[:-4]:      # keep the last 4 versions for rollback
        old.unlink()
    log.info("AI picks: model retrained on %d rows, validation rank-correlation %.3f, in %.0fs",
             meta["rows"], ic, time.time() - t0)
    return mdl


def _load_model_file():
    try:
        return pickle.loads(MODEL_F.read_bytes())
    except Exception:
        return None


def model(max_age_days=7):
    m = _load_model_file()
    if m and (pd.Timestamp.now() - pd.Timestamp(m["trained"])).days <= max_age_days:
        return m["model"]
    return train()


def score_today():
    """-> DataFrame (symbol, score, close(raw), atr(raw)) for today's top-300, best first."""
    from .high_prob import universe
    try:   # stocks only (ETFs / funds are not on the NSE equity list)
        from .tipcheck import equity_list
        eq = set(equity_list()["SYMBOL"].astype(str))
    except Exception:
        eq = None
    rows = []
    for s in universe():
        if eq is not None and s not in eq:
            continue
        d = _adjusted(s)
        if d is None:
            continue
        f = features(d).iloc[[-1]].copy()
        f["sym"], f["close"] = s, float(d["raw_close"].iloc[-1])
        f["atr"] = float(f["atr"].iloc[0]) * float(d["raw_close"].iloc[-1]) / float(d["close"].iloc[-1])
        rows.append(f)
    if not rows:
        return pd.DataFrame()
    P = pd.concat(rows)
    P.index.name = "date"
    P = P.reset_index()
    P["date"] = P["date"].max()                       # one cross-section (stocks with a stale last bar included)
    P, X = _finish(P, _market())
    mdl = model()
    if mdl is None:
        log.warning("AI picks: no validated model - no AI picks today")
        return pd.DataFrame()
    P["score"] = mdl.predict(X)
    return P.sort_values("score", ascending=False)[["sym", "score", "close", "atr"]].rename(columns={"sym": "symbol"})


def send_evening(day, settings=None, scored=None):
    from .live_engine import already, issue_tip, load_tips, send, tv_link
    s = settings or load_settings()
    if not s.get("ai_picks", True):
        return 0
    try:
        from .autopilot import rules as _ap
        if _ap().get("ai_paused"):
            log.info("AI picks: paused by the autopilot (live record)")
            return 0
    except Exception:
        pass
    sc = score_today() if scored is None else scored
    if not len(sc):
        return 0
    t = load_tips()
    open_syms = set(t.loc[t["status"] == "open", "symbol"].astype(str)) if len(t) else set()
    open_ai = int(((t["status"] == "open") & (t.get("setup", "") == "AI")).sum()) if len(t) and "setup" in t else 0
    room = max(0, int(s.get("ai_max_open", 10)) - open_ai)
    cap = float(s.get("capital", 45000))
    n = 0
    for _, r in sc.head(int(s.get("ai_top", 5)) * 3).iterrows():
        if n >= min(room, int(s.get("ai_top", 5))):
            break
        sym = r["symbol"]
        if sym in open_syms or already(sym, "NORMAL", str(day)):
            continue
        from . import safety
        stop = round(r["close"] - STOP_ATR * r["atr"], 2)
        qty = safety.size(r["close"], stop, s, RISK_PCT)
        if qty < 1:
            continue
        msg = (f"• AI pick (machine-learning ranker, 10-day hold)\n\n"
             f"Buy #{sym} at the next market open ≈ {r['close']:,.2f} 📊\n\n"
             f"SL at {stop:,.2f} ❗️ (wide safety stop)\n\n"
             f"Exit: sell after 10 trading days - I'll alert you\n\n"
             f"{RISK_PCT:g}% Risk\n\n"
             f"⭐ RANK - {RANK}/10 · Qty {qty} · top of today's market-wide AI ranking. Tested walk-forward: the "
             f"top picks made {STATS['pick_avg']:+.2f}% per 10 days after costs ({STATS['edge_before_costs']:+.2f}% "
             f"more than the average stock before costs, but after costs better in only {STATS['years_better']} "
             f"years) - a SMALL edge, lowest-priority tip; ~{STATS['win']:.0f}% of picks win.\n\n{tv_link(sym, daily=True)}")
        if issue_tip({"time": str(pd.Timestamp.now(tz='Asia/Kolkata').tz_localize(None))[:16], "type": "NORMAL",
                      "symbol": sym, "side": "buy", "entry": r["close"], "stop": stop, "targets": "", "rank": RANK,
                      "qty": qty, "status": "open", "hit": 0, "day": str(day), "setup": "AI"}, msg, s):
            n += 1
    log.info("AI picks: %d sent (room %d)", n, room)
    return n


def evening_exits(day):
    from .autopilot import close_tip
    from .live_engine import _LOCK, TIPS_F, load_tips, write_tips, send
    msgs = []
    with _LOCK:
        t = load_tips()
        if not len(t) or "setup" not in t:
            return msgs
        for i, r in t[(t["status"] == "open") & (t["setup"] == "AI")].iterrows():
            d = _adjusted(r["symbol"])
            if d is None:
                continue
            since = d[d.index > pd.Timestamp(str(r["day"]))]
            if len(since) >= H:
                raw = float(d["raw_close"].iloc[-1])
                close_tip(t, i, "time", raw)
                msgs.append(f"⌛ #{r['symbol']} (AI pick) - 10 trading days done: sell at the next market open "
                            f"(now {raw:,.2f}, {(raw / float(r['entry']) - 1) * 100:+.1f}% from the tip).")
        write_tips(t)
    for m in msgs:
        send(m, label="exit alert")
    return msgs
