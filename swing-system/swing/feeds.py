"""Data-hungry items of the owner's library, ready to run as soon as their data exists.

1. Built from data the system ALREADY collects every evening:
   * F&O end-of-day file (data/fno, kept forever): open-interest change, price/OI quadrant, futures basis
     (% and annualised), days to roll, calendar spread, put/call OI and volume ratios, max pain, and - from the
     option prices - at-the-money implied volatility, its rank/percentile, 25-delta-style skew and term slope.
     (IV fields exist from 2026-11-04 onwards; rank/percentile need ~1 year of them, so they fill in over time.)
   * Market breadth from the stock universe itself: advance/decline line and ratio, McClellan oscillator and
     summation, Arms index (TRIN), high-low index.
   * Execution estimates from daily data: participation rate and square-root market-impact for the planned size.
2. Waiting for a feed you may add later (e.g. Kite Connect ticks or another vendor): drop files into data/feeds/
   with the columns below and every function here starts working - no code change needed.
     data/feeds/ticks/<SYMBOL>/<YYYY-MM-DD>.csv   ts, price, qty[, side(+1 buy aggressor / -1 sell)]
     data/feeds/book/<SYMBOL>/<YYYY-MM-DD>.csv    ts, bid, ask, bid_qty, ask_qty[, bid_orders, ask_orders, cancels]
     data/feeds/auction/<YYYY-MM-DD>.csv          symbol, buy_qty, sell_qty, price   (closing auction)
     data/feeds/funding/<SYMBOL>.csv              ts, funding_rate[, long_liq, short_liq]  (crypto perpetuals only)
"""
import math

import numpy as np
import pandas as pd

from .config import DATA

FEEDS = DATA / "feeds"
RISK_FREE = 0.065


# ----------------------------------------------------------------------------- F&O (already collected)
def _bs_price(S, K, T, sig, call):
    from math import erf, exp, log, sqrt
    if T <= 0 or sig <= 0:
        return max(0.0, (S - K) if call else (K - S))
    d1 = (log(S / K) + (RISK_FREE + sig * sig / 2) * T) / (sig * sqrt(T))
    d2 = d1 - sig * sqrt(T)
    N = lambda x: 0.5 * (1 + erf(x / sqrt(2)))
    if call:
        return S * N(d1) - K * exp(-RISK_FREE * T) * N(d2)
    return K * exp(-RISK_FREE * T) * N(-d2) - S * N(-d1)


def implied_vol(price, S, K, T, call):
    """Black-Scholes implied volatility by bisection (European approximation of NSE stock options)."""
    if not (price > 0 and S > 0 and K > 0 and T > 0):
        return np.nan
    intrinsic = max(0.0, (S - K) if call else (K - S))
    if price <= intrinsic + 1e-9:
        return np.nan
    lo, hi = 1e-3, 5.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if _bs_price(S, K, T, mid, call) > price:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def option_iv_fields(opt, spot, day):
    """From one underlying's raw option rows (UDiFF columns): ATM IV (near and next expiry), skew, volumes."""
    out = {}
    if opt.empty or not spot or not np.isfinite(spot):
        return out
    exps = sorted(opt["XpryDt"].unique())
    def atm_iv(exp):
        g = opt[opt["XpryDt"] == exp]
        T = max((pd.Timestamp(exp) - pd.Timestamp(day)).days, 1) / 365
        ks = np.sort(g["StrkPric"].unique())
        if not len(ks):
            return np.nan, T, g
        k = ks[np.argmin(np.abs(ks - spot))]
        ivs = [implied_vol(float(r["ClsPric"]), spot, k, T, r["OptnTp"] == "CE") for _, r in g[g["StrkPric"] == k].iterrows()]
        ivs = [x for x in ivs if np.isfinite(x)]
        return (float(np.mean(ivs)) if ivs else np.nan), T, g
    iv0, T0, g0 = atm_iv(exps[0])
    out["atm_iv"] = iv0
    if len(exps) > 1:
        out["atm_iv_next"] = atm_iv(exps[1])[0]
    ks = np.sort(g0["StrkPric"].unique())
    if len(ks) > 2:
        kp, kc = ks[np.argmin(np.abs(ks - 0.95 * spot))], ks[np.argmin(np.abs(ks - 1.05 * spot))]
        p = g0[(g0["StrkPric"] == kp) & (g0["OptnTp"] == "PE")]
        cc = g0[(g0["StrkPric"] == kc) & (g0["OptnTp"] == "CE")]
        if len(p) and len(cc):
            out["skew_95_105"] = implied_vol(float(p["ClsPric"].iloc[0]), spot, kp, T0, False) - \
                implied_vol(float(cc["ClsPric"].iloc[0]), spot, kc, T0, True)
    vol_col = "TtlTradgVol" if "TtlTradgVol" in g0 else None
    if vol_col:
        out["call_vol"] = float(g0.loc[g0["OptnTp"] == "CE", vol_col].sum())
        out["put_vol"] = float(g0.loc[g0["OptnTp"] == "PE", vol_col].sum())
    return out


def fno_panel(B):
    """Daily F&O fields aligned to B (date x stock); NaN where a stock is not in F&O or before the data starts."""
    if "_fno" in B:
        return B["_fno"]
    from .intel_fno import DIR
    c = B["c"]
    rows = []
    for f in sorted(DIR.glob("*.csv")):
        if f.stat().st_size == 0:
            continue
        d = pd.Timestamp(f.stem)
        if d < c.index[0] or d > c.index[-1]:
            continue
        x = pd.read_csv(f)
        x["date"] = d
        rows.append(x)
    out = {}
    if rows:
        df = pd.concat(rows, ignore_index=True)
        df = df[df["symbol"].isin(set(c.columns))]
        for k in df.columns.drop(["symbol", "date"]):
            if not pd.api.types.is_numeric_dtype(df[k]):
                continue
            out[k] = df.pivot_table(index="date", columns="symbol", values=k).reindex(index=c.index, columns=c.columns)
        for k in ("fut_expiry", "opt_expiry"):
            if k in df:
                out[k] = df.pivot(index="date", columns="symbol", values=k).reindex(index=c.index, columns=c.columns)
    B["_fno"] = out
    return out


def fno_feature(fid, B):
    F = fno_panel(B)
    if not F:
        return None
    c = B["c"]
    g = lambda k: F.get(k)
    def days_to(k):
        e = g(k)
        if e is None:
            return None
        ed = e.apply(pd.to_datetime, errors="coerce")
        idx = pd.DataFrame(np.repeat(c.index.values[:, None], c.shape[1], 1), index=c.index, columns=c.columns)
        return (ed - idx).apply(lambda s: s.dt.days)
    iv = g("atm_iv")
    rank = (lambda x: (x - x.rolling(252, min_periods=60).min()) / (x.rolling(252, min_periods=60).max() - x.rolling(252, min_periods=60).min())) if iv is not None else None
    with np.errstate(invalid="ignore", divide="ignore"):
        Fs = {
            "open_interest_change": lambda: g("fut_oi_chg"),
            "open_interest_delta": lambda: g("fut_oi_chg"),
            "price_oi_quadrant": lambda: (np.sign(g("fut_close") - g("fut_prev")) * 2 + np.sign(g("fut_oi_chg"))),
            "futures_basis": lambda: g("fut_close") - g("spot"),
            "basis_percent": lambda: (g("fut_close") / g("spot") - 1) * 100,
            "basis_annualised": lambda: (g("fut_close") / g("spot") - 1) * 365 / days_to("fut_expiry").clip(lower=1) * 100,
            "futures_roll_days": lambda: days_to("fut_expiry"),
            "calendar_spread": lambda: g("fut_next_close") - g("fut_close") if g("fut_next_close") is not None else None,
            "options_put_call_open_interest_ratio": lambda: g("pcr"),
            "options_put_call_volume_ratio": lambda: g("put_vol") / g("call_vol") if g("put_vol") is not None else None,
            "options_max_pain": lambda: g("max_pain"),
            "options_implied_volatility_rank": lambda: rank(iv) if iv is not None else None,
            "options_implied_volatility_percentile": lambda: iv.rolling(252, min_periods=60).rank(pct=True) if iv is not None else None,
            "options_skew_25d": lambda: g("skew_95_105"),
            "iv_skew": lambda: g("skew_95_105"),
            "options_term_structure": lambda: g("atm_iv_next") - iv if iv is not None and g("atm_iv_next") is not None else None,
            "iv_term_slope": lambda: g("atm_iv_next") - iv if iv is not None and g("atm_iv_next") is not None else None,
        }
    if fid not in Fs:
        raise KeyError(fid)
    return Fs[fid]()


FNO_FEATURES = ["open_interest_change", "price_oi_quadrant", "futures_basis", "basis_percent", "basis_annualised",
                "futures_roll_days", "calendar_spread", "options_put_call_open_interest_ratio",
                "options_put_call_volume_ratio", "options_max_pain", "options_implied_volatility_rank",
                "options_implied_volatility_percentile", "options_skew_25d", "iv_skew", "options_term_structure",
                "iv_term_slope"]
FNO_GROWING = {"options_put_call_volume_ratio", "options_implied_volatility_rank", "options_implied_volatility_percentile",
               "options_skew_25d", "iv_skew", "options_term_structure", "iv_term_slope", "calendar_spread"}


# ----------------------------------------------------------------------------- breadth from the universe itself
def breadth(fid, B):
    c, v, h, l, m = B["c"], B["v"], B["h"], B["l"], B["member"]
    chg = c.diff()
    adv = ((chg > 0) & m).sum(axis=1).astype(float)
    dec = ((chg < 0) & m).sum(axis=1).astype(float)
    advv = (v.where((chg > 0) & m)).sum(axis=1)
    decv = (v.where((chg < 0) & m)).sum(axis=1)
    nh = ((h >= h.rolling(252, min_periods=200).max()) & m).sum(axis=1).astype(float)
    nl = ((l <= l.rolling(252, min_periods=200).min()) & m).sum(axis=1).astype(float)
    net = (adv - dec) / (adv + dec).replace(0, np.nan)
    mcc = net.ewm(span=19, adjust=False).mean() - net.ewm(span=39, adjust=False).mean()
    F = {
        "market_breadth_ad_line": lambda: (adv - dec).cumsum(),
        "market_breadth_ad_ratio": lambda: adv / dec.replace(0, np.nan),
        "market_breadth_mcclellan_oscillator": lambda: mcc * 1000,
        "market_breadth_mcclellan_summation": lambda: (mcc * 1000).cumsum(),
        "market_breadth_trin_arms": lambda: (adv / dec.replace(0, np.nan)) / (advv / decv.replace(0, np.nan)),
        "market_breadth_high_low_index": lambda: (nh / (nh + nl).replace(0, np.nan) * 100).rolling(10).mean(),
    }
    if fid not in F:
        raise KeyError(fid)
    s = F[fid]()
    return pd.DataFrame(np.repeat(s.to_numpy()[:, None], c.shape[1], 1), index=c.index, columns=c.columns)


BREADTH = ["market_breadth_ad_line", "market_breadth_ad_ratio", "market_breadth_mcclellan_oscillator",
           "market_breadth_mcclellan_summation", "market_breadth_trin_arms", "market_breadth_high_low_index"]


# ----------------------------------------------------------------------------- execution estimates
def participation_rate(qty, avg_daily_volume):
    return qty / avg_daily_volume if avg_daily_volume else np.nan


def market_impact_bps(qty, avg_daily_volume, daily_vol, k=1.0):
    """Square-root impact model: k * sigma_daily * sqrt(qty / ADV), in basis points."""
    if not avg_daily_volume or not np.isfinite(daily_vol):
        return np.nan
    return k * daily_vol * math.sqrt(max(qty, 0) / avg_daily_volume) * 1e4


# ----------------------------------------------------------------------------- feeds you can add later
def _read(kind, sym, day):
    f = FEEDS / kind / sym / f"{pd.Timestamp(day):%Y-%m-%d}.csv"
    return pd.read_csv(f, parse_dates=["ts"]) if f.exists() else None


def available(kind):
    d = FEEDS / kind
    return d.exists() and any(d.rglob("*.csv"))


def tick_sign(t):
    """Aggressor side if given, else the tick rule (+1 uptick, -1 downtick, carry forward on zero ticks)."""
    if "side" in t:
        return t["side"].astype(float)
    s = np.sign(t["price"].diff()).replace(0, np.nan).ffill().fillna(0)
    return s


def tick_metrics(t, book=None, atr=None):
    """Microstructure metrics for one stock-day of ticks (and optional quotes)."""
    s = tick_sign(t)
    sv = s * t["qty"]
    dp = t["price"].diff()
    out = {
        "volume_delta": float(sv.sum()), "cumulative_volume_delta": float(sv.cumsum().iloc[-1]),
        "cumulative_delta": float(sv.cumsum().iloc[-1]), "tick_rule_signed_volume": float(sv.sum()),
        "trade_imbalance": float(sv.sum() / t["qty"].sum()) if t["qty"].sum() else np.nan,
        "trade_sign_imbalance": float(s.mean()),
        "trade_intensity": float(len(t) / max((t["ts"].max() - t["ts"].min()).total_seconds() / 60, 1)),
    }
    cvd = sv.groupby(t["ts"]).sum().cumsum()
    last30 = cvd[cvd.index >= cvd.index.max() - pd.Timedelta("30min")]
    out["cumulative_delta_change"] = float(last30.iloc[-1] - last30.iloc[0]) if len(last30) else np.nan
    x = sv.iloc[1:].to_numpy(); y = dp.iloc[1:].to_numpy()
    out["kyle_lambda"] = float(np.dot(x, y) / np.dot(x, x)) if np.dot(x, x) else np.nan
    t5 = t.set_index("ts")["price"].resample("5min").last().dropna()
    out["price_impact_5m"] = float(np.corrcoef(sv.groupby(t["ts"].dt.floor("5min")).sum().reindex(t5.index).fillna(0),
                                               t5.diff().fillna(0))[0, 1]) if len(t5) > 3 else np.nan
    if book is not None and len(book):
        b = book
        mid = (b["bid"] + b["ask"]) / 2
        out["quoted_spread_bps"] = float(((b["ask"] - b["bid"]) / mid).mean() * 1e4)
        if atr:
            out["spread_to_atr"] = float((b["ask"] - b["bid"]).mean() / atr)
        out["microprice"] = float(((b["bid"] * b["ask_qty"] + b["ask"] * b["bid_qty"]) / (b["bid_qty"] + b["ask_qty"])).iloc[-1])
        out["order_book_imbalance"] = float(((b["bid_qty"] - b["ask_qty"]) / (b["bid_qty"] + b["ask_qty"])).mean())
        out["order_book_depth_imbalance"] = out["order_book_imbalance"]
        out["queue_imbalance"] = float((b["bid_qty"] / (b["bid_qty"] + b["ask_qty"])).mean())
        # order-flow imbalance (Cont, Kukanov & Stoikov)
        e = ((b["bid"] >= b["bid"].shift()) * b["bid_qty"] - (b["bid"] <= b["bid"].shift()) * b["bid_qty"].shift()
             - (b["ask"] <= b["ask"].shift()) * b["ask_qty"] + (b["ask"] >= b["ask"].shift()) * b["ask_qty"].shift())
        out["order_flow_imbalance"] = float(e.fillna(0).sum())
        if "cancels" in b:
            out["order_cancel_rate"] = float(b["cancels"].sum() / max(len(t), 1))
        q = pd.merge_asof(t.sort_values("ts"), b.assign(mid=mid).sort_values("ts")[["ts", "mid"]], on="ts")
        out["effective_spread_bps"] = float((2 * (q["price"] - q["mid"]).abs() / q["mid"]).mean() * 1e4)
        later = pd.merge_asof(t.assign(ts5=t["ts"] + pd.Timedelta("5min")).sort_values("ts5"),
                              b.assign(mid=mid).sort_values("ts")[["ts", "mid"]].rename(columns={"ts": "ts5"}), on="ts5")
        out["realised_spread"] = float((2 * s.values * (later["price"] - later["mid"]) / later["mid"]).mean() * 1e4)
        # absorption: heavy aggressive selling while the bid holds (bid) / buying while the ask holds (ask)
        out["absorption_bid"] = float((sv < 0).mean() > 0.6 and b["bid"].iloc[-1] >= b["bid"].iloc[0])
        out["absorption_ask"] = float((sv > 0).mean() > 0.6 and b["ask"].iloc[-1] <= b["ask"].iloc[0])
        # iceberg: repeated fills at one price beyond the displayed size
        fills = t.groupby("price")["qty"].sum()
        shown = b["bid_qty"].median() + b["ask_qty"].median()
        out["iceberg_order_inference"] = float((fills > 5 * shown).any()) if shown else np.nan
    return out


def daily_tick_feature(fid, sym, day):
    t = _read("ticks", sym, day)
    if t is None:
        return None
    return tick_metrics(t, _read("book", sym, day)).get(fid)


def closing_auction_imbalance(day):
    f = FEEDS / "auction" / f"{pd.Timestamp(day):%Y-%m-%d}.csv"
    if not f.exists():
        return None
    a = pd.read_csv(f)
    return (a["buy_qty"] - a["sell_qty"]) / (a["buy_qty"] + a["sell_qty"])


def funding_features(sym):
    f = FEEDS / "funding" / f"{sym}.csv"
    if not f.exists():
        return None
    x = pd.read_csv(f, parse_dates=["ts"]).set_index("ts")
    out = pd.DataFrame({"funding_rate": x["funding_rate"],
                        "funding_rate_zscore": (x["funding_rate"] - x["funding_rate"].rolling(90).mean()) / x["funding_rate"].rolling(90).std()})
    if {"long_liq", "short_liq"} <= set(x.columns):
        out["liquidation_imbalance"] = (x["short_liq"] - x["long_liq"]) / (x["short_liq"] + x["long_liq"])
    return out


TICK_FEATURES = ["volume_delta", "cumulative_volume_delta", "cumulative_delta", "tick_rule_signed_volume", "trade_imbalance",
                 "trade_sign_imbalance", "trade_intensity", "kyle_lambda", "price_impact_5m", "quoted_spread_bps",
                 "microprice", "order_book_imbalance", "order_book_depth_imbalance", "queue_imbalance",
                 "order_flow_imbalance", "order_cancel_rate", "effective_spread_bps", "realised_spread",
                 "cumulative_delta_change", "absorption_bid", "absorption_ask", "iceberg_order_inference", "spread_to_atr"]
FUNDING = ["funding_rate", "funding_rate_zscore", "liquidation_imbalance"]
