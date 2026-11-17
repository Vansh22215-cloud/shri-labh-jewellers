"""Line-by-line Python replica of src/core.pine (VANTAGE AI), used to backtest the EXACT indicator logic on 13 years of
NSE data outside TradingView. Pine built-ins are re-implemented with TradingView's documented formulas:
  ta.ema  alpha = 2/(n+1), seeded with the first value        ta.rma  alpha = 1/n, seeded with the SMA of the first n
  ta.rsi  rma of gains / losses                               ta.atr  rma of true range
  ta.dmi  Wilder DI+/DI-/ADX                                  ta.macd ema12 - ema26, signal ema9
  ta.pivothigh/low  the bar R bars back must be strictly above/below the L bars before and R bars after it
Known small differences vs TradingView (documented in AUDIT_REPORT.md): EMA seeding on the first ~200 bars (the
script waits 260 bars), tie handling in pivots, data-vendor price differences."""
import numpy as np
import pandas as pd

P = dict(capital=50000.0, riskPct=1.0, maxAllocPct=25.0, useBreakout=True, usePullback=False, minScore=70,
         strongScore=80, brkLen=50, minRvol=1.5, maxExtAtr=3.0, minRoomR=1.5, minGapBars=5, maxStopPct=15.0,
         exitMode="Fixed risk/reward", atrLen=14, stopMult=3.0, trailMult=4.0, t1R=2.0, t2R=3.0, useMarket=True, swingLen=5,
         wTrend=25.0, wMom=20.0, wStr=20.0, wRS=15.0, wVol=10.0, wMkt=10.0,
         useDip=True, dipStopMult=4.0, dipMaxDays=10, useRCP=True, rcpStopMult=5.0, rcpMaxDays=60,
         dipRsi=2.0, beAtR=None, timeStopBars=None)        # research switches (defaults = the live logic)
SW = "/home/user/shri-labh-jewellers/swing-system"


def ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False).mean().values


def rma(x, n):
    x = np.asarray(x, float)
    out = np.full(len(x), np.nan)
    v = ~np.isnan(x)
    idx = np.flatnonzero(v)
    if len(idx) < n:
        return out
    s = idx[0]
    if not v[s:s + n].all():
        return pd.Series(x).ewm(alpha=1 / n, adjust=False).mean().values
    out[s + n - 1] = x[s:s + n].mean()
    a = 1.0 / n
    for i in range(s + n, len(x)):
        out[i] = a * x[i] + (1 - a) * out[i - 1] if not np.isnan(x[i]) else out[i - 1]
    return out


def sma(x, n):
    return pd.Series(x).rolling(n).mean().values


def shift(x, k=1):
    x = np.asarray(x, float)
    out = np.full(len(x), np.nan)
    if k < len(x):
        out[k:] = x[:-k] if k > 0 else x
    return out


def highest(x, n):
    return pd.Series(x).rolling(n).max().values


def lowest(x, n):
    return pd.Series(x).rolling(n).min().values


def pivot(x, L, R, hi=True):
    x = np.asarray(x, float)
    n = len(x)
    out = np.full(n, np.nan)
    for t in range(L + R, n):
        c = x[t - R]
        left, right = x[t - R - L:t - R], x[t - R + 1:t + 1]
        if hi and c > left.max() and c > right.max():
            out[t] = c
        if not hi and c < left.min() and c < right.min():
            out[t] = c
    return out


def barssince(cond):
    out = np.full(len(cond), np.nan)
    last = None
    for i, c in enumerate(cond):
        if c:
            last = i
        if last is not None:
            out[i] = i - last
    return out


def weekly_prev(d):
    """[close[1], ema20[1], ema20[2]] of the previous COMPLETED week, mapped onto daily bars."""
    wk = d["close"].resample("W-FRI").last().dropna()
    we = pd.Series(ema(wk.values, 20), index=wk.index)
    prev = pd.DataFrame({"wc": wk.shift(1), "we": we.shift(1), "we2": we.shift(2)})
    key = d.index.to_period("W-FRI").to_timestamp("D", "end").normalize()
    prev.index = prev.index.normalize()
    return prev.reindex(key).values


def run(d, bench, allow=None, p=None, state=None):
    """d: daily OHLCV (index = dates); bench: benchmark close Series. -> list of trade dicts (same rules as Pine)."""
    p = dict(P, **(p or {}))
    o, h, l, c, v = (d[k].values.astype(float) for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    allow = np.ones(n, bool) if allow is None else allow
    tr = np.maximum.reduce([h - l, np.abs(h - shift(c)), np.abs(l - shift(c))])
    tr[0] = h[0] - l[0]
    atr = rma(tr, p["atrLen"])
    e20, e50, e200 = ema(c, 20), ema(c, 50), ema(c, 200)
    ch = np.diff(c, prepend=np.nan)
    up, dn = rma(np.where(ch > 0, ch, 0.0), 14), rma(np.where(ch < 0, -ch, 0.0), 14)
    with np.errstate(divide="ignore", invalid="ignore"):
        rsi = np.where(dn == 0, 100.0, np.where(up == 0, 0.0, 100 - 100 / (1 + up / dn)))
    rsi[np.isnan(up) | np.isnan(dn)] = np.nan
    macd = ema(c, 12) - ema(c, 26)
    hist = macd - ema(macd, 9)
    upm, dnm = h - shift(h), shift(l) - l
    pdm = np.where((upm > dnm) & (upm > 0), upm, 0.0)
    mdm = np.where((dnm > upm) & (dnm > 0), dnm, 0.0)
    trur = rma(tr, 14)
    with np.errstate(divide="ignore", invalid="ignore"):
        dip, dim = 100 * rma(pdm, 14) / trur, 100 * rma(mdm, 14) / trur
        ssum = dip + dim
        adx = 100 * rma(np.abs(dip - dim) / np.where(ssum == 0, 1, ssum), 14)
    volAvg = shift(sma(v, 20))
    with np.errstate(divide="ignore", invalid="ignore"):
        rvol = np.where(volAvg > 0, v / volAvg, np.nan)
    hiPrior = shift(highest(h, p["brkLen"]))
    hi252 = shift(highest(h, 252))
    W = weekly_prev(d)
    wC, wE, wE2 = W[:, 0], W[:, 1], W[:, 2]
    weeklyKnown = ~np.isnan(wE) & ~np.isnan(wE2)
    weeklyUp = weeklyKnown & (wC > wE) & (wE > wE2)
    b = bench.reindex(d.index).values.astype(float)
    bE50, bE200 = bench.ewm(span=50, adjust=False).mean().reindex(d.index).values, \
        bench.ewm(span=200, adjust=False).mean().reindex(d.index).values
    benchOk = ~np.isnan(b) & ~np.isnan(bE200) & (b > 0)
    rs = np.where(benchOk, c / np.where(benchOk, b, 1), np.nan)
    rsPerf = rs / shift(rs, 63) - 1
    rsSma = sma(rs, 50)
    rsE = pd.Series(rs).ewm(span=10, adjust=False, ignore_na=True).mean().values.copy()
    rsE[np.isnan(rs)] = np.nan
    rsKnown = ~np.isnan(rsPerf) & ~np.isnan(rsSma) & ~np.isnan(shift(rsE, 10))
    rsOut = rsKnown & (rsPerf > 0) & (rs > rsSma)
    rsImp = rsKnown & (rsE > shift(rsE, 10))
    mktBull = benchOk & (b > bE200) & (bE50 > bE200)
    mktBear = benchOk & (b < bE200) & (bE50 < bE200)
    L = p["swingLen"]
    ph, pl = pivot(h, L, L, True), pivot(l, L, L, False)
    upVol = pd.Series(np.where(c > shift(c), v, 0.0)).rolling(20).sum().values
    dnVol = pd.Series(np.where(c < shift(c), v, 0.0)).rolling(20).sum().values
    sv10, sv50, sv3 = sma(v, 10), sma(v, 50), sma(v, 3)
    low5, close5, rsi5 = lowest(l, 5), lowest(c, 5), lowest(rsi, 5)
    with np.errstate(invalid="ignore"):
        newBreak = (c > hiPrior) & (shift(c) <= shift(hiPrior))

    # ---------------- Type 3 DIP-BUY and Type 4 RCP POSITIONAL: the tested reference implementations (swing-system)
    import sys
    if SW not in sys.path:
        sys.path.insert(0, SW)
    from swing.confirmations import msb_order_block, squeeze_on, swing_low_hold, vix_fix_spike, wavetrend_oversold
    from swing.high_prob import rsi as rsi_n
    from swing.orderflow import order_block_touches
    from swing.rolling_profile import signals as rcp_signals
    atrS = sma(tr, 14)                                      # ATR as a simple average of the true range (as tested)
    sma5, sma200 = sma(c, 5), sma(c, 200)
    if p["useDip"]:
        rsi2 = rsi_n(pd.Series(c), 2).values
        bS200 = bench.rolling(200).mean().reindex(d.index).values
        bR2 = rsi_n(bench, 2).reindex(d.index).values
        fear = vix_fix_spike(h, l, c)
        sqz = squeeze_on(h, l, c)
        dd = pd.DataFrame({"open": o, "high": h, "low": l, "close": c}, index=d.index)
        obt = pd.Series(order_block_touches(dd)[0]).rolling(3, min_periods=1).max().fillna(0).astype(bool).values
        zone = obt | wavetrend_oversold(h, l, c) | msb_order_block(o, h, l, c) | swing_low_hold(o, h, l, c)
        with np.errstate(invalid="ignore"):
            dipBase = (c >= 1.10 * sma200) & (rsi2 < p["dipRsi"]) & benchOk & (b > bS200) & (bR2 < 20)
        dipSig = dipBase & ~sqz & (fear | zone)
        dipTier = np.where(fear & zone, "A", np.where(fear, "B", "C"))
    else:
        dipSig, dipTier = np.zeros(n, bool), np.full(n, "")
    if p["useRCP"]:
        R = rcp_signals(d[["open", "high", "low", "close", "volume"]], "price")
        rcpBuy, rcpSell = R["buy"].values, R["sell"].values
        with np.errstate(invalid="ignore"):
            posSig = rcpBuy & (c >= 0.9 * pd.Series(c).rolling(250).max().values)
    else:
        rcpSell, posSig = np.zeros(n, bool), np.zeros(n, bool)

    # ---------------- sequential part (structure + score + state), in the exact order of core.pine
    swHi = swHiPrev = swLo = swLoPrev = np.nan
    hiTaken = loTaken = False
    structDir = 0
    dzTop = dzBot = np.nan
    brkLevel, brkBar = np.nan, None
    last_failed = last_bull = None
    inPos = pendingEntry = pendingExit = False
    pendingWhy = setupType = ""
    planEntry = entryPx = initStop = stopLvl = tgt1 = tgt2 = hiSince = np.nan
    entryBar = None
    lastExitBar = -100000
    posQty = entryScore = 0
    posType, posTier = "", ""
    t1Done = t2Done = False
    trades, cur, pend_info = [], None, {}
    wsum = sum(p[k] for k in ("wTrend", "wMom", "wStr", "wRS", "wVol", "wMkt"))
    wnorm = 100.0 / wsum if wsum > 0 else 0.0

    def nn(x):
        return not np.isnan(x)

    for t in range(n):
        if nn(ph[t]):
            swHiPrev, swHi, hiTaken = swHi, ph[t], False
        if nn(pl[t]):
            swLoPrev, swLo, loTaken = swLo, pl[t], False
        bullBreak = nn(swHi) and not hiTaken and c[t] > swHi
        bearBreak = nn(swLo) and not loTaken and c[t] < swLo
        bullChoch = bullBreak and structDir == -1
        bearChoch = bearBreak and structDir == 1
        bearBos = bearBreak and structDir != 1
        if bullBreak:
            hiTaken, structDir = True, 1
            for i in range(1, 11):
                if t - i >= 0 and c[t - i] < o[t - i]:
                    dzTop, dzBot = h[t - i], l[t - i]
                    break
        if bearBreak:
            loTaken, structDir = True, -1
        if nn(dzBot) and c[t] < dzBot:
            dzTop = dzBot = np.nan
        higherLow = nn(swLo) and nn(swLoPrev) and swLo > swLoPrev
        failedBreakout = nn(brkLevel) and t - brkBar <= 3 and t > brkBar and c[t] < brkLevel
        if failedBreakout or (brkBar is not None and t - brkBar > 3):
            brkLevel, brkBar = np.nan, None
        if newBreak[t]:
            brkLevel, brkBar = hiPrior[t], t
        if failedBreakout:
            last_failed = t
        if bullBreak:
            last_bull = t
        recentFailed = last_failed is not None and t - last_failed <= 5
        upperWick = h[t] - max(o[t], c[t])
        body = abs(c[t] - o[t])
        nearRes = (nn(swHi) and h[t] >= swHi * 0.995 and c[t] < swHi) or (nn(hi252[t]) and h[t] >= hi252[t] * 0.995 and c[t] < hi252[t])
        rejection = upperWick >= 2 * body and upperWick >= 0.5 * atr[t] and nearRes

        # score
        ptTrend = (5.0 if c[t] > e20[t] else 0) + (5.0 if e20[t] > e50[t] else 0) + (5.0 if e50[t] > e200[t] else 0) + \
            (2.5 if t >= 10 and e50[t] > e50[t - 10] else 0) + (2.5 if t >= 20 and e200[t] > e200[t - 20] else 0) + \
            ((5.0 if weeklyUp[t] else 0.0) if weeklyKnown[t] else 2.5)
        r_ = rsi[t]
        hm1 = hist[t - 1] if t >= 1 else np.nan
        hm2 = hist[t - 2] if t >= 2 else np.nan
        ptMom = (8.0 if 50 <= r_ <= 70 else 4.0 if 70 < r_ <= 78 else 3.0 if 45 <= r_ < 50 else 0.0) + \
            (6.0 if hist[t] > 0 and hist[t] > hm1 else 4.0 if hist[t] > 0 else 2.0 if hist[t] > hm1 and hm1 > hm2 else 0.0) + \
            (6.0 if adx[t] >= 20 and dip[t] > dim[t] else 3.0 if dip[t] > dim[t] else 0.0)
        ptStr = max(0.0, (8.0 if structDir == 1 else 4.0 if structDir == 0 else 0.0) + (6.0 if higherLow else 0) +
                    (6.0 if last_bull is not None and t - last_bull <= 15 else 0) - (6.0 if recentFailed else 0) -
                    (4.0 if rejection else 0))
        ptRS = ((5.0 if rsPerf[t] > 0 else 0) + (5.0 if rs[t] > rsSma[t] else 0) + (5.0 if rsImp[t] else 0)) if rsKnown[t] else 7.5
        acc = upVol[t] / dnVol[t] if dnVol[t] > 0 else 2.0
        riseWeak = t >= 10 and c[t] > c[t - 10] and sv10[t] < 0.8 * sv50[t]
        rv = 0.0 if np.isnan(rvol[t]) else rvol[t]
        upday = t >= 1 and c[t] > c[t - 1]
        ptVol = max(0.0, (5.0 if acc >= 1.2 else 2.5 if acc >= 1.0 else 0) +
                    (5.0 if upday and rv >= 1.5 else 0.0 if upday and rv < 0.7 else 2.5) - (2.5 if riseWeak else 0))
        ptMkt = ((5.0 if b[t] > bE200[t] else 0) + (5.0 if bE50[t] > bE200[t] else 0)) if benchOk[t] else 5.0
        raw = (p["wTrend"] * ptTrend / 25 + p["wMom"] * ptMom / 20 + p["wStr"] * ptStr / 20 + p["wRS"] * ptRS / 15 +
               p["wVol"] * ptVol / 10 + p["wMkt"] * ptMkt / 10) * wnorm
        score = int(np.floor(raw + 0.5))

        # setups
        trendOk = c[t] > e200[t] and e50[t] > e200[t] and c[t] > e50[t]
        rsOkBrk = (not rsKnown[t]) or rsPerf[t] > 0 or rs[t] > rsSma[t]
        rsOkPb = (not rsKnown[t]) or rs[t] > rsSma[t]
        breakoutSetup = p["useBreakout"] and trendOk and bool(newBreak[t]) and rv >= p["minRvol"] and (hist[t] > 0 or r_ > 55) and rsOkBrk
        stackUp = e20[t] > e50[t] and e50[t] > e200[t] and t >= 10 and e50[t] > e50[t - 10]
        touched = low5[t] <= e20[t] * 1.005 or (nn(dzTop) and low5[t] <= dzTop and c[t] > dzBot)
        held = close5[t] >= e50[t] * 0.98
        rsiCool = rsi5[t] <= 55 and rsi5[t] >= 38
        volDry = t >= 1 and sv3[t - 1] < volAvg[t]
        recovery = t >= 1 and c[t] > h[t - 1] and c[t] > o[t] and c[t] > e20[t]
        pullbackSetup = p["usePullback"] and stackUp and touched and held and rsiCool and volDry and recovery and rsOkPb

        planStop = c[t] - p["stopMult"] * atr[t]
        riskPS = c[t] - planStop
        stopOk = riskPS > 0 and riskPS / c[t] * 100 <= p["maxStopPct"]
        overhead = np.nan
        if nn(hi252[t]) and c[t] < hi252[t]:
            overhead = hi252[t]
        if nn(swHi) and swHi > c[t]:
            overhead = swHi if np.isnan(overhead) else min(overhead, swHi)
        roomOk = np.isnan(overhead) or overhead - c[t] >= p["minRoomR"] * riskPS
        notExtended = c[t] - e20[t] <= p["maxExtAtr"] * atr[t] and r_ <= 80
        mktOk = (not p["useMarket"]) or not mktBear[t]
        riskAmt = p["capital"] * p["riskPct"] / 100
        qtyRisk = int(np.floor(riskAmt / riskPS)) if riskPS > 0 else 0
        qtyCap = int(np.floor(p["capital"] * p["maxAllocPct"] / 100 / c[t])) if c[t] > 0 else 0
        qtyCalc = min(qtyRisk, qtyCap)
        warm = t >= 260 and nn(e200[t]) and nn(atr[t])
        if not warm:
            continue

        # state machine (confirmed bars)
        ev_buy = ev_sell = None
        exitFill, exitPx, exit_why = False, np.nan, ""
        if inPos and pendingExit:
            inPos, pendingExit, exitFill, exitPx, lastExitBar = False, False, True, o[t], t
            exit_why = pendingWhy
        if pendingEntry:
            pendingEntry, inPos, entryPx, entryBar, hiSince = False, True, o[t], t, h[t]
            t1Done = t2Done = False
            cur = dict(pend_info, entry_date=d.index[t], entry=o[t], init_stop=initStop, plan_entry=planEntry, qty=posQty,
                       setup=setupType, score=entryScore, t1=tgt1, t2=tgt2)
        if inPos:
            if l[t] <= stopLvl:
                exit_why = "Trailing stop" if stopLvl > initStop else "Stop-loss"
                inPos, exitFill, exitPx, lastExitBar = False, True, min(o[t], stopLvl), t
            elif posType in ("Breakout", "Pullback") and p["exitMode"] == "Fixed risk/reward" and h[t] >= tgt2:
                inPos, exitFill, exitPx, lastExitBar, exit_why = False, True, max(o[t], tgt2), t, "Target 2"
        if exitFill and cur is not None and exit_why in ("Stop-loss", "Trailing stop", "Target 2"):
            ev_sell = {"why": exit_why, "price": float(exitPx), "signal": cur.get("signal"), "intrabar": True}
        if exitFill and cur is not None:
            cur.update(exit_date=d.index[t], exit=exitPx, why=exit_why, days=t - entryBar, t1_hit=t1Done)
            trades.append(cur)
            cur = None
        if inPos:
            if not t1Done and h[t] >= tgt1:
                t1Done = True
            if not t2Done and h[t] >= tgt2:
                t2Done = True
            hiSince = max(hiSince, h[t])
            if posType in ("Breakout", "Pullback") and p["exitMode"] != "Fixed risk/reward":
                stopLvl = max(stopLvl, hiSince - p["trailMult"] * atr[t])
            if p["beAtR"] and posType in ("Breakout", "Pullback", "RCP") and h[t] >= planEntry + p["beAtR"] * (planEntry - initStop):
                stopLvl = max(stopLvl, entryPx)                       # E1: break-even once +1R was reached
            if (p["timeStopBars"] and posType in ("Breakout", "Pullback", "RCP") and not pendingExit
                    and t - entryBar >= p["timeStopBars"] and c[t] < entryPx):
                pendingExit, pendingWhy = True, f"Time stop ({p['timeStopBars']} bars, no progress)"
                ev_sell = {"why": pendingWhy, "price": float(c[t]), "signal": (cur or {}).get("signal"), "intrabar": False}
            if pendingExit:
                pass
            elif posType == "Dip-buy":
                why = ("Closed above the 5-day average (dip-buy exit)" if c[t] > sma5[t] else
                       f"Time exit ({p['dipMaxDays']} days)" if t - entryBar >= p["dipMaxDays"] - 1 else "")
                if why:
                    pendingExit, pendingWhy = True, why
                    ev_sell = {"why": why, "price": float(c[t]), "signal": (cur or {}).get("signal"), "intrabar": False}
            elif posType == "RCP":
                why = ("Rolling Candle Profile SELL" if rcpSell[t] else
                       f"Time exit ({p['rcpMaxDays']} days)" if t - entryBar >= p["rcpMaxDays"] - 1 else "")
                if why:
                    pendingExit, pendingWhy = True, why
                    ev_sell = {"why": why, "price": float(c[t]), "signal": (cur or {}).get("signal"), "intrabar": False}
            elif p["exitMode"] == "Combined":
                why = ""
                if c[t] < e50[t] and hist[t] < 0:
                    why = "Trend deterioration (below EMA50, MACD negative)"
                elif bearChoch:
                    why = "Bearish structure change (CHoCH)"
                elif bearBos and c[t] < e20[t]:
                    why = "Support breakdown (bearish BOS)"
                elif failedBreakout and t - entryBar <= 5:
                    why = "Failed breakout"
                if why:
                    pendingExit, pendingWhy = True, why
                    ev_sell = {"why": why, "price": float(c[t]), "signal": (cur or {}).get("signal"), "intrabar": False}
        gapOk = t - lastExitBar >= p["minGapBars"]
        if not inPos and not pendingEntry and gapOk and allow[t]:
            # priority: the setup with the best tested record first
            pick, ps = None, np.nan
            if dipSig[t] and atrS[t] > 0:
                pick, ps = "Dip-buy", c[t] - p["dipStopMult"] * atrS[t]
            elif posSig[t] and atrS[t] > 0:
                pick, ps = "RCP", c[t] - p["rcpStopMult"] * atrS[t]
            elif ((breakoutSetup or pullbackSetup) and notExtended and stopOk and roomOk and mktOk and not rejection
                  and score >= p["minScore"]):
                pick, ps = ("Breakout" if breakoutSetup else "Pullback"), planStop
            if pick is not None:
                rps = c[t] - ps
                q = min(int(np.floor(riskAmt / rps)) if rps > 0 else 0, qtyCap)
                if q >= 1:
                    pendingEntry = True
                    setupType = posType = pick
                    posTier = dipTier[t] if pick == "Dip-buy" else ""
                    planEntry, initStop, stopLvl = c[t], ps, ps
                    if pick in ("Breakout", "Pullback"):
                        tgt1, tgt2 = c[t] + p["t1R"] * rps, c[t] + p["t2R"] * rps
                    else:
                        tgt1 = tgt2 = np.nan
                    posQty, entryScore = q, score
                    regime = "BULLISH" if mktBull[t] else "BEARISH" if mktBear[t] else "SIDEWAYS"
                    pend_info = {"signal": d.index[t], "regime": regime, "tier": posTier}
                    ev_buy = {"setup": pick, "tier": posTier, "score": int(score), "close": float(c[t]),
                              "stop": float(ps), "t1": float(tgt1), "t2": float(tgt2), "signal": d.index[t]}
        if state is not None and t == n - 1:
            state.update(last_date=d.index[t], buy=ev_buy, sell=ev_sell, in_position=bool(inPos or pendingEntry))
    return trades
