"""Abnormal-market detector and daily loss limit (ROADMAP T2). Fixed rules (DECISIONS D67):
  * India VIX jumps more than 20% in a day, or is above 28            -> abnormal (panic)
  * Nifty moved more than 2.5% (either way) on the day                -> abnormal (shock day)
  * Today's realised losses on tracked tips reach 2% of capital        -> daily loss limit
Any of these -> no NEW trades for the next session (existing trades keep their stops).
"""
import pandas as pd

from . import data_prices


def check(capital, tips_df=None, today=None):
    reasons = []
    v = data_prices.load("INDIAVIX")
    if v is not None and len(v) > 2:
        c = v["close"].dropna()
        jump = (c.iloc[-1] / c.iloc[-2] - 1) * 100
        if jump > 20 or c.iloc[-1] > 28:
            reasons.append(f"Abnormal market: India VIX {c.iloc[-1]:.1f} ({jump:+.0f}% today) - panic conditions")
    n = data_prices.load("NIFTY50")
    if n is not None and len(n) > 2:
        mv = (n["close"].iloc[-1] / n["close"].iloc[-2] - 1) * 100
        if abs(mv) > 2.5:
            reasons.append(f"Abnormal market: Nifty moved {mv:+.1f}% today - shock day")
    if tips_df is not None and len(tips_df):
        today = str(pd.Timestamp(today or pd.Timestamp.today()).date())
        t = tips_df[(tips_df["status"] == "closed") & (tips_df["exit_date"].astype(str) == today)]
        loss = float(t["pnl"].astype(float).clip(upper=0).sum()) if len(t) else 0.0
        if loss <= -0.02 * capital:
            reasons.append(f"Daily loss limit: Rs {-loss:,.0f} lost today (limit 2% = Rs {0.02 * capital:,.0f})")
    return reasons
