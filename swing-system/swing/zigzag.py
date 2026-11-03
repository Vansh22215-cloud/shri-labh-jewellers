"""ATR zigzag swing engine + the swing-geometry patterns of the owner's library (harmonic, Elliott, pitchforks,
diamond, megaphone, Fibonacci cluster / time zone, three drives).

No look-ahead: a swing point is CONFIRMED only when the close has moved k x ATR away from it. Events are stamped
on that confirming bar (first_knowable_at), never on the swing bar itself. Every pattern below is evaluated on
those events only, using the last 7 confirmed swing points (alternating highs and lows).
Definitions follow the catalogue's conventional Fibonacci ratios with explicit tolerances (rule version cat-v3).
Bullish (long-side) variants only - the system buys delivery stocks.
"""
import numpy as np
import pandas as pd

K = 2.0           # swing size in ATRs
NBUF = 7


def events(B, k=K):
    """Run the zigzag once per panel. Returns dict with arrays: t, j (bar and stock of each confirmation),
    V/I/Ty (E x 7: value, bar index, +1 high / -1 low of the last 7 confirmed swings, newest last)."""
    key = f"_zz_{k}"
    if key in B:
        return B[key]
    h, l, c, A = (B[x].to_numpy(dtype=float) for x in ("h", "l", "c", "atr"))
    T, N = c.shape
    d = np.zeros(N)
    hi, hi_i = np.full(N, np.nan), np.zeros(N)
    lo, lo_i = np.full(N, np.nan), np.zeros(N)
    V, I, Ty = np.full((N, NBUF), np.nan), np.full((N, NBUF), np.nan), np.zeros((N, NBUF))
    out_t, out_j, out_V, out_I, out_T = [], [], [], [], []
    for t in range(T):
        ht, lt, ct, at = h[t], l[t], c[t], A[t]
        ok = ~np.isnan(ct) & ~np.isnan(at) & ~np.isnan(ht) & ~np.isnan(lt)
        new = ok & np.isnan(hi)
        hi[new], lo[new], hi_i[new], lo_i[new] = ht[new], lt[new], t, t
        up, dn = ok & (d >= 0), ok & (d <= 0)
        # track extremes of the current leg (and the opposite extreme since that extreme)
        m = up & (ht > hi)
        hi[m], hi_i[m] = ht[m], t
        m2 = m & (d > 0)
        lo[m2], lo_i[m2] = lt[m2], t
        m = up & ~m & (lt < lo) & (d > 0)
        lo[m], lo_i[m] = lt[m], t
        m = dn & (lt < lo)
        lo[m], lo_i[m] = lt[m], t
        m2 = m & (d < 0)
        hi[m2], hi_i[m2] = ht[m2], t
        m = dn & ~m & (ht > hi) & (d < 0)
        hi[m], hi_i[m] = ht[m], t
        flip_dn = ok & (d >= 0) & (ct < hi - k * at)       # swing high confirmed
        flip_up = ok & (d <= 0) & (ct > lo + k * at)       # swing low confirmed
        both = flip_dn & flip_up
        flip_up &= ~both
        for mask, val, idx, typ in ((flip_dn, hi, hi_i, 1.0), (flip_up, lo, lo_i, -1.0)):
            if not mask.any():
                continue
            V[mask] = np.roll(V[mask], -1, axis=1); I[mask] = np.roll(I[mask], -1, axis=1)
            Ty[mask] = np.roll(Ty[mask], -1, axis=1)
            V[mask, -1], I[mask, -1], Ty[mask, -1] = val[mask], idx[mask], typ
            js = np.where(mask)[0]
            out_t.append(np.full(len(js), t)); out_j.append(js)
            out_V.append(V[js].copy()); out_I.append(I[js].copy()); out_T.append(Ty[js].copy())
        # start the new leg from this bar
        for mask in (flip_up, flip_dn):
            hi[mask], hi_i[mask], lo[mask], lo_i[mask] = ht[mask], t, lt[mask], t
        d[flip_up] = 1
        d[flip_dn] = -1
    if out_t:
        E = {"t": np.concatenate(out_t), "j": np.concatenate(out_j), "V": np.concatenate(out_V),
             "I": np.concatenate(out_I), "Ty": np.concatenate(out_T)}
    else:
        E = {"t": np.zeros(0, int), "j": np.zeros(0, int), "V": np.zeros((0, NBUF)), "I": np.zeros((0, NBUF)),
             "Ty": np.zeros((0, NBUF))}
    E["T"], E["N"] = T, N
    B[key] = E
    return E


def _mask(B, E, sel):
    out = np.zeros((E["T"], E["N"]), bool)
    out[E["t"][sel], E["j"][sel]] = True
    c = B["c"]
    return pd.DataFrame(out, index=c.index, columns=c.columns)


def held(B, E, sel, values, max_age):
    """Value set at each selected event, carried forward up to max_age bars; any later swing event of the same
    stock ends it (the structure has changed)."""
    arr = np.full((E["T"], E["N"]), np.nan)
    arr[E["t"], E["j"]] = -np.inf                     # every event resets
    arr[E["t"][sel], E["j"][sel]] = values[sel]
    df = pd.DataFrame(arr, index=B["c"].index, columns=B["c"].columns).ffill(limit=max_age)
    return df.replace(-np.inf, np.nan)


def _between(x, lo, hi):
    with np.errstate(invalid="ignore"):
        return (x >= lo) & (x <= hi)


def _near(x, target, tol=0.05):
    return _between(x, target - tol, target + tol)


def _xabcd(E):
    V = E["V"]
    newest_low = E["Ty"][:, -1] == -1
    X, A, Bp, C, D = (V[:, i] for i in (-5, -4, -3, -2, -1))
    with np.errstate(invalid="ignore", divide="ignore"):
        XA = A - X
        ab = (A - Bp) / XA            # B retracement of XA
        bc = (C - Bp) / (A - Bp)      # C retracement of AB
        xd = (A - D) / XA             # D retracement of XA
        xc = C - X
        cd_xc = (C - D) / xc          # D retracement of XC (cypher, shark)
        cd_ab = (C - D) / (A - Bp)
    ok = newest_low & (XA > 0) & ~np.isnan(X)
    return ok, X, A, Bp, C, D, ab, bc, xd, cd_xc, cd_ab


HARMONIC = {
    "harmonic_gartley": lambda ab, bc, xd, cx, cdab, X, A, Bp, C, D: _near(ab, .618) & _between(bc, .382, .886) & _near(xd, .786),
    "harmonic_bat": lambda ab, bc, xd, cx, cdab, X, A, Bp, C, D: _between(ab, .382, .5) & _between(bc, .382, .886) & _near(xd, .886),
    "alternate_bat_bullish": lambda ab, bc, xd, cx, cdab, X, A, Bp, C, D: _between(ab, .30, .382) & _between(bc, .382, .886) & _near(xd, 1.13),
    "harmonic_butterfly": lambda ab, bc, xd, cx, cdab, X, A, Bp, C, D: _near(ab, .786) & _between(bc, .382, .886) & _between(xd, 1.27, 1.618),
    "harmonic_crab": lambda ab, bc, xd, cx, cdab, X, A, Bp, C, D: _between(ab, .382, .618) & _between(bc, .382, .886) & _near(xd, 1.618, .08),
    "harmonic_deep_crab": lambda ab, bc, xd, cx, cdab, X, A, Bp, C, D: _near(ab, .886) & _between(bc, .382, .886) & _near(xd, 1.618, .08),
    "harmonic_cypher": lambda ab, bc, xd, cx, cdab, X, A, Bp, C, D: _between(ab, .382, .618) & _between((C - X) / (A - X), 1.272, 1.414) & _near(cx, .786),
    "harmonic_shark": lambda ab, bc, xd, cx, cdab, X, A, Bp, C, D: _between(ab, .382, .886) & _between(bc, 1.13, 1.618) & _between(cx, .886, 1.13),
    "5_0_bullish": lambda ab, bc, xd, cx, cdab, X, A, Bp, C, D: _between(ab, 1.13, 1.618) & _between(bc, 1.618, 2.24) & _near((C - D) / (C - Bp), .5),
    "harmonic_ab_cd": lambda ab, bc, xd, cx, cdab, X, A, Bp, C, D: _between(bc, .618, .786) & _between(cdab, .9, 1.1) & (D < Bp),
}
# catalogue names that are the same rule
HARMONIC_ALIASES = {"chart_pattern/cypher_bullish": "cp_harmonic_cypher", "chart_pattern/deep_crab_bullish": "cp_harmonic_deep_crab",
                    "chart_pattern/shark_bullish": "cp_harmonic_shark", "chart_pattern/abcd_bullish": "cp_harmonic_ab_cd",
                    "chart_pattern/elliott_impulse_wave": "cp_elliott_impulse", "chart_pattern/gap_exhaustion": "cp_exhaustion_gap"}


def _cross_above(c, level):
    return (c > level) & (c.shift(1) <= level.shift(1))


def signal(pid, B, p=None):
    E = events(B)
    c, l, o = B["c"], B["l"], B["o"]
    A = B["atr"]
    V, I, Ty = E["V"], E["I"], E["Ty"]
    newest_low, newest_high = Ty[:, -1] == -1, Ty[:, -1] == 1
    T = E["T"]
    tpos = pd.DataFrame(np.repeat(np.arange(T)[:, None], E["N"], 1).astype(float), index=c.index, columns=c.columns)
    with np.errstate(invalid="ignore", divide="ignore"):
        if pid in HARMONIC:
            ok, X, Ap, Bp, C, D, ab, bc, xd, cx, cdab = _xabcd(E)
            sel = ok & HARMONIC[pid](ab, bc, xd, cx, cdab, X, Ap, Bp, C, D)
            e = _mask(B, E, sel)                                       # buy as point D is confirmed
        elif pid == "three_drives_bullish":
            D1, h1, D2, h2, D3 = (V[:, i] for i in (-5, -4, -3, -2, -1))
            sel = newest_low & (D1 > D2) & (D2 > D3) & _between((h1 - D2) / (h1 - D1), 1.27, 1.618) \
                & _between((h2 - D3) / (h2 - D2), 1.27, 1.618)
            e = _mask(B, E, sel)
        elif pid == "elliott_impulse":                                 # enter wave 3: break of wave-1 top after wave 2
            L0, H1, L2 = V[:, -3], V[:, -2], V[:, -1]
            sel = newest_low & (L2 > L0) & _between((H1 - L2) / (H1 - L0), .382, .786) & \
                ((H1 - L0) >= 2 * A.to_numpy()[E["t"], E["j"]])
            e = _cross_above(c, held(B, E, sel, H1, 20))
        elif pid in ("elliott_abc_correction", "elliott_zigzag", "elliott_flat_correction"):
            H0, La, Hb, Lc = V[:, -4], V[:, -3], V[:, -2], V[:, -1]
            a_len = H0 - La
            b_ret = (Hb - La) / a_len
            c_len = (Hb - Lc) / a_len
            if pid == "elliott_abc_correction":
                sel = newest_low & (Lc < La) & _between(b_ret, .382, .786) & _between(c_len, .618, 1.618)
            elif pid == "elliott_zigzag":
                sel = newest_low & (Lc < La) & _between(b_ret, .382, .618) & _near(c_len, 1.0, .2)
            else:
                sel = newest_low & (b_ret >= .9) & _between(c_len, .9, 1.3)
            e = _mask(B, E, sel) & B["above200"] & (B["sma200"] > B["sma200"].shift(20))
        elif pid in ("elliott_triangle", "elliott_diagonal", "diamond_bottom", "megaphone_formation"):
            P0, P1, P2, P3, P4, P5 = (V[:, i] for i in (-6, -5, -4, -3, -2, -1))
            if pid == "elliott_triangle":       # contracting a-b-c-d-e in an uptrend, buy the break of d
                sel = newest_low & (P0 > P2) & (P2 > P4) & (P1 < P3) & (P3 < P5)
                e = _cross_above(c, held(B, E, sel, P4, 15)) & B["above200"]
            elif pid == "elliott_diagonal":     # ending diagonal after a decline: overlapping, contracting waves
                sel = newest_low & (P1 > P3) & (P3 > P5) & (P0 > P2) & (P2 > P4) & (P4 > P1) & \
                    ((P0 - P1) > (P2 - P3)) & ((P2 - P3) > (P4 - P5))
                e = _cross_above(c, held(B, E, sel, P4, 15))
            elif pid == "diamond_bottom":       # broadening then contracting swings after a decline
                sel = newest_low & (P2 > P0) & (P3 < P1) & (P4 < P2) & (P5 > P3)
                dec = (c.shift(60) > 1.15 * c).astype(bool)
                e = _cross_above(c, held(B, E, sel, P4, 20)) & dec.shift(20).fillna(False).astype(bool)
            else:                               # megaphone: higher highs and lower lows, buy the upside break
                sel = newest_low & (P0 < P2) & (P2 < P4) & (P1 > P3) & (P3 > P5)
                e = _cross_above(c, held(B, E, sel, P4, 20))
        elif pid in ("andrews_pitchfork", "schiff_pitchfork", "modified_schiff_pitchfork"):
            L0, H1, L2 = V[:, -3], V[:, -2], V[:, -1]
            i0, i1, i2 = I[:, -3], I[:, -2], I[:, -1]
            if pid == "andrews_pitchfork":
                ax, ay = i0, L0
            elif pid == "schiff_pitchfork":
                ax, ay = i0, (L0 + H1) / 2
            else:
                ax, ay = (i0 + i1) / 2, (L0 + H1) / 2
            mx, my = (i1 + i2) / 2, (H1 + L2) / 2
            slope = (my - ay) / np.maximum(mx - ax, 1)
            sel = newest_low & (L2 > L0) & (slope > 0)
            base, bi, sl = held(B, E, sel, L2, 60), held(B, E, sel, i2.astype(float), 60), held(B, E, sel, slope, 60)
            line = base + sl * (tpos - bi)                     # lower parallel through point 2
            e = (l <= line + 0.25 * A) & (c > line) & (c > o) & (tpos - bi > 3)
        elif pid == "fibonacci_cluster":
            Hn = V[:, -1]
            lows = np.stack([V[:, -2], V[:, -4], V[:, -6]], 1)
            levels = np.concatenate([Hn[:, None] - r * (Hn[:, None] - lows) for r in (.382, .5, .618)], 1)   # E x 9
            grp = np.tile(np.arange(3), 3)
            a_ev = A.to_numpy()[E["t"], E["j"]]
            best, bestd = np.full(len(Hn), np.nan), np.full(len(Hn), np.inf)
            for x in range(9):
                for y in range(x + 1, 9):
                    if grp[x] == grp[y]:
                        continue
                    dd = np.abs(levels[:, x] - levels[:, y])
                    m = dd < bestd
                    bestd[m], best[m] = dd[m], (levels[m, x] + levels[m, y]) / 2
            sel = newest_high & (Hn >= np.nanmax(V[:, -6:], 1)) & (bestd <= 0.25 * a_ev)
            cl = held(B, E, sel, best, 40)
            e = (l <= cl + 0.2 * A) & (c > cl) & (c > o) & B["above200"]
        elif pid == "fibonacci_time_zone":
            n = I[:, -1] - I[:, -3]
            fib = np.array([13, 21, 34, 55, 89])
            sel = newest_low & (np.min(np.abs(n[:, None] - fib[None, :]), 1) <= 1)
            e = _mask(B, E, sel) & B["above200"]
        else:
            raise ValueError(f"no zigzag detector for {pid}")
    return (e.fillna(False).astype(bool) & B["member"]).fillna(False)


DETECTORS = list(HARMONIC) + ["three_drives_bullish", "elliott_impulse", "elliott_abc_correction", "elliott_zigzag",
                              "elliott_flat_correction", "elliott_triangle", "elliott_diagonal", "diamond_bottom",
                              "megaphone_formation", "andrews_pitchfork", "schiff_pitchfork",
                              "modified_schiff_pitchfork", "fibonacci_cluster", "fibonacci_time_zone"]
