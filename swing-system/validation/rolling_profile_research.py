"""Test of the TradingView 'Rolling Candle Profile with Buy/Sell Signals' (Zeiierman) BUY rule on NSE data.

The script's source could not be downloaded here, so it is REBUILT from the author's published description:
  * anchor = EMA(21) of close
  * 12 price layers from the candle body's middle to the anchor; each layer's pressure = recency-weighted
    (decay 0.95/bar), price-localised (Gaussian, width 1 x ATR) buying vs selling dominance (B-S)/(B+S) of the last 60 candles
  * candle pressure ('Price Pressure' mode): displacement vs ATR, candle direction, close location, wick rejection;
    'Hybrid' mode also weights each candle by its relative volume
  * a layer is coloured when |pressure| >= 0.25 (dominance threshold); BUY = at least 7 green layers, price above a
    RISING anchor, fresh alignment (not true on the previous bar), at least 6 bars since the last BUY
Long-only, entry at the next bar's open, 0.35% round-trip costs (delivery). Daily: 13 years, point-in-time top-300.
Hourly: 147 liquid stocks, ~3 years. Development / holdout split at 2023-11 (daily) and 2025-06 (hourly).
"""
import sys

import numpy as np
import pandas as pd

ROOT = "/home/user/shri-labh-jewellers/swing-system"
sys.path.insert(0, ROOT)
from swing import data_prices  # noqa: E402

COST = 0.0035
WIN, LAYERS, DECAY, THR, MIN_BANDS, SPACING = 60, 12, 0.95, 0.25, 7, 6


def atr(d, n=14):
    tr = pd.concat([d.high - d.low, (d.high - d.close.shift()).abs(), (d.low - d.close.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()


def candle_pressure(d, a):
    rng = (d.high - d.low).replace(0, np.nan)
    cl = ((d.close - d.low) - (d.high - d.close)) / rng
    body = (d.close - d.open) / rng
    wick = ((np.minimum(d.open, d.close) - d.low) - (d.high - np.maximum(d.open, d.close))) / rng
    disp = ((d.close - d.close.shift()) / a).clip(-1, 1)
    return (0.3 * disp + 0.25 * body + 0.25 * cl + 0.2 * wick).clip(-1, 1).fillna(0)


def signals(d, mode="price"):
    """-> DataFrame with anchor, green count, red count, BUY, SELL (bool)."""
    a = atr(d)
    anc = d.close.ewm(span=21, adjust=False).mean()
    p = candle_pressure(d, a).values
    vol = (d.volume / d.volume.rolling(20).mean()).clip(0.2, 3).fillna(1).values if mode == "hybrid" else np.ones(len(d))
    tp = ((d.high + d.low + d.close) / 3).values
    mid = ((d.open + d.close) / 2).values
    A, AT = anc.values, a.values
    n = len(d)
    green, red, net = np.zeros(n), np.zeros(n), np.zeros(n)
    rec = DECAY ** np.arange(WIN)[::-1]                        # oldest .. newest
    frac = np.linspace(0, 1, LAYERS)
    for t in range(WIN + 20, n):
        if not np.isfinite(AT[t]) or AT[t] <= 0:
            continue
        lv = mid[t] + (A[t] - mid[t]) * frac                   # 12 layers body -> anchor
        sl = slice(t - WIN + 1, t + 1)
        k = np.exp(-0.5 * ((lv[:, None] - tp[sl][None, :]) / AT[t]) ** 2)
        w = k * (rec * vol[sl])[None, :]
        bp = (w * np.clip(p[sl], 0, None)[None, :]).sum(1)          # buying pressure at each layer
        sp = (w * np.clip(-p[sl], 0, None)[None, :]).sum(1)         # selling pressure
        tot = bp + sp
        pr = np.where(tot > 1e-9, (bp - sp) / np.where(tot > 1e-9, tot, 1), 0)   # dominance -1..+1
        green[t], red[t], net[t] = (pr >= THR).sum(), (pr <= -THR).sum(), pr.mean()
    c = d.close.values
    rising = np.r_[False, A[1:] > A[:-1]]
    bull = (green >= MIN_BANDS) & (c > A) & rising & (net > 0)
    bear = (red >= MIN_BANDS) & (c < A) & ~rising & (net < 0)
    buy, sell = np.zeros(n, bool), np.zeros(n, bool)
    last_b = last_s = -999
    for t in range(1, n):
        if bull[t] and not bull[t - 1] and t - last_b >= SPACING:
            buy[t], last_b = True, t
        if bear[t] and not bear[t - 1] and t - last_s >= SPACING:
            sell[t], last_s = True, t
    return pd.DataFrame({"anchor": A, "green": green, "red": red, "buy": buy, "sell": sell,
                         "ema_cross": (c > A) & np.r_[True, c[:-1] <= A[:-1]] & rising}, index=d.index)


def run_trades(d, ent, ex_rule, stop_atr=None, tgt_atr=None, max_bars=60):
    o, h, l = d.open.values, d.high.values, d.low.values
    a = atr(d).values
    out, i, n = [], 0, len(d)
    while i < n - 2:
        if not ent[i] or not np.isfinite(a[i]):
            i += 1
            continue
        e = o[i + 1]
        st = e - stop_atr * a[i] if stop_atr else -np.inf
        tg = e + tgt_atr * a[i] if tgt_atr else np.inf
        j, px = i + 1, None
        while j < n - 1:
            if l[j] <= st:
                px = min(st, o[j]); break
            if h[j] >= tg:
                px = max(tg, o[j]); break
            if ex_rule[j] or j - (i + 1) >= max_bars - 1:
                px = o[j + 1]; break
            j += 1
        if px is None:
            break
        out.append((d.index[i + 1], px / e - 1 - COST, j - i))
        i = j + 1
    return out


def summary(R, split):
    rows = []
    for k, v in R.items():
        df = pd.DataFrame(v, columns=["date", "ret", "bars"])
        if not len(df):
            continue
        dev, ho = df[df.date < split], df[df.date >= split]
        w = lambda x: round((x.ret > 0).mean() * 100, 1) if len(x) else None
        rows.append({"test": k, "trades": len(df), "win%": w(df), "avg%": round(df.ret.mean() * 100, 2),
                     "avg_win%": round(df.ret[df.ret > 0].mean() * 100, 2),
                     "avg_loss%": round(df.ret[df.ret <= 0].mean() * 100, 2),
                     "dev_win%": w(dev), "HOLD_win%": w(ho), "HOLD_avg%": round(ho.ret.mean() * 100, 2) if len(ho) else None,
                     "bars_held": round(df.bars.mean(), 1)})
    return pd.DataFrame(rows)


def tests(d, s, nifty_up=None, R=None, mask=None):
    m = mask if mask is not None else np.ones(len(d), bool)
    nu = nifty_up if nifty_up is not None else np.ones(len(d), bool)
    below = (d.close.values < s.anchor.values)
    for name, ent in (("BUY signal", s.buy.values), ("plain EMA21 cross-up (no bands) - comparison", s.ema_cross.values)):
        e = ent & m
        R.setdefault(f"{name} | exit on SELL signal", []).extend(run_trades(d, e, s.sell.values))
        R.setdefault(f"{name} | exit close below anchor", []).extend(run_trades(d, e, below))
        R.setdefault(f"{name} | stop 1.5 ATR, target 3 ATR", []).extend(
            run_trades(d, e, np.zeros(len(d), bool), 1.5, 3.0, 20))
        R.setdefault(f"{name} + Nifty uptrend | exit close below anchor", []).extend(run_trades(d, e & nu, below))


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "daily"
    mode = sys.argv[2] if len(sys.argv) > 2 else "price"
    R = {}
    if which == "daily":
        u = pd.read_csv(f"{ROOT}/data/universe_history.csv")
        u["asof"] = pd.to_datetime(u["asof"])
        u = u[u["rank"] <= 300]
        members = {a: set(g["symbol"]) for a, g in u.groupby("asof")}
        months = sorted(members)
        nf = data_prices.load("NIFTY50")["close"]
        NUP = nf > nf.rolling(200).mean()
        for sym in sorted(set(u["symbol"])):
            d0 = data_prices.load(sym)
            if d0 is None or len(d0) < 300:
                continue
            f = (d0["adj_close"] / d0["close"]).fillna(1.0)
            d = pd.DataFrame({"open": d0.open * f, "high": d0.high * f, "low": d0.low * f, "close": d0.adj_close,
                              "volume": d0.volume}).dropna()
            d = d[d.index >= "2012-01-01"]
            if len(d) < 300:
                continue
            mm = np.zeros(len(d), bool)
            for i, a in enumerate(months):
                b = months[i + 1] if i + 1 < len(months) else pd.Timestamp("2100-01-01")
                if sym in members[a]:
                    mm |= (d.index >= a) & (d.index < b)
            tests(d, signals(d, mode), NUP.reindex(d.index).fillna(False).values, R, mm)
        split = "2023-11-01"
    else:
        import glob
        nf = data_prices.load("NIFTY50")["close"]
        NUP = nf > nf.rolling(200).mean()
        for fp in sorted(glob.glob(f"{ROOT}/data/intraday/*.csv")):
            d = pd.read_csv(fp, parse_dates=["Datetime"], index_col="Datetime").dropna()
            d = d[d.volume > 0] if mode == "hybrid" else d
            if len(d) < 500:
                continue
            nu = NUP.reindex(d.index.normalize()).ffill().fillna(False).values
            tests(d, signals(d, mode), nu, R)
        split = "2025-06-01"
    out = summary(R, split)
    print(f"== {which} / {mode} ==")
    print(out.to_string(index=False))
    out.to_csv(f"{ROOT}/validation/rolling_profile_{which}_{mode}.csv", index=False)
