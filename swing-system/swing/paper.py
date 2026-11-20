"""PRACTICE ACCOUNT (owner 20 Nov: "you have ₹50,800 as funds" - pretend money, real Kite prices, real charges).
No real order is ever placed: every fill is simulated and recorded here.

Fills:   buys fill a little above the price, sells a little below (slippage: options max(₹0.05, 0.3%),
         stocks 0.05%); a stop-loss that is jumped over fills at the worse price.
Charges: Zerodha's real charges (options: ₹20 an order, 0.1% STT on sell premium, exchange, SEBI, stamp, GST;
         intraday stocks: 0.03%/₹20 brokerage, 0.025% STT on sells, exchange, SEBI, stamp, GST).
Money:   options need their full premium; intraday (MIS) stocks need 25% of their value (4x - Zerodha gives up
         to 5x on the most liquid stocks, less on many; 25% is the cautious figure).
The dashboard shows P&L like Zerodha's 'Closed positions' (before charges) and the charges and net below it."""
import json
from dataclasses import asdict, dataclass, field

import pandas as pd

from . import costs
from .config import PRIVATE, get_logger

log = get_logger()
MIS_MARGIN = 0.25          # owner 20 Nov: never assume more leverage than Zerodha gives (4x, many stocks)


def slip(price, kind):
    return max(0.05, 0.003 * price) if kind == "OPT" else 0.0005 * price


@dataclass
class Position:
    key: str
    name: str
    symbol: str              # Kite instrument ("NFO:NIFTY..." or "RELIANCE")
    kind: str                # OPT or EQ
    side: str                # LONG or SHORT
    qty: int
    avg: float
    stop: float
    target: float
    strategy: str
    entry_time: str
    ltp: float = 0.0
    best: float = 0.0
    lots: int = 0
    note: str = ""
    t1: float = 0.0                 # scaling out: first target (1R); 0 = off
    book_frac: float = 0.0          # share booked at t1
    scaled: bool = False
    margin: float = 0.25            # share of the value blocked (stocks: Kite's own figure when available)


@dataclass
class Account:
    start: float = 50800.0
    cash: float = 50800.0                       # after realised P&L and charges
    open: dict = field(default_factory=dict)
    closed: list = field(default_factory=list)


class Broker:
    def __init__(self, path=None, start=50800.0):
        self.path = path
        self.acc = Account(start=start, cash=start)
        if path and path.exists():
            try:
                d = json.loads(path.read_text())
                self.acc = Account(start=d["start"], cash=d["cash"], open={k: Position(**v) for k, v in d["open"].items()},
                                   closed=d["closed"])
            except Exception as e:
                log.warning("Practice account unreadable (%s) - starting fresh", type(e).__name__)

    def save(self):
        if not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"start": self.acc.start, "cash": self.acc.cash,
                                   "open": {k: asdict(v) for k, v in self.acc.open.items()}, "closed": self.acc.closed}))
        tmp.replace(self.path)

    # ---- money
    def blocked(self):
        return sum(p.qty * p.avg * (1 if p.kind == "OPT" else p.margin) for p in self.acc.open.values())

    def available(self):
        return self.acc.cash - self.blocked()

    def day_closed(self, day):
        return [c for c in self.acc.closed if c["exit_time"][:10] == str(day)[:10]]

    def day_pnl(self, day, net=True):
        return sum(c["net" if net else "pnl"] for c in self.day_closed(day))

    # ---- orders
    def open_position(self, key, name, symbol, kind, side, qty, price, stop, target, strategy, t, lots=0, note="",
                      margin=None):
        if key in self.acc.open or qty < 1:
            return None
        fill = price + slip(price, kind) if side == "LONG" else price - slip(price, kind)
        margin = MIS_MARGIN if margin is None else margin
        need = qty * fill * (1 if kind == "OPT" else margin)
        if need > self.available():
            return None
        p = Position(key, name, symbol, kind, side, int(qty), round(fill, 2), round(stop, 2), round(target, 2), strategy,
                     str(pd.Timestamp(t))[:19], ltp=fill, best=fill, lots=lots, note=note, margin=margin)
        self.acc.open[key] = p
        self.save()
        return p

    def close_position(self, key, price, t, why, gap_worse=False):
        p = self.acc.open.pop(key, None)
        if p is None:
            return None
        fill = price - slip(price, p.kind) if p.side == "LONG" else price + slip(price, p.kind)
        buy, sell = (p.avg, fill) if p.side == "LONG" else (fill, p.avg)
        bv, sv = buy * p.qty, sell * p.qty
        ch = costs.option_cost(bv, sv) if p.kind == "OPT" else costs.intraday_cost(bv, sv)
        pnl = round(sv - bv, 2)
        c = {"name": p.name, "symbol": p.symbol, "kind": p.kind, "product": "Intraday", "qty": p.qty, "side": p.side,
             "buy_avg": round(buy, 2), "sell_avg": round(sell, 2), "ltp": round(price, 2), "pnl": pnl,
             "charges": ch, "net": round(pnl - ch, 2), "entry_time": p.entry_time, "exit_time": str(pd.Timestamp(t))[:19],
             "why": why, "strategy": p.strategy, "lots": p.lots}
        self.acc.cash = round(self.acc.cash + pnl - ch, 2)
        self.acc.closed.append(c)
        self.save()
        return c

    def close_part(self, key, qty, price, t, why):
        """Book part of an open position (scaling out). The rest stays open."""
        p = self.acc.open.get(key)
        if p is None or not 0 < qty < p.qty:
            return None
        from copy import copy
        part = copy(p)
        part.qty = int(qty)
        part.lots = int(round(p.lots * qty / p.qty)) if p.lots else 0
        p.qty -= int(qty)
        p.lots = max(p.lots - part.lots, 0) if p.lots else 0
        self.acc.open[key + "-part"] = part
        return self.close_position(key + "-part", price, t, why)

    def mark(self, key, price):
        p = self.acc.open.get(key)
        if p:
            p.ltp = price
            p.best = max(p.best, price) if p.side == "LONG" else min(p.best, price)

    def set_ltp(self, day, prices):
        """End of day: the instrument's last price (the dashboard's LTP column)."""
        for c in self.day_closed(day):
            if c["symbol"] in prices:
                c["ltp"] = round(prices[c["symbol"]], 2)
        self.save()
