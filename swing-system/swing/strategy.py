"""How a strategy is written (the new VANTAGE - owner 20 Nov: "simple: find entry, exit, targets and stop-loss").

A strategy is a small class in swing/strategies/<name>.py:

    from swing.strategy import Strategy

    class MyIdea(Strategy):
        name = "my_idea"            # short id
        interval = "15minute"       # minute, 3/5/10/15/30/60minute or day
        kind = "intraday"           # intraday (closed by 3:20 pm, MIS costs) or delivery (held overnight)
        def entries(self, d):       # d = the stock's Kite candles (+ d.attrs["nifty"] = NIFTY candles, same interval)
            return (d["close"] > d["high"].shift(1).rolling(20).max())      # True = BUY at this candle's close
    STRATEGY = MyIdea()

Everything else has a default the owner can change per strategy:
  stop_pct      None -> settings.yaml stop_loss_pct (1% below the entry, owner 20 Nov)
  targets_r     (2.0,)  targets as multiples of the risk (entry - stop): 2R = +2% with a 1% stop
  exits(d)      optional: True on a candle -> sell at that candle's close (e.g. "close below the 20 EMA")
  max_bars      optional: sell after this many candles
  entry_at      "close" (buy at the signal candle's close) or "next_open"
The tester and the live scanner call exactly the same code, so what is tested is what runs live."""
from dataclasses import dataclass, field

import pandas as pd


@dataclass
class Signal:
    sym: str
    time: pd.Timestamp
    entry: float
    stop: float
    targets: list = field(default_factory=list)
    strategy: str = ""
    interval: str = ""
    kind: str = ""
    note: str = ""


class Strategy:
    name = "unnamed"
    interval = "day"
    kind = "delivery"
    stop_pct = None
    targets_r = (2.0,)
    max_bars = None
    entry_at = "close"
    last_entry_time = "15:10"        # intraday: no new entries after this
    square_off_time = "15:20"        # intraday: everything sold by this time
    version = 1
    description = ""

    def entries(self, d):
        raise NotImplementedError

    def exits(self, d):
        return pd.Series(False, index=d.index)

    # ---- shared helpers
    def stop_fraction(self, settings=None):
        if self.stop_pct is not None:
            return float(self.stop_pct) / 100
        if settings is None:
            from .config import load_settings
            settings = load_settings()
        return float(settings.get("stop_loss_pct", 1.0)) / 100

    def levels(self, entry, settings=None):
        stop = entry * (1 - self.stop_fraction(settings))
        risk = entry - stop
        return stop, [round(entry + r * risk, 2) for r in self.targets_r]

    def signal_at(self, sym, d, settings=None):
        """Live: a BUY on the LAST finished candle? -> Signal or None."""
        if d is None or len(d) < 2:
            return None
        e = self.entries(d)
        if not bool(e.iloc[-1]):
            return None
        t = d.index[-1]
        if self.kind == "intraday" and t.strftime("%H:%M") > self.last_entry_time:
            return None
        px = float(d["close"].iloc[-1])
        stop, tg = self.levels(px, settings)
        return Signal(sym, t, px, round(stop, 2), tg, self.name, self.interval, self.kind)


def load_all():
    """{name: strategy} of every file in swing/strategies/."""
    import importlib
    import pkgutil
    from . import strategies
    out = {}
    for m in pkgutil.iter_modules(strategies.__path__):
        mod = importlib.import_module(f"swing.strategies.{m.name}")
        st = getattr(mod, "STRATEGY", None)
        if isinstance(st, Strategy):
            out[st.name] = st
    return out
