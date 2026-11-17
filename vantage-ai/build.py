"""Builds the two TradingView scripts from ONE shared core, so the indicator and the backtesting strategy can never
drift apart. Run: python3 build.py   (then copy each .pine file into TradingView's Pine Editor)."""
from pathlib import Path

HERE = Path(__file__).parent
CORE = (HERE / "src" / "core.pine").read_text()
LICENSE = ("// This source code is subject to the terms of the Mozilla Public License 2.0 at https://mozilla.org/MPL/2.0/\n"
           "// VANTAGE AI — NSE positional decision-support engine (long-only, daily). Research tool, not advice.\n")

HEAD_IND = ('//@version=6\n' + LICENSE +
            'indicator("VANTAGE AI — NSE Positional Decision Engine", shorttitle = "VANTAGE AI", overlay = true,\n'
            '     max_labels_count = 500, max_lines_count = 50, max_boxes_count = 50)\n')
HEAD_STR = ('//@version=6\n' + LICENSE +
            'strategy("VANTAGE AI — Backtest (identical logic)", shorttitle = "VANTAGE AI BT", overlay = true,\n'
            '     initial_capital = 50000, currency = currency.INR, pyramiding = 0, default_qty_type = strategy.fixed,\n'
            '     default_qty_value = 1, commission_type = strategy.commission.percent, commission_value = 0.12,\n'
            '     slippage = 2, process_orders_on_close = false, calc_on_every_tick = false, max_bars_back = 500)\n'
            '// Costs: 0.12% per side ≈ delivery STT 0.1% + exchange/SEBI/stamp/GST; slippage 2 ticks. Change in Properties.\n')


def build():
    ind = HEAD_IND + CORE + (HERE / "src" / "indicator_tail.pine").read_text()
    st = HEAD_STR + CORE + (HERE / "src" / "strategy_tail.pine").read_text()
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
