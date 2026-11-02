"""Writes validation/search.html from validation/search_latest.json (plain-English search report)."""
import html
import json

from .config import DISCLAIMER, ROOT

VAL = ROOT / "validation"


def _tbl(rows, cols, labels=None):
    labels = labels or cols
    th = "".join(f"<th>{html.escape(l)}</th>" for l in labels)
    tb = "".join("<tr>" + "".join(f"<td>{html.escape(str(r.get(c, '')))}</td>" for c in cols) + "</tr>" for r in rows)
    return f"<table><tr>{th}</tr>{tb}</table>"


def write():
    o = json.loads((VAL / "search_latest.json").read_text())
    ok = o["passed"]
    checks = "".join(f"<tr><td style='color:{'#15803d' if c['passed'] else '#b91c1c'}'><b>{'PASS' if c['passed'] else 'FAIL'}</b></td>"
                     f"<td>{html.escape(c['check'])}</td><td>{html.escape(c['detail'])}</td></tr>" for c in o["checks"])
    h = o["holdout"]
    page = f"""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Strategy Search</title><style>body{{font-family:system-ui,Segoe UI,Arial;max-width:1000px;margin:auto;padding:16px;color:#0f172a;background:#fff;line-height:1.45}}
table{{border-collapse:collapse;font-size:12px;display:block;overflow-x:auto;margin:6px 0 14px}}td,th{{border-bottom:1px solid #e2e8f0;padding:4px 6px;text-align:left}}</style></head><body>
<h1>Strategy search report ({o['date']})</h1><p><b>{DISCLAIMER}</b></p>
<h2 style='color:{'#15803d' if ok else '#b91c1c'}'>SEARCH GATE {'PASSED' if ok else 'FAILED'}</h2>
<p>The system tested <b>{o['variants_searched']}</b> different strategies (10 families x stop-losses x exits x holding
periods x market filter). Raw variants ever backtested: <b>{o['raw_variants_ever']}</b>. With that many tries some
look great by pure luck, so the only fair test is this: <b>every January, pick the strategy that did best over the
previous 3 years, then see how that pick did in the year that followed</b>. That is what you would have experienced.</p>
<table>{checks}</table>
<h2>Year by year: what the search picked, and how it then did</h2>
{_tbl(o['picks'], ['year', 'picked', 'how', 'past_36m_sharpe', 'return_pct', 'niftybees_pct', 'trades', 'beat_niftybees'],
      ['Year', 'Pick', 'Strategy', 'Past 3y Sharpe', 'Next-year return %', 'NIFTYBEES %', 'Trades', 'Beat index?'])}
<p>Walk-forward chain: about {o['chain_cagr_pct']}% a year vs NIFTYBEES about {o['niftybees_cagr_pct_wf']}% a year
(2013-Apr 2025 for the index); worst fall {o['chain_max_dd']}%; t-stat vs index {o['chain_t']}.</p>
<h2>Holdout (never used for any choice)</h2>
<p>Pick made with data up to the holdout start: <b>{html.escape(h['picked'])}</b> ({html.escape(h['how'])}).
Result {h.get('total_return_pct')}% (worst fall {h.get('max_drawdown_pct')}%, {h.get('trades', 0)} trades) vs NIFTYBEES
{h['niftybees_return_pct']}% vs liquid fund {h['liquid_fund_return_pct']}%.</p>
<h2>Which families work best on average (median of all their variants, 2013-Apr 2025)</h2>
{_tbl(o['family_medians'], ['family', 'cagr_pct', 'max_drawdown_pct', 'sharpe'], ['Family', 'CAGR %', 'Max drawdown %', 'Sharpe'])}
<p>Share of all variants whose growth beat NIFTYBEES over the whole period: {o['share_variants_beating_niftybees_cagr']:.0%}.</p>
<h2>Cherry-picked top 10 (NOT evidence)</h2>
<p>These are the best of {o['variants_searched']} backtests chosen with hindsight. To count as real after this many tries,
a t-stat of at least {o['cherry_haircut_t_needed']} would be needed. Shown for transparency only.</p>
{_tbl(o['cherry_picked_top10'], ['variant', 'how', 't_vs_niftybees', 'cagr_pct', 'max_dd_pct', 'trades'],
      ['Variant', 'Strategy', 't vs index', 'CAGR %', 'Max DD %', 'Trades'])}
<h2>Caveats</h2><ul><li>Same data caveats as validation/latest.html: survivorship bias (delisted stocks missing, which
flatters results), Yahoo data errors, fundamentals not tested, tax not included.</li>
<li>Each year's result comes from that strategy's continuous backtest (positions carried over), a small simplification.</li></ul>
</body></html>"""
    (VAL / "search.html").write_text(page, encoding="utf-8")
