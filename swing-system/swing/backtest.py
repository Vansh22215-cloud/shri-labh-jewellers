"""Event-driven daily portfolio backtest with realistic Zerodha costs.

Rules simulated (identical to what the live report tells you to do):
  * Signals are computed at the close of day t; orders execute at the OPEN of day t+1.
  * Do-not-buy rule: skip the trade if day t+1 opens above (signal close + 0.5 x ATR)
    or at/below the stop.
  * Stop-loss: if a day OPENS below the stop, we exit at that (worse) open price
    (gap-through-stop). Otherwise if the day's low touches the stop we exit at the stop.
    If the stop and a target are both inside the same day's range we assume the
    STOP happened first (conservative).
  * Target 1 (+1.5R): sell half, move stop to entry (breakeven). Target 2 (+3R): sell rest.
  * Time stop: after 25 trading days, sell at the next open.
  * Max 4 open positions; risk 1% of equity per trade; max 25% of equity per position.
  * If equity falls 10% below its peak, no new trades for 20 trading days.
  * No new trades when the market regime filter is off (weak market).
  * Idle cash earns the liquid-fund return (applied daily).
  * Every buy/sell pays Zerodha delivery charges + 0.15% slippage.
"""
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import costs
from .strategy import position_size


@dataclass
class Position:
    symbol: str
    setup: str
    signal_date: pd.Timestamp
    entry_date: pd.Timestamp
    entry: float          # fill price incl. slippage
    qty: int
    stop: float
    t1: float
    t2: float
    r: float              # initial risk per share
    cost_paid: float
    days: int = 0
    atr_e: float = 0.0
    hc: float = 0.0
    exit_next: bool = False
    t1_done: bool = False
    realised: float = 0.0  # net rupees from partial exits
    exits: list = field(default_factory=list)


def run(P, sig, params, start, end, capital=45000.0, liquid_nav=None, max_candidates=8, qty_override=None):
    """Simulate the strategy between start and end. Returns (equity Series, trades DataFrame, daily exposure)."""
    p = params
    style = p.get("exit_style", "targets")   # targets | trail | signal
    dates = P["close"].loc[start:end].index
    o, h, l, c = (P[k] for k in ("open", "high", "low", "close"))
    score, elig, setup, atrv, regime = sig["score"], sig["eligible"], sig["setup"], sig["atr"], sig["regime_ok"]

    if liquid_nav is not None:
        lf = liquid_nav.reindex(liquid_nav.index.union(dates)).ffill().reindex(dates)
        lf_ret = lf.pct_change().fillna(0).clip(-0.01, 0.01)
    else:
        lf_ret = pd.Series(0.0, index=dates)
    sma5 = c.rolling(5, min_periods=5).mean() if style == "signal" else None

    cash, peak = capital, capital
    pause_until = -1
    positions, trades, eq, expo = [], [], [], []
    pending = []  # candidates from previous close

    for i, d in enumerate(dates):
        # 1) idle cash earns liquid fund return (credited for the day)
        cash *= (1 + lf_ret.iloc[i])
        equity_prev = eq[-1] if eq else capital

        # 2) entries at today's open from yesterday's ranked candidates
        if pending and i > pause_until:
            held = {ps.symbol for ps in positions}
            for cand in pending:
                if len(positions) >= p["max_open_positions"]:
                    break
                s = cand["symbol"]
                if s in held:
                    continue
                op = o.at[d, s]
                if not np.isfinite(op) or op <= 0:
                    continue
                if op > cand["close"] + p["do_not_buy_gap_atr"] * cand["atr"] or op <= cand["stop"]:
                    continue  # do-not-buy rule
                fill = costs.fill_price(op, "buy")
                qty = cand.get("qty") or position_size(equity_prev, cash, fill, cand["stop"], p)
                if qty < 1:
                    continue
                value = qty * fill
                fee = costs.buy_cost(value)
                if value + fee > cash:
                    continue
                cash -= value + fee
                r = fill - cand["stop"]
                positions.append(Position(s, cand["setup"], cand["date"], d, fill, qty, cand["stop"],
                                          fill + p["target1_r"] * r, fill + p["target2_r"] * r, r, fee,
                                          atr_e=cand["atr"], hc=fill))
                held.add(s)

        # 3) manage open positions with today's bar
        still = []
        for ps in positions:
            od, hd, ld, cd = o.at[d, ps.symbol], h.at[d, ps.symbol], l.at[d, ps.symbol], c.at[d, ps.symbol]
            if not np.isfinite(cd):
                still.append(ps)  # no trade today (suspension/holiday for this stock)
                continue
            new_today = ps.entry_date == d
            if not new_today:
                ps.days += 1
            closed = False

            def sell(q, px, why):
                nonlocal cash
                fill = costs.fill_price(px, "sell")
                value = q * fill
                fee = costs.sell_cost(value)
                cash += value - fee
                ps.realised += value - fee
                ps.exits.append((d, q, fill, why))
                ps.qty -= q

            # time stop: sell at the open after max_hold_days; exit signal from last close
            if not new_today and ps.days > p["max_hold_days"]:
                sell(ps.qty, od, "time")
                closed = True
            elif not new_today and ps.exit_next:
                sell(ps.qty, od, "signal")
                closed = True
            # gap through stop
            elif not new_today and od <= ps.stop:
                sell(ps.qty, od, "stop_gap")
                closed = True
            elif ld <= ps.stop:
                sell(ps.qty, ps.stop, "stop")
                closed = True
            elif style in ("targets", "targets_trail"):
                if not ps.t1_done and hd >= ps.t1:
                    px = od if (not new_today and od >= ps.t1) else ps.t1
                    half = ps.qty // 2
                    if half >= 1:
                        sell(half, px, "target1")
                    ps.t1_done = True
                    ps.stop = max(ps.stop, ps.entry)  # breakeven from now on
                if ps.qty > 0 and style == "targets" and hd >= ps.t2:
                    px = od if (not new_today and od >= ps.t2) else ps.t2
                    sell(ps.qty, px, "target2")
                    closed = True
            if closed or ps.qty == 0:
                gross_in = ps.entry * sum(q for _, q, _, _ in ps.exits)
                pnl = ps.realised - gross_in - ps.cost_paid
                trades.append({
                    "symbol": ps.symbol, "setup": ps.setup, "signal_date": ps.signal_date,
                    "entry_date": ps.entry_date, "entry": round(ps.entry, 2),
                    "qty": sum(q for _, q, _, _ in ps.exits), "exit_date": d,
                    "exit_reason": ps.exits[-1][3], "days": ps.days,
                    "pnl": round(pnl, 2), "r_multiple": round(pnl / (ps.r * sum(q for _, q, _, _ in ps.exits)), 3),
                    "init_r": round(ps.r, 2),
                })
            else:
                if style == "trail" or (style == "targets_trail" and ps.t1_done):   # chandelier stop: highest close minus k x ATR (only moves up)
                    ps.hc = max(ps.hc, cd)
                    ps.stop = max(ps.stop, ps.hc - p.get("trail_atr_mult", 3.0) * ps.atr_e)
                elif style == "signal" and sma5 is not None and cd > sma5.at[d, ps.symbol]:
                    ps.exit_next = True    # bounced above 5-day average: sell at next open
                still.append(ps)
        positions = still

        # 4) mark to market
        mv = 0.0
        for ps in positions:
            px = c.at[d, ps.symbol]
            if not np.isfinite(px):
                px = c[ps.symbol].loc[:d].dropna().iloc[-1]
            mv += ps.qty * px
        equity = cash + mv
        eq.append(equity)
        expo.append(mv / equity if equity > 0 else 0)
        peak = max(peak, equity)
        if i > pause_until and equity <= peak * (1 - p["drawdown_pause_pct"] / 100):
            pause_until = i + p["drawdown_pause_days"]
        if i == pause_until:
            peak = equity  # restart the drawdown clock after the pause

        # 5) tonight's candidates for tomorrow
        pending = []
        if bool(regime.get(d, False)) and i >= pause_until:
            row = elig.loc[d]
            names = row[row].index
            if len(names):
                sc = score.loc[d, names].sort_values(ascending=False).head(max_candidates)
                for s in sc.index:
                    cl, av = c.at[d, s], atrv.at[d, s]
                    pending.append({"symbol": s, "date": d, "close": cl, "atr": av, "setup": setup.at[d, s],
                                    "stop": cl - p["stop_atr_mult"] * av, "qty": qty_override})

    equity = pd.Series(eq, index=dates, name="equity")
    return equity, pd.DataFrame(trades), pd.Series(expo, index=dates, name="exposure")


def buy_and_hold(price, start, end, capital=45000.0):
    """Benchmark: put all capital into one instrument at the first open, pay costs once."""
    px = price.loc[start:end].dropna()
    if px.empty:
        return pd.Series(dtype=float)
    first = costs.fill_price(px.iloc[0], "buy")
    qty = np.floor(capital / (first * 1.003))
    leftover = capital - qty * first - costs.buy_cost(qty * first)
    return qty * px + leftover


def exposure_matched(index_price, exposure, liquid_nav, capital=45000.0):
    """Benchmark: hold the index with the SAME daily exposure as the strategy; idle cash in liquid fund.
    (Costs ignored for this benchmark, which slightly flatters it.)"""
    r_idx = index_price.reindex(exposure.index).ffill().pct_change().fillna(0)
    lf = liquid_nav.reindex(liquid_nav.index.union(exposure.index)).ffill().reindex(exposure.index)
    r_lf = lf.pct_change().fillna(0)
    w = exposure.shift(1).fillna(0)
    return capital * (1 + w * r_idx + (1 - w) * r_lf).cumprod()


def stats(equity, trades=None):
    if equity is None or len(equity) < 2:
        return {}
    ret = equity.iloc[-1] / equity.iloc[0] - 1
    yrs = max((equity.index[-1] - equity.index[0]).days / 365.25, 1e-9)
    cagr = (1 + ret) ** (1 / yrs) - 1 if ret > -1 else -1
    dd = (equity / equity.cummax() - 1).min()
    d = equity.pct_change().dropna()
    sharpe = d.mean() / d.std() * np.sqrt(252) if d.std() > 0 else 0
    out = {"total_return_pct": round(ret * 100, 2), "cagr_pct": round(cagr * 100, 2),
           "max_drawdown_pct": round(dd * 100, 2), "sharpe": round(float(sharpe), 2)}
    if trades is not None and len(trades):
        out.update({"trades": int(len(trades)), "win_rate_pct": round((trades["pnl"] > 0).mean() * 100, 1),
                    "avg_r": round(trades["r_multiple"].mean(), 3),
                    "avg_days": round(trades["days"].mean(), 1),
                    "profit_factor": round(trades.loc[trades.pnl > 0, "pnl"].sum()
                                           / max(1e-9, -trades.loc[trades.pnl <= 0, "pnl"].sum()), 2)})
    elif trades is not None:
        out["trades"] = 0
    return out
