"""Owner 20 Nov: "show me confirmation that no live tip can silently use Yahoo data".
1) STATIC: in every module that makes live tips or alerts, every Yahoo call sits in a function that first checks
   data_prices.yahoo_allowed() (true only in an explicit comparison run), and price history is read only through
   data_prices.load (strict Kite).
2) DYNAMIC: with Yahoo made to explode and no Kite data, the live paths return nothing (no tip) instead of Yahoo."""
import ast
from pathlib import Path

import pandas as pd
import pytest

SW = Path(__file__).resolve().parents[1] / "swing"
LIVE_MODULES = ["vantage", "live_engine", "alerts", "high_prob", "breakout", "positional", "foundry_shadow", "brief",
                "basket", "intraday_paper", "live_scan", "fno_analyst", "kite", "tipcheck", "lab_rules", "kite_daily",
                "registry", "safety", "tip_status", "intraday"]
YAHOO_CALLS = ("download", "Ticker")


def _yahoo_calls(tree):
    """-> [(function name, line)] of yf.download / yf.Ticker / yfinance.* calls and _load_yahoo / download_full."""
    out = []
    for fn in [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
        for c in ast.walk(fn):
            if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute):
                base = c.func.value.id if isinstance(c.func.value, ast.Name) else ""
                if (base in ("yf", "yfinance") and c.func.attr in YAHOO_CALLS) or \
                        c.func.attr in ("_load_yahoo", "download_full", "patch_today_from_intraday", "patch_missing_day_batch"):
                    out.append((fn, c.lineno))
    return out


@pytest.mark.parametrize("mod", LIVE_MODULES)
def test_every_live_yahoo_call_is_guarded(mod):
    f = SW / f"{mod}.py"
    if not f.exists():
        pytest.skip("module not present")
    src = f.read_text()
    tree = ast.parse(src)
    for fn, line in _yahoo_calls(tree):
        body = ast.get_source_segment(src, fn) or ""
        assert "yahoo_allowed" in body or mod == "kite_daily", \
            f"{mod}.py:{line} ({fn.name}) can reach Yahoo without the yahoo_allowed() guard"


def test_kite_daily_uses_yahoo_only_to_verify():
    """kite_daily touches Yahoo only in the comparison audit / the non-strict frame - never in frame_strict."""
    src = (SW / "kite_daily.py").read_text()
    tree = ast.parse(src)
    strict = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "frame_strict")
    assert "_load_yahoo" not in (ast.get_source_segment(src, strict) or "")


def test_live_paths_return_nothing_without_kite(monkeypatch):
    import yfinance
    from swing import data_prices, kite, kite_daily, intraday_paper, live_scan, tipcheck

    def boom(*a, **k):
        raise AssertionError("a live path tried to use Yahoo")
    monkeypatch.setattr(yfinance, "download", boom)
    monkeypatch.setattr(yfinance, "Ticker", boom)
    monkeypatch.setattr(data_prices, "_load_yahoo", boom)
    monkeypatch.delenv("SWING_PRICE_SOURCE", raising=False)
    monkeypatch.setattr(kite, "logged_in", lambda *a: False)
    monkeypatch.setattr(kite, "quotes", lambda syms: {})
    monkeypatch.setattr(kite_daily, "frame_strict", lambda s: None)
    assert data_prices.load("RELIANCE") is None                    # history: Kite or nothing
    assert kite.live_prices(["RELIANCE"]) == ({}, "unavailable")   # live prices: Kite or nothing
    snap, ts = live_scan.snapshot(["RELIANCE"])
    assert ts is None and all(len(v) == 0 for v in snap.values())  # hourly scan: no Yahoo snapshot
    assert tipcheck.live_price("RELIANCE") is None                 # forwarded-tip checker: no Yahoo price
    assert tipcheck.history("RELIANCE") is None


def test_vantage_makes_no_tip_and_reports_when_kite_history_is_missing(monkeypatch):
    from swing import vantage, kite, kite_daily, health, telegram
    reports, sent = [], []
    monkeypatch.setattr(health, "traded_today", lambda now=None: True)
    monkeypatch.setattr(kite_daily, "coverage", lambda *a: 0.02)
    monkeypatch.setattr(kite, "report_unavailable", lambda s, what, why="": reports.append((what, why)) or True)
    monkeypatch.setattr(telegram, "send_reliable", lambda *a, **k: sent.append(a))
    monkeypatch.setattr(vantage, "symbols", lambda: ["AAA"])
    from swing import data_prices
    monkeypatch.setattr(data_prices, "update", lambda syms: None)
    r = vantage.run(day="2026-11-20", source="kite")
    assert not r["ok"] and "not complete" in r["why"] and reports and reports[0][0] == "VANTAGE scan"
    assert sent == []                                              # no tip, no alert
