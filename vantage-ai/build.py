"""Builds the two TradingView scripts from ONE shared core, so the indicator and the backtesting strategy can never
drift apart. Run: python3 build.py   (then copy each .pine file into TradingView's Pine Editor)."""
from pathlib import Path

HERE = Path(__file__).parent
CORE = (HERE / "src" / "core.pine").read_text()
LICENSE = ("// This work is licensed under CC BY-NC-SA 4.0 (https://creativecommons.org/licenses/by-nc-sa/4.0/) because it\n"
           "// includes a port of 'Rolling Candle Profile with Buy/Sell Signals' (c) Zeiierman (CC BY-NC-SA 4.0). Also rebuilt\n"
           "// from open-source ideas: CM Williams Vix Fix (ChrisMoody), WaveTrend + Squeeze (LazyBear), Market Structure\n"
           "// Break & Order Block (EmreKb). Personal, non-commercial use.\n"
           "// VANTAGE AI — NSE positional decision-support engine (long-only, daily). Research tool, not advice.\n")

HEAD_IND = ('//@version=6\n' + LICENSE +
            'indicator("VANTAGE AI — NSE Positional Decision Engine", shorttitle = "VANTAGE AI", overlay = true,\n'
            '     max_labels_count = 500, max_lines_count = 50, max_boxes_count = 50, max_bars_back = 1000)\n')
HEAD_STR = ('//@version=6\n' + LICENSE +
            'strategy("VANTAGE AI — Backtest (identical logic)", shorttitle = "VANTAGE AI BT", overlay = true,\n'
            '     initial_capital = 50000, currency = currency.INR, pyramiding = 0, default_qty_type = strategy.fixed,\n'
            '     default_qty_value = 1, commission_type = strategy.commission.percent, commission_value = 0.12,\n'
            '     slippage = 2, process_orders_on_close = false, calc_on_every_tick = false, max_bars_back = 1000)\n'
            '// Costs: 0.12% per side ≈ delivery STT 0.1% + exchange/SEBI/stamp/GST; slippage 2 ticks. Change in Properties.\n')


def calibrated(core):
    """Fill the likely-% table from the 13-year test (validation/results_final.json -> calibration)."""
    import json
    cal = json.load(open(HERE / "validation" / "results_final.json"))["Fixed risk/reward"]["calibration"]
    def get(k, f, default):
        v = cal.get(k, {}).get(f)
        return default if v is None else v
    pairs = {"DIP_A": "Dip-buy A", "DIP_B": "Dip-buy B", "DIP_C": "Dip-buy C", "RCP": "RCP",
             "BRK_90": "Breakout 90+", "BRK_80": "Breakout 80-89", "BRK_70": "Breakout 70-79", "PB": "Pullback"}
    if not cal.get("Pullback"):          # pullbacks are OFF in the final run -> use the step-1 test (Fixed exits)
        cal["Pullback"] = {"win_pct": 33, "n": 397}
    for tok, key in pairs.items():
        core = core.replace(f"__{tok}__", str(int(get(key, "win_pct", get(key.split(" ")[0], "win_pct", 0)))))
        core = core.replace(f"__N_{tok}__", str(int(get(key, "n", get(key.split(" ")[0], "n", 0)))))
    assert "__" not in core.split("likelyN")[1][:600], "calibration token left"
    return core


def _code_part(line):
    """The line without a trailing // comment (ignoring // inside strings)."""
    q = None
    for i, ch in enumerate(line):
        if q:
            if ch == q:
                q = None
        elif ch in "\"'":
            q = ch
        elif line.startswith("//", i):
            return line[:i]
    return line


def unwrap(text):
    """Join every wrapped continuation line (indent not a multiple of 4) onto its statement, so each statement is ONE
    line. TradingView's mobile editor can change leading spaces on paste, which breaks Pine's line-wrapping rule
    (owner 17 Nov: 'Syntax error at input G_CAP')."""
    out = []
    for line in text.split("\n"):
        ind = len(line) - len(line.lstrip(" "))
        if line.strip() and not line.lstrip().startswith("//") and ind % 4 != 0 and out:
            prev = out[-1]
            assert _code_part(prev) == prev, "a wrapped statement follows a line with a comment: " + prev
            out[-1] = prev.rstrip() + " " + line.strip()
        else:
            out.append(line)
    res = "\n".join(out)
    for ln in res.split("\n"):
        ind = len(ln) - len(ln.lstrip(" "))
        assert not (ln.strip() and not ln.lstrip().startswith("//") and ind % 4), "continuation left: " + ln
    return res


def build():
    global CORE
    CORE = calibrated(CORE)
    ind = HEAD_IND + CORE + (HERE / "src" / "indicator_tail.pine").read_text()
    st = HEAD_STR + CORE + (HERE / "src" / "strategy_tail.pine").read_text()
    ind, st = unwrap(ind), unwrap(st)
    (HERE / "VANTAGE_AI_Indicator.pine").write_text(ind)
    (HERE / "VANTAGE_AI_Strategy.pine").write_text(st)
    return ind, st


def core_of(text):
    a = text.index("// ===== CORE BEGIN")
    b = text.index("// ===== CORE END")
    return text[a:b]


if __name__ == "__main__":
    ind, st = build()
    assert core_of(ind) == core_of(st), "core differs!"
    print("built: VANTAGE_AI_Indicator.pine (%d lines), VANTAGE_AI_Strategy.pine (%d lines); core identical"
          % (ind.count("\n"), st.count("\n")))
