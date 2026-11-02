"""Daily HTML report, per-stock charts and per-stock notes (stocks/SYMBOL.md)."""
import html
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from .config import DISCLAIMER, REPORTS, STOCKS

CHARTS = REPORTS / "charts"
CHARTS.mkdir(parents=True, exist_ok=True)


def stock_chart(sym, raw, plan, day):
    """Price (last ~9 months) with 20/50/200-day averages and the trade-plan levels."""
    df = raw.tail(260).copy()
    c = raw["close"]
    fig, (ax, axv) = plt.subplots(2, 1, figsize=(8, 4.6), sharex=True, gridspec_kw={"height_ratios": [4, 1]})
    show = df.index[-180:]
    ax.plot(show, df.loc[show, "close"], color="#1f2937", lw=1.4, label="Close")
    for n, col in ((20, "#2563eb"), (50, "#f59e0b"), (200, "#9333ea")):
        ax.plot(show, c.rolling(n).mean().reindex(show), lw=1, color=col, label=f"{n}-day avg")
    if plan:
        for key, col, lab in (("stop", "#dc2626", "Stop"), ("entry_high", "#6b7280", "Do not buy above"),
                              ("target1", "#16a34a", "Target 1"), ("target2", "#15803d", "Target 2")):
            ax.axhline(plan[key], color=col, ls="--", lw=1)
            ax.text(show[-1], plan[key], f"{lab} {plan[key]:.2f} ", color=col, fontsize=7, va="bottom", ha="right")
    ax.set_title(f"{sym}  ({day})", fontsize=10)
    ax.legend(fontsize=7, loc="lower left", framealpha=0.6)
    ax.grid(alpha=0.2)
    axv.bar(show, df.loc[show, "volume"], color="#9ca3af", width=1)
    axv.set_ylabel("Volume", fontsize=7)
    fig.autofmt_xdate()
    fig.tight_layout()
    f = CHARTS / f"{day}_{sym}.png"
    fig.savefig(f, dpi=90)
    plt.close(fig)
    return f"charts/{f.name}"


def append_stock_note(sym, day, plan, extra):
    """Keep a running per-stock memory file so context carries over between days."""
    f = STOCKS / f"{sym}.md"
    head = "" if f.exists() else f"# {sym} - running notes\n\n{DISCLAIMER}\n\n"
    lines = [f"## {day}"]
    if plan:
        lines.append(f"- Setup: **{plan['setup']}**, score {plan['score']:.0f}/100")
        lines.append(f"- Plan: entry {plan['entry_low']}-{plan['entry_high']}, stop {plan['stop']}, "
                     f"T1 {plan['target1']}, T2 {plan['target2']}, qty {plan['qty']}")
        lines.append(f"- Reasons: {'; '.join(plan['reasons'])}")
        lines.append(f"- Risks: {'; '.join(plan['risks'])}")
    for k, v in (extra or {}).items():
        lines.append(f"- {k}: {v}")
    with open(f, "a", encoding="utf-8") as fh:
        fh.write(head + "\n".join(lines) + "\n\n")


def _table(rows, cols):
    if not rows:
        return "<p class='muted'>None.</p>"
    h = "".join(f"<th>{html.escape(c)}</th>" for c in cols)
    b = "".join("<tr>" + "".join(f"<td>{html.escape(str(r.get(c, '')))}</td>" for c in cols) + "</tr>" for r in rows)
    return f"<table><tr>{h}</tr>{b}</table>"


CSS = """
:root{--bg:#f8fafc;--card:#fff;--ink:#0f172a;--muted:#64748b;--line:#e2e8f0;--good:#15803d;--bad:#b91c1c;--warn:#b45309}
@media (prefers-color-scheme: dark){:root{--bg:#0b1220;--card:#111a2e;--ink:#e2e8f0;--muted:#94a3b8;--line:#1e293b;--good:#4ade80;--bad:#f87171;--warn:#fbbf24}}
body{font-family:system-ui,Segoe UI,Arial,sans-serif;background:var(--bg);color:var(--ink);margin:0;padding:16px;max-width:980px;margin:auto;line-height:1.45}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:12px 0}
h1{font-size:22px;margin:4px 0} h2{font-size:17px;margin:4px 0 8px} h3{font-size:15px;margin:6px 0}
.muted{color:var(--muted)} .good{color:var(--good)} .bad{color:var(--bad)} .warn{color:var(--warn)}
.banner{font-size:18px;font-weight:700;padding:14px;border-radius:10px;border:2px solid currentColor}
table{border-collapse:collapse;width:100%;font-size:13px;overflow-x:auto;display:block}
th,td{border-bottom:1px solid var(--line);padding:5px 6px;text-align:left;white-space:nowrap}
img{max-width:100%;border-radius:6px;background:#fff}
.kv td:first-child{color:var(--muted)}
"""


def daily_html(ctx):
    """ctx: dict assembled by scripts/run_nightly.py."""
    day = ctx["day"]
    parts = [f"<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
             f"<title>Swing Report {day}</title><style>{CSS}</style></head><body>"]
    parts.append(f"<h1>Swing report for {day}</h1><p class='muted'>Generated {datetime.now():%Y-%m-%d %H:%M}. "
                 f"Strategy {ctx['strategy']} | mode: {ctx['mode_text']}</p>")
    parts.append(f"<div class='card'><b>{html.escape(DISCLAIMER)}</b></div>")
    cls = "good" if ctx["tips"] else "bad"
    parts.append(f"<div class='card banner {cls}'>{html.escape(ctx['headline'])}</div>")
    if ctx.get("why"):
        parts.append("<div class='card'><h2>Why</h2><ul>" + "".join(f"<li>{html.escape(w)}</li>" for w in ctx["why"]) + "</ul></div>")
    if ctx.get("money_advice"):
        parts.append(f"<div class='card'><h2>What to do with your money</h2><p>{html.escape(ctx['money_advice'])}</p></div>")

    # Market context
    m = ctx["market"]
    parts.append("<div class='card'><h2>Market today</h2><table class='kv'>" + "".join(
        f"<tr><td>{html.escape(k)}</td><td>{html.escape(str(v))}</td></tr>" for k, v in m.items()) + "</table></div>")

    # Tips
    for i, pl in enumerate(ctx["tips"], 1):
        hr = pl.get("hit_rate", {})
        parts.append(f"<div class='card'><h2>#{i} {html.escape(pl['symbol'])} <span class='muted'>"
                     f"({html.escape(pl.get('name') or '')})</span></h2>")
        parts.append(f"<img src='{pl['chart']}' alt='chart {pl['symbol']}'>")
        rows = [
            ("Setup", f"{pl['setup']} (score {pl['score']:.0f}/100)"),
            ("Buy zone (next morning)", f"Rs {pl['entry_low']} - Rs {pl['entry_high']}"),
            ("DO NOT BUY if", f"price is above Rs {pl['entry_high']} or below Rs {pl['stop']} at the open"),
            ("Stop-loss", f"Rs {pl['stop']} (sell everything if price closes/trades below)"),
            ("Target 1", f"Rs {pl['target1']} - sell half, then move stop to your buy price"),
            ("Target 2", f"Rs {pl['target2']} - sell the rest"),
            ("Quantity", f"{pl['qty']} shares (~Rs {pl['qty'] * pl['last_close']:,.0f}); "
                         f"loss if stopped ~Rs {pl['risk_rupees']:,.0f} + charges (limit: 1% of capital)"),
            ("Expected holding", f"up to {pl['max_hold']} trading days (sell at the open after that)"),
            ("Next results date", pl.get("results") or "unknown - check before buying"),
            ("Historical hit-rate of this setup", f"{hr.get('win_rate_pct','?')}% winners, avg {hr.get('avg_r','?')}R "
                                                  f"over {hr.get('trades','?')} backtest trades" if hr else "n/a"),
        ]
        parts.append("<table class='kv'>" + "".join(f"<tr><td>{a}</td><td>{html.escape(str(b))}</td></tr>" for a, b in rows) + "</table>")
        parts.append("<h3>Reasons</h3><ul>" + "".join(f"<li>{html.escape(r)}</li>" for r in pl["reasons"]) + "</ul>")
        parts.append("<h3>Risks</h3><ul>" + "".join(f"<li>{html.escape(r)}</li>" for r in pl["risks"]) + "</ul>")
        if pl.get("claude_review"):
            parts.append(f"<h3>Claude risk review ({html.escape(pl.get('claude_verdict',''))})</h3>"
                         f"<p>{html.escape(pl['claude_review'])}</p>")
        parts.append("</div>")

    if ctx.get("removed"):
        parts.append("<div class='card'><h2>Removed by safety screens</h2>" +
                     _table(ctx["removed"], ["symbol", "reason"]) + "</div>")

    parts.append("<div class='card'><h2>Your open trades (from my_trades.csv)</h2>" +
                 _table(ctx["my_trades"], ["symbol", "buy", "last", "pnl_pct", "days_held", "status"]) +
                 "<p class='muted'>To add a trade you placed: open <b>my_trades.csv</b> in Excel/Notepad and add a line "
                 "like <code>INFY,2026-11-03,1500,7,1430</code> (symbol, buy date, buy price, quantity, stop).</p></div>")

    ps, bt = ctx["paper"], ctx["backtest_ref"]
    parts.append("<div class='card'><h2>Paper trading vs backtest</h2>"
                 f"<p>Paper period: {html.escape(ctx['paper_text'])}</p>" +
                 _table([{"": "Paper tips (live, since start)", **ps}, {"": "Shadow picks (recorded while tips blocked)", **ctx['shadow']},
                         {"": "Backtest expectation", **bt}],
                        ["", "closed", "win_rate_pct", "avg_r", "total_pnl"]) +
                 "<p class='muted'>Few closed trades = results are mostly luck. Wait for 30+ before judging.</p></div>")

    parts.append("<div class='card'><h2>System health</h2><ul>" +
                 "".join(f"<li class='{c}'>{html.escape(t)}</li>" for c, t in ctx["health"]) + "</ul></div>")
    parts.append("<div class='card'><h2>Validation gate</h2>" + ctx["gate_html"] + "</div>")
    parts.append(f"<p class='muted'>{html.escape(DISCLAIMER)}</p></body></html>")
    out = "\n".join(parts)
    f = REPORTS / f"{day}.html"
    f.write_text(out, encoding="utf-8")
    (REPORTS / "latest.html").write_text(out, encoding="utf-8")
    return f
