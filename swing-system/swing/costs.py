"""Zerodha equity DELIVERY (CNC) charges on NSE.

Source: https://zerodha.com/charges/ (checked 2026-11-02)
  Brokerage            : Rs 0
  STT                  : 0.1% on buy AND sell value
  Exchange txn (NSE)   : 0.00307% of turnover
  SEBI fee             : Rs 10 per crore (0.0001%)
  Stamp duty           : 0.015% on buy side only
  GST                  : 18% on (brokerage + exchange txn + SEBI fee)
  DP charge            : Rs 15.34 per scrip per sell day (incl. GST)
Slippage is extra and modelled separately (see SLIPPAGE_PCT).
"""
STT = 0.001
EXCHANGE = 0.0000307
SEBI = 10 / 1e7
STAMP_BUY = 0.00015
GST = 0.18
DP_PER_SELL = 15.34
BROKERAGE = 0.0

# Slippage per side, as a fraction of price. 0.15% is a conservative estimate for
# market orders in top-500 NSE stocks at the open for a small (<Rs 15k) order.
SLIPPAGE_PCT = 0.0015


def buy_cost(value):
    """Rupee charges for buying shares worth `value` (excludes slippage)."""
    exch = value * EXCHANGE
    sebi = value * SEBI
    return round(value * STT + exch + sebi + value * STAMP_BUY + GST * (BROKERAGE + exch + sebi), 2)


def sell_cost(value):
    """Rupee charges for selling shares worth `value` (one sell order, excludes slippage)."""
    exch = value * EXCHANGE
    sebi = value * SEBI
    return round(value * STT + exch + sebi + GST * (BROKERAGE + exch + sebi) + DP_PER_SELL, 2)


def fill_price(price, side):
    """Price after slippage: buys fill higher, sells fill lower."""
    return price * (1 + SLIPPAGE_PCT) if side == "buy" else price * (1 - SLIPPAGE_PCT)
