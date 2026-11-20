"""Live candles from Kite's stream: packets, 1-minute candles, bigger intervals, which candles close when."""
import struct
from datetime import datetime

import pandas as pd

from swing import live_feed as lf


def packet_quote(tok, ltp, vol, o, h, l, c):
    f = [tok, int(ltp * 100), 1, int(ltp * 100), vol, 0, 0, int(o * 100), int(h * 100), int(l * 100), int(c * 100)]
    return struct.pack(">iiiiiiiiiii", *f)


def message(*packets):
    out = struct.pack(">H", len(packets))
    for p in packets:
        out += struct.pack(">H", len(p)) + p
    return out


def test_parse_quote_and_index_packets():
    idx = struct.pack(">iiiiiii", 256265, 2400000, 2410000, 2390000, 2395000, 2380000, 2000)
    t = lf.parse_binary(message(packet_quote(738561, 2450.5, 120000, 2440, 2460, 2430, 2435), idx))
    assert t[0] == {"token": 738561, "ltp": 2450.5, "volume": 120000.0, "open": 2440.0, "high": 2460.0, "low": 2430.0,
                    "close": 2435.0}
    assert t[1]["token"] == 256265 and t[1]["ltp"] == 24000.0 and t[1]["high"] == 24100.0
    assert lf.parse_binary(b"\x00") == []                      # heartbeat


def feed_ticks(b, rows):
    for hhmmss, ltp, vol in rows:
        now = datetime(2026, 11, 20, *map(int, hhmmss.split(":")))
        b.tick({"token": 1, "ltp": ltp, "volume": vol, "open": 100, "high": 105, "low": 95, "close": 99}, now)


def test_minute_candles_from_ticks():
    b = lf.CandleBuilder({1: "AAA"})
    feed_ticks(b, [("09:15:01", 100, 1000), ("09:15:30", 102, 1500), ("09:15:59", 101, 1800),
                   ("09:16:05", 99, 2000), ("09:16:50", 98, 2600)])
    b.close_minute(datetime(2026, 11, 20, 9, 17))
    m = b.minutes("AAA")
    assert m.iloc[0].tolist() == [100, 102, 100, 101, 800]       # volume = growth during the minute
    assert m.iloc[1].tolist() == [99, 99, 98, 98, 800]
    assert b.today("AAA", "day").iloc[0]["close"] == 98


def test_bigger_candles_only_when_finished():
    b = lf.CandleBuilder({1: "AAA"})
    rows = []
    for i in range(7):                                            # 9:15 ... 9:21, one tick each minute
        rows.append((f"09:{15 + i}:10", 100 + i, 1000 * (i + 1)))
    feed_ticks(b, rows)
    b.close_minute(datetime(2026, 11, 20, 9, 22))
    five = b.today("AAA", "5minute", now=datetime(2026, 11, 20, 9, 22))
    assert list(five.index.strftime("%H:%M")) == ["09:15"]           # 9:20 candle not finished yet
    assert five.iloc[0]["open"] == 100 and five.iloc[0]["close"] == 104


def test_which_candles_close():
    at = lambda h, m: lf.closed_intervals(datetime(2026, 11, 20, h, m))
    assert at(9, 15) == ["minute"]
    assert set(at(9, 19)) == {"minute", "5minute"}
    assert set(at(9, 44)) == {"minute", "3minute", "5minute", "10minute", "15minute", "30minute"}
    assert "60minute" in at(10, 14)
    assert set(at(15, 29)) == set(lf.INTRADAY) | {"day"}            # 3:30 pm: everything and the day


def test_save_and_reload(tmp_path, monkeypatch):
    monkeypatch.setattr(lf, "LIVE", tmp_path)
    b = lf.CandleBuilder({1: "AAA"})
    feed_ticks(b, [("09:15:01", 100, 1000), ("09:16:01", 101, 1500)])
    b.close_minute(datetime(2026, 11, 20, 9, 17))
    assert b.save("2026-11-20") == 2
    c = lf.CandleBuilder({1: "AAA"})
    assert c.load_saved("2026-11-20") == 2 and len(c.minutes("AAA")) == 2


def test_history_repair_wins():
    b = lf.CandleBuilder({1: "AAA"})
    feed_ticks(b, [("09:15:01", 100, 1000)])
    b.close_minute(datetime(2026, 11, 20, 9, 16))
    k = pd.DataFrame({"open": [100.5], "high": [101], "low": [99], "close": [100.2], "volume": [5000.0]},
                     index=pd.DatetimeIndex([pd.Timestamp("2026-11-20 09:15")]))
    b.add_history("AAA", k)
    assert b.minutes("AAA").iloc[0]["volume"] == 5000
