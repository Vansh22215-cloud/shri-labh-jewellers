"""Risk score from 1 (lowest) to 10 (highest) for a trade idea. Fixed rules (DECISIONS.md D57):
  +3 strategy not validated (aggressive mode)          (+1 if validated)
  +0..3 volatility: daily range (ATR) <2% 0, 2-3.5% 1, 3.5-5% 2, >5% 3
  +0..2 liquidity: median daily value > Rs 100 cr 0, 20-100 cr 1, < 20 cr 2
  +1 below a rising 200-day average (against the long-term trend)
  +1 weak overall market (Nifty below 200-day average or poor breadth)
  +2 results due within 7 days
  +1 more than 15% above the 50-day average (stretched)
Capped at 10. It is a checklist score, not a probability.
"""


def score(atr_pct, value_cr, above_rising_200, market_ok, results_days, ext_50_pct, validated=False):
    s = 1 if validated else 3
    reasons = ["strategy not validated (+3)"] if not validated else []
    v = 0 if atr_pct < 2 else 1 if atr_pct < 3.5 else 2 if atr_pct < 5 else 3
    if v:
        reasons.append(f"volatile, moves ~{atr_pct:.1f}% a day (+{v})")
    s += v
    lq = 0 if value_cr > 100 else 1 if value_cr > 20 else 2
    if lq:
        reasons.append(f"liquidity Rs {value_cr:.0f} cr/day (+{lq})")
    s += lq
    if not above_rising_200:
        s += 1; reasons.append("not in a long-term uptrend (+1)")
    if not market_ok:
        s += 1; reasons.append("weak overall market (+1)")
    if results_days is not None and results_days <= 7:
        s += 2; reasons.append(f"results in {results_days} days (+2)")
    if ext_50_pct > 15:
        s += 1; reasons.append(f"stretched {ext_50_pct:.0f}% above 50-day avg (+1)")
    return min(10, s), reasons


def label(s):
    return "LOW" if s <= 3 else "MEDIUM" if s <= 5 else "HIGH" if s <= 7 else "VERY HIGH"
