"""Runs the full validation of one strategy version and writes validation/latest.html + json."""
import html
import json
from datetime import date

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from . import backtest, data_prices, engine, validate
from .config import DISCLAIMER, get_logger
from .validate import VAL

log = get_logger()

CAVEATS = [
    "SURVIVORSHIP BIAS: the universe is rebuilt each month from official NSE data (including stocks later "
    "delisted), but free price history (Yahoo) exists only for stocks still listed today. Stocks that were "
    "in the universe but later delisted, merged or renamed are MISSING from the backtest. Those are often "
    "the losers, so results are probably flattered. Coverage is reported above.",
    "DATA QUALITY: prices come from Yahoo Finance and are cross-checked against NSE official closing prices; "
    "stocks that disagree or have unexplained jumps are quarantined (excluded). Yahoo data still contains "
    "undetected errors, and demergers are not adjusted.",
    "FUNDAMENTALS are NOT part of this backtest (free point-in-time history does not exist for 10+ years). "
    "The live quality screen can only remove tips; its effect is untested.",
    "RESULTS DATES used in tests are actual historical dates; in reality a date is known only a few days "
    "in advance.",
    "UNCERTAINTY: a few hundred trades over ~12 years is a small sample. Past performance - even when "
    "honestly tested - does not predict future returns. Market regimes change.",
    "COSTS: Zerodha delivery charges (STT 0.1% each side, exchange, SEBI, GST, stamp duty, DP Rs 15.34 per "
    "sell) + 0.15% slippage per side are included. Income tax on gains (STCG) is NOT included.",
]


def run(strategy_name, params=None, note="live version re-validation", write=True):
    from .config import load_strategy
    p = params or load_strategy(strategy_name)
    n_var = validate.register_variant(p, note)
    P, sig, nifty, industry, coverage, hist = engine.build(p, use_results_filter=(p.get("results_rule") == "exclude"))
    table, trades = validate.evaluate(P, sig, p)
    ceq, ctr, cex, t = validate.continuous(P, sig, p)
    g = validate.gate(table, ceq, ctr, t, n_var)
    g["date"] = str(date.today())
    wf_tr = trades[trades["period"].str.startswith("WF")] if len(trades) else trades
    res = {"strategy": strategy_name, "params_hash": validate.params_hash(p), "gate": g,
           "periods": table.to_dict("records"), "coverage": coverage, "tstat": round(t, 2),
           "continuous": backtest.stats(ceq, ctr), "setup_stats": validate.setup_stats(wf_tr),
           "wf_summary": {"closed": int(len(wf_tr)),
                          "win_rate_pct": round((wf_tr["pnl"] > 0).mean() * 100, 1) if len(wf_tr) else None,
                          "avg_r": round(wf_tr["r_multiple"].mean(), 2) if len(wf_tr) else None,
                          "total_pnl": "-"},
           "holdout_start": validate.HOLDOUT_START, "data_end": str(P["close"].index[-1].date())}
    if not write:
        return res, ceq, table
    (VAL / "latest.json").write_text(json.dumps(res, indent=1, default=str))
    gs = json.loads(validate.GATE.read_text()) if validate.GATE.exists() else {}
    gs[strategy_name] = g
    validate.GATE.write_text(json.dumps(gs, indent=1))
    trades.to_csv(VAL / f"trades_{strategy_name}.csv", index=False)

    # chart: continuous walk-forward equity vs benchmarks
    lf = data_prices.liquid_fund_nav()
    bees = data_prices.benchmark()["close"]
    b = backtest.buy_and_hold(bees, ceq.index[0], ceq.index[-1])
    m = backtest.exposure_matched(bees, cex, lf)
    lfq = lf.reindex(lf.index.union(ceq.index)).ffill().reindex(ceq.index)
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.plot(ceq.index, ceq / 1000, label=f"Strategy {strategy_name} (after costs)", lw=1.6, color="#2563eb")
    ax.plot(b.index, b / 1000, label="NIFTYBEES buy & hold", lw=1.2, color="#f59e0b")
    ax.plot(m.index, m / 1000, label="Same exposure in NIFTYBEES, rest liquid fund", lw=1, color="#9333ea", alpha=.8)
    ax.plot(lfq.index, 45 * lfq / lfq.iloc[0], label="Liquid fund only", lw=1, color="#6b7280")
    ax.set_ylabel("Rs thousands (start 45k)")
    ax.set_title("Walk-forward span (holdout excluded)")
    ax.grid(alpha=.2)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(VAL / "equity.png", dpi=90)
    plt.close(fig)

    cols = ["period", "total_return_pct", "niftybees_return_pct", "liquid_fund_return_pct",
            "exposure_matched_return_pct", "max_drawdown_pct", "niftybees_max_dd_pct", "trades", "win_rate_pct",
            "avg_r", "avg_exposure_pct", "beat_niftybees"]
    th = "".join(f"<th>{c}</th>" for c in cols)
    tb = "".join("<tr>" + "".join(f"<td>{r.get(c, '')}</td>" for c in cols) + "</tr>" for r in res["periods"])
    checks = "".join(f"<tr><td style='color:{'#15803d' if c['passed'] else '#b91c1c'}'><b>{'PASS' if c['passed'] else 'FAIL'}"
                     f"</b></td><td>{html.escape(c['check'])}</td><td>{html.escape(c['detail'])}</td></tr>" for c in g["checks"])
    cov = coverage
    cov_txt = (f"{cov['with_price_data']} of {cov['universe_symbols_ever']} stocks that were ever in the monthly "
               f"top-500 have usable price data ({cov['with_price_data'] / max(1, cov['universe_symbols_ever']):.0%}). "
               f"{cov['quarantined']} were quarantined for bad data.")
    page = f"""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Validation {strategy_name}</title><style>body{{font-family:system-ui,Segoe UI,Arial;max-width:1000px;margin:auto;padding:16px;background:#fff;color:#0f172a}}
table{{border-collapse:collapse;font-size:12px;display:block;overflow-x:auto}}td,th{{border-bottom:1px solid #e2e8f0;padding:4px 6px;white-space:nowrap}}img{{max-width:100%}}</style></head><body>
<h1>Validation report - strategy {strategy_name} ({date.today()})</h1>
<p><b>{DISCLAIMER}</b></p>
<h2 style='color:{'#15803d' if g['passed'] else '#b91c1c'}'>GATE {'PASSED' if g['passed'] else 'FAILED'}</h2>
<table>{checks}</table>
<p>Variants tried so far (all versions and proposals ever tested): <b>{g['variants_tried']}</b>.
More variants = higher chance of a lucky fit, so the bar rises with this number.</p>
<h2>Every period (each starts fresh with Rs 45,000)</h2><table><tr>{th}</tr>{tb}</table>
<p>Walk-forward periods are calendar years from {validate.WF_START} to before {validate.HOLDOUT_START}. Strategy settings were fixed
before testing and were not tuned on any of them. The HOLDOUT ({validate.HOLDOUT_START} to {res['data_end']}) is never used to choose settings.</p>
<h2>Continuous walk-forward run</h2><p>{html.escape(json.dumps(res['continuous']))}; t-stat of monthly excess return vs NIFTYBEES: {res['tstat']}</p>
<img src='equity.png' alt='equity curve'>
<h2>Setup hit-rates (walk-forward trades)</h2><p>{html.escape(json.dumps(res['setup_stats']))}</p>
<h2>Coverage</h2><p>{html.escape(cov_txt)}</p>
<h2>Honest caveats</h2><ul>{''.join(f'<li>{html.escape(c)}</li>' for c in CAVEATS)}</ul>
</body></html>"""
    (VAL / "latest.html").write_text(page, encoding="utf-8")
    (VAL / f"validation_{strategy_name}_{date.today()}.html").write_text(page, encoding="utf-8")
    log.info("Validation %s: gate %s", strategy_name, "PASSED" if g["passed"] else "FAILED")
    return res, ceq, table
