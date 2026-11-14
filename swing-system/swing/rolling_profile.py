"""Rolling Candle Profile with Buy/Sell Signals - exact Python port (D104).

Original Pine script: (c) Zeiierman, licensed CC BY-NC-SA 4.0 (https://creativecommons.org/licenses/by-nc-sa/4.0/).
This port is a derivative for personal, non-commercial use and is shared under the same licence.
Default inputs (EMA 21 anchor, Price Pressure, chart timeframe, width 0.01, wick 0.85, dominance 0.25, 7 bands,
6-bar spacing). The final signal step (cut off in the source provided) follows the author's description: BUY = buy
pressure AND >= 7 coloured bands AND close above a RISING anchor, fresh, >= 6 bars since the last BUY; SELL mirrored.
"""
import numpy as np
import pandas as pd

BANDS, LOOK, ANCHOR_LEN = 12, 60, 21
PX_WIDTH, WICK_W, SIG_DOM, MIN_BANDS, SIG_GAP = 0.01, 0.85, 0.25, 7, 6
AGE = 0.5 ** (np.arange(LOOK) / 3.0)          # weight of the bar k bars ago


def clamp(x, lo, hi):
    return np.minimum(hi, np.maximum(lo, x))


def kernel(here, center, inv_w):
    q = 1.0 - np.abs(here - center) * inv_w
    return np.where(q <= 0, 0.0, q * q * (3.0 - 2.0 * q))


def pine_ema(x, n):
    """ta.ema: alpha 2/(n+1), seeded with the first value."""
    return pd.Series(x).ewm(alpha=2 / (n + 1), adjust=False).mean().values


def signals(d, mode="price", tick=0.05):
    o, h, l, c, vol = (d[k].values.astype(float) for k in ("open", "high", "low", "close", "volume"))
    n = len(d)
    is_price, is_hyb = mode == "price", mode == "hybrid"
    anchor = pine_ema(c, ANCHOR_LEN)
    pc = np.r_[o[0], c[:-1]]                       # nz(close[1], open)
    pc2 = np.r_[np.nan, np.nan, c[:-2]]
    hlc3 = (h + l + c) / 3
    r = np.maximum(h - l, tick)
    directional = clamp((c - o) / r, -1, 1)
    impulse = np.abs(directional)
    travel = clamp((c - pc) / r, -1.5, 1.5)
    close_loc = clamp((2 * c - h - l) / r, -1, 1)
    resp = clamp(0.55 * travel + 0.25 * directional + 0.20 * close_loc, -1.5, 1.5)
    force = np.abs(resp)
    prior = np.nan_to_num(pc - pc2)
    cont = np.where(prior * resp > 0, 1.45, np.where(prior * resp < 0, 0.55, 1.0))
    raw_v = np.where(np.nan_to_num(vol) > 0, vol, 1.0)
    v = raw_v * (0.65 + force * 0.70) if is_hyb else raw_v
    flow_dir = clamp(0.45 * directional + 0.55 * resp, -1, 1) if is_hyb else directional
    if is_price:
        buy = np.maximum(resp, 0) * (1 + force * 1.25) * cont * 2
        sell = np.maximum(-resp, 0) * (1 + force * 1.25) * cont * 2
    else:
        buy, sell = v * (1 + flow_dir) * 0.5, v * (1 - flow_dir) * 0.5
    low_w = np.maximum(0, np.minimum(o, c) - l) / r
    high_w = np.maximum(0, h - np.maximum(o, c)) / r
    low_rej = low_w * (0.35 + 1.2 * np.maximum(resp, 0)) if is_price else v * low_w
    high_rej = high_w * (0.35 + 1.2 * np.maximum(-resp, 0)) if is_price else v * high_w
    stall = (1 - clamp(force, 0, 1)) * 0.20 if is_price else v * (1 - impulse)
    bpx = c * 0.7 + h * 0.3 if is_price else (hlc3 * 0.75 + h * 0.25 if is_hyb else hlc3)
    spx = c * 0.7 + l * 0.3 if is_price else (hlc3 * 0.75 + l * 0.25 if is_hyb else hlc3)
    total_now = (buy + sell + low_rej + high_rej + stall) if is_price else v
    buy_ctr = np.where(buy > 0, bpx, hlc3)
    sell_ctr = np.where(sell > 0, spx, hlc3)
    low_ctr = np.where(low_rej > 0, (l + np.minimum(o, c)) * 0.5, l)
    high_ctr = np.where(high_rej > 0, (h + np.maximum(o, c)) * 0.5, h)
    stall_ctr = hlc3
    baseline = pine_ema(total_now, 55)
    scale = np.where(total_now > 0, np.minimum(1.0, np.maximum(baseline, 1e-6) * 20 / np.where(total_now > 0, total_now, 1)), 1.0)
    buy, sell, low_rej, high_rej, stall = buy * scale, sell * scale, low_rej * scale, high_rej * scale, stall * scale
    body_lo, body_hi = np.minimum(o, c), np.maximum(o, c)
    edge = np.where(anchor < body_lo, body_lo, np.where(anchor > body_hi, body_hi, np.nan))
    vol_base = np.maximum(1e-6, baseline)
    base_w = np.maximum(h - l, tick) * PX_WIDTH
    base_wick_w = base_w * 0.6
    vis = np.zeros(n, int)
    buy_b, sell_b = np.zeros(n, int), np.zeros(n, int)
    prof_buy, prof_sell = np.zeros(n), np.zeros(n)
    frac = (np.arange(BANDS) + 0.5)[:, None]
    for t in range(max(ANCHOR_LEN + 2, LOOK + 2), n):
        if np.isnan(edge[t]) or abs(edge[t] - anchor[t]) <= 2 * tick:
            continue
        dist = (edge[t] - anchor[t]) / BANDS
        min_w = abs(dist) * (1.15 if is_price else 1.8)
        min_wick = abs(dist) * (1.00 if is_price else 1.3)
        ks = slice(t - LOOK + 1, t + 1)
        rev = lambda x: x[ks][::-1]                # index 0 = current bar (k = 0)
        inv_w = 1 / np.maximum(np.maximum(rev(base_w), min_w), tick)
        inv_ww = 1 / np.maximum(np.maximum(rev(base_wick_w), min_wick), tick)
        here = anchor[t] + dist * frac            # 12 x 1
        bf = (rev(buy) * kernel(here, rev(buy_ctr), inv_w) * AGE).sum(1) + \
            WICK_W * (rev(low_rej) * kernel(here, rev(low_ctr), inv_ww) * AGE).sum(1)
        sf = (rev(sell) * kernel(here, rev(sell_ctr), inv_w) * AGE).sum(1) + \
            WICK_W * (rev(high_rej) * kernel(here, rev(high_ctr), inv_ww) * AGE).sum(1)
        tot = bf + sf
        imb = np.where(tot > 0, clamp((bf - sf) / np.where(tot > 0, tot, 1) * 3, -1, 1), 0)
        act = clamp(tot / (vol_base[t] * (0.80 if is_price else 2.0)), 0, 1)
        visible = (act >= 0.08) & (np.abs(imb) >= 0.14) if is_price else (act >= 0.08)
        vis[t] = visible.sum()
        buy_b[t] = (visible & (imb > 0.03)).sum()
        sell_b[t] = (visible & (imb < -0.03)).sum()
        prof_buy[t], prof_sell[t] = bf[visible].sum(), sf[visible].sum()
    prof_tot = prof_buy + prof_sell
    prof_bias = np.where(prof_tot > 0, (prof_buy - prof_sell) / np.where(prof_tot > 0, prof_tot, 1), 0)
    cb, cs = buy + WICK_W * low_rej, sell + WICK_W * high_rej
    curr_bias = np.where(cb + cs > 0, (cb - cs) / np.where(cb + cs > 0, cb + cs, 1), 0)
    has_prof = (vis >= MIN_BANDS) & (prof_tot > 0)
    act_bias = np.where(has_prof, prof_bias, curr_bias)
    buy_press = (act_bias >= SIG_DOM) & np.where(has_prof, buy_b > sell_b, (prof_tot <= 0) | (prof_bias > -SIG_DOM))
    sell_press = (act_bias <= -SIG_DOM) & np.where(has_prof, sell_b > buy_b, (prof_tot <= 0) | (prof_bias < SIG_DOM))
    rising = np.r_[False, anchor[1:] > anchor[:-1]]
    falling = np.r_[False, anchor[1:] < anchor[:-1]]
    bull = buy_press & has_prof & (c > anchor) & rising
    bear = sell_press & has_prof & (c < anchor) & falling
    buys, sells = np.zeros(n, bool), np.zeros(n, bool)
    lb = ls = -10 ** 9
    for t in range(1, n):
        if bull[t] and not bull[t - 1] and t - lb >= SIG_GAP:
            buys[t], lb = True, t
        if bear[t] and not bear[t - 1] and t - ls >= SIG_GAP:
            sells[t], ls = True, t
    return pd.DataFrame({"anchor": anchor, "green": buy_b, "red": sell_b, "buy": buys, "sell": sells,
                         "ema_cross": (c > anchor) & np.r_[True, c[:-1] <= anchor[:-1]] & rising}, index=d.index)
