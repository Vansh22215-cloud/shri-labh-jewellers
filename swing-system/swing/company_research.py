"""COMPANY OF THE DAY: deep fundamental analysis across ALL NSE-listed companies (owner's request 2026-11-03).

Each night ~120 companies' annual statements are refreshed from Yahoo (free; all ~2,000+ NSE EQ companies are
covered every ~3 weeks). Every company with statements is scored 0-100 on:
  Quality 25 (ROCE, ROE, net margin)   Growth 20 (revenue & profit CAGR)   Financial health 20 (debt/equity,
  interest cover, current ratio)   Cash 15 (operating cash flow vs profit, free cash flow)   Valuation 10 (P/E, P/B)
  Piotroski F-score 10 (9 classic yes/no health tests)
Red flags (losses, negative equity, negative cash flow, very high debt) lower the score. Tradeability: the pick must
trade at least Rs 1 crore a day and cost Rs 20 or more (tiny illiquid stocks are where pump-and-dumps happen).
The pick is RESEARCH, not a trade tip: it says "worth checking", and every pick's later performance is logged
(journal/company_picks.csv) so we learn whether the method works. Yahoo's statements are restated (not
point-in-time) and sometimes incomplete; the message shows what is missing.
"""
import html
import json
import math
from datetime import date

import numpy as np
import pandas as pd

from . import data_prices
from .config import FUND, JOURNAL, get_logger
from .fundamentals import fetch_fundamentals

log = get_logger()
PICKS = JOURNAL / "company_picks.csv"
E = html.escape


def all_companies():
    from .tipcheck import equity_list
    eq = equity_list()
    ser = [c for c in eq.columns if c.strip() == "SERIES"][0]
    return eq[eq[ser].astype(str).str.strip() == "EQ"][["SYMBOL", "NAME OF COMPANY"]].rename(
        columns={"SYMBOL": "symbol", "NAME OF COMPANY": "name"})


def refresh_batch(n=120):
    """Refresh the n companies whose statements are oldest (or missing)."""
    syms = list(all_companies()["symbol"])
    def age(s):
        f = FUND / f"{s}.json"
        if not f.exists():
            return 1e12
        try:
            return 1e11 if json.loads(f.read_text()).get("v") != 2 else -f.stat().st_mtime
        except Exception:
            return 1e12
    todo = sorted(syms, key=age, reverse=True)[:n]
    ok = 0
    for s in todo:
        snap = fetch_fundamentals(s, max_age_days=0)
        ok += bool(snap.get("ok"))
    log.info("Company research: refreshed %d/%d statements", ok, len(todo))
    return ok


def _years(snap):
    y = snap.get("annual") or {}
    return [y[k] for k in sorted(y) if y[k].get("revenue")]


def _cagr(a, b, n):
    if a and b and a > 0 and b > 0 and n > 0:
        return ((b / a) ** (1 / n) - 1) * 100
    return None


def analyse(snap):
    ys = _years(snap)
    if len(ys) < 2:
        return None
    last, prev, first = ys[-1], ys[-2], ys[0]
    n = len(ys) - 1
    r = {"symbol": snap["symbol"], "name": snap.get("name") or snap["symbol"], "sector": snap.get("sector"),
         "industry": snap.get("industry"), "years": len(ys), "summary": snap.get("summary", "")}
    rev, ni, ebit, eq = last.get("revenue"), last.get("net_income"), last.get("ebit"), last.get("equity")
    cap_emp = (last.get("total_assets") or 0) - (last.get("current_liabilities") or 0)
    r["revenue_cr"] = rev / 1e7 if rev else None
    r["profit_cr"] = ni / 1e7 if ni is not None else None
    r["roce"] = ebit / cap_emp * 100 if (ebit is not None and cap_emp > 0) else None
    r["roe"] = ni / eq * 100 if (ni is not None and eq and eq > 0) else None
    r["net_margin"] = ni / rev * 100 if (ni is not None and rev) else None
    r["prev_margin"] = prev["net_income"] / prev["revenue"] * 100 if (prev.get("net_income") is not None and prev.get("revenue")) else None
    r["rev_cagr"] = _cagr(first.get("revenue"), rev, n)
    r["profit_cagr"] = _cagr(first.get("net_income"), ni, n)
    r["de"] = (last.get("debt") or 0) / eq if (eq and eq > 0) else None
    r["int_cover"] = ebit / last["interest"] if (ebit and last.get("interest")) else None
    r["current_ratio"] = last["current_assets"] / last["current_liabilities"] if (last.get("current_assets") and last.get("current_liabilities")) else None
    ocf = last.get("ocf")
    r["ocf_cr"] = ocf / 1e7 if ocf is not None else None
    r["ocf_to_profit"] = ocf / ni if (ocf is not None and ni and ni > 0) else None
    capex = last.get("capex")
    r["fcf_cr"] = (ocf + capex) / 1e7 if (ocf is not None and capex is not None) else None   # capex is negative
    r["pe"], r["pb"] = snap.get("pe"), snap.get("pb")
    r["mcap_cr"] = snap["market_cap"] / 1e7 if snap.get("market_cap") else None
    r["promoter_pct"] = snap["insider_pct"] * 100 if snap.get("insider_pct") is not None else None
    # Piotroski F-score (9 tests; missing data counts as 'no')
    ta, pta = last.get("total_assets"), prev.get("total_assets")
    roa = ni / ta if (ni is not None and ta) else None
    proa = prev["net_income"] / pta if (prev.get("net_income") is not None and pta) else None
    lev = (last.get("debt") or 0) / ta if ta else None
    plev = (prev.get("debt") or 0) / pta if pta else None
    cr_prev = prev["current_assets"] / prev["current_liabilities"] if (prev.get("current_assets") and prev.get("current_liabilities")) else None
    gm = last["gross_profit"] / rev if (last.get("gross_profit") and rev) else None
    pgm = prev["gross_profit"] / prev["revenue"] if (prev.get("gross_profit") and prev.get("revenue")) else None
    at = rev / ta if (rev and ta) else None
    pat = prev["revenue"] / pta if (prev.get("revenue") and pta) else None
    tests = {"profit positive": ni is not None and ni > 0, "operating cash flow positive": ocf is not None and ocf > 0,
             "return on assets improving": roa is not None and proa is not None and roa > proa,
             "cash flow above profit": ocf is not None and ni is not None and ocf > ni,
             "debt ratio falling": lev is not None and plev is not None and lev <= plev,
             "current ratio improving": r["current_ratio"] is not None and cr_prev is not None and r["current_ratio"] > cr_prev,
             "no share dilution": bool(last.get("shares") and prev.get("shares") and last["shares"] <= prev["shares"] * 1.01),
             "gross margin improving": gm is not None and pgm is not None and gm > pgm,
             "asset turnover improving": at is not None and pat is not None and at > pat}
    r["fscore"], r["ftests"] = sum(tests.values()), tests

    def sc(x, good, ok_):            # 1 at/above good, 0.5 at ok_, 0 below
        if x is None:
            return 0.25
        return 1.0 if x >= good else 0.5 if x >= ok_ else 0.0
    def sc_low(x, good, ok_):
        if x is None:
            return 0.25
        return 1.0 if x <= good else 0.5 if x <= ok_ else 0.0
    quality = (sc(r["roce"], 20, 12) + sc(r["roe"], 18, 10) + sc(r["net_margin"], 12, 5)) / 3
    growth = (sc(r["rev_cagr"], 15, 8) + sc(r["profit_cagr"], 18, 8)) / 2
    health = (sc_low(r["de"], 0.3, 1.0) + sc(r["int_cover"], 6, 3) + sc(r["current_ratio"], 1.5, 1.1)) / 3
    cash = (sc(r["ocf_to_profit"], 0.9, 0.6) + (1.0 if (r["fcf_cr"] or -1) > 0 else 0.0)) / 2
    val = (sc_low(r["pe"], 25, 45) + sc_low(r["pb"], 4, 8)) / 2
    r["parts"] = {"Quality": round(quality * 25, 1), "Growth": round(growth * 20, 1), "Financial health": round(health * 20, 1),
                  "Cash flow": round(cash * 15, 1), "Valuation": round(val * 10, 1), "Piotroski": round(r["fscore"] / 9 * 10, 1)}
    flags = []
    if ni is not None and ni <= 0:
        flags.append("loss-making in the latest year")
    if eq is not None and eq <= 0:
        flags.append("negative shareholder equity")
    if ocf is not None and ocf < 0:
        flags.append("operating cash flow negative")
    if r["de"] is not None and r["de"] > 2:
        flags.append(f"very high debt (debt/equity {r['de']:.1f})")
    if r["pe"] is not None and r["pe"] > 100:
        flags.append(f"very expensive (P/E {r['pe']:.0f})")
    if r["promoter_pct"] is not None and r["promoter_pct"] < 25:
        flags.append(f"low promoter/insider holding ({r['promoter_pct']:.0f}%)")
    r["flags"] = flags
    r["score"] = round(sum(r["parts"].values()) - 8 * len(flags), 1)
    return r


def price_context(sym):
    df = data_prices.load(sym)
    if df is None or (pd.Timestamp.today() - df.index[-1]).days > 7:
        data_prices.download_full([sym], start=str((pd.Timestamp.today() - pd.DateOffset(years=3)).date()))
        df = data_prices.load(sym)
    if df is None or len(df) < 60:
        return None
    c = df["close"]
    out = {"price": float(c.iloc[-1]), "value_cr": float((c * df["volume"]).tail(60).median()) / 1e7,
           "ret_1y": (c.iloc[-1] / c.iloc[-min(250, len(c) - 1)] - 1) * 100}
    if len(c) >= 200:
        out["vs_200"] = (c.iloc[-1] / c.tail(200).mean() - 1) * 100
    out["hi52_gap"] = (c.iloc[-1] / df["high"].tail(250).max() - 1) * 100
    return out


def pick_of_the_day(min_value_cr=1.0, min_price=20, cooldown_days=60):
    rows = []
    for f in FUND.glob("*.json"):
        try:
            snap = json.loads(f.read_text())
        except Exception:
            continue
        if not snap.get("ok"):
            continue
        a = analyse(snap)
        if a and not a["flags"]:
            rows.append(a)
    if not rows:
        return None, 0
    rows.sort(key=lambda x: -x["score"])
    recent = set()
    if PICKS.exists():
        pk = pd.read_csv(PICKS)
        recent = set(pk[pd.to_datetime(pk["date"]) >= pd.Timestamp.today() - pd.Timedelta(days=cooldown_days)]["symbol"])
    for a in rows[:60]:
        if a["symbol"] in recent:
            continue
        pc = price_context(a["symbol"])
        if not pc or pc["value_cr"] < min_value_cr or pc["price"] < min_price:
            continue
        a["px"] = pc
        # backups when Yahoo's profile service is down: name from NSE's list, valuation from price x shares
        if not a.get("name") or a["name"] == a["symbol"]:
            nm = all_companies().set_index("symbol")["name"].get(a["symbol"])
            a["name"] = nm or a["symbol"]
        snap = json.loads((FUND / f"{a['symbol']}.json").read_text())
        last = _years(snap)[-1]
        if last.get("shares"):
            mcap = pc["price"] * last["shares"]
            a["mcap_cr"] = a.get("mcap_cr") or mcap / 1e7
            if a.get("pe") is None and last.get("net_income") and last["net_income"] > 0:
                a["pe"] = mcap / last["net_income"]
            if a.get("pb") is None and last.get("equity") and last["equity"] > 0:
                a["pb"] = mcap / last["equity"]
            if a["pe"] is not None and a["pe"] > 100:
                continue
            a["parts"]["Valuation"] = round(((1.0 if (a["pe"] or 99) <= 25 else 0.5 if (a["pe"] or 99) <= 45 else 0)
                                             + (1.0 if (a["pb"] or 99) <= 4 else 0.5 if (a["pb"] or 99) <= 8 else 0)) / 2 * 10, 1)
            a["score"] = round(sum(a["parts"].values()) - 8 * len(a["flags"]), 1)
        rec = pd.DataFrame([{"date": str(date.today()), "symbol": a["symbol"], "score": a["score"],
                             "price": round(pc["price"], 2), "fscore": a["fscore"]}])
        (pd.concat([pd.read_csv(PICKS), rec]) if PICKS.exists() else rec).to_csv(PICKS, index=False)
        return a, len(rows)
    return None, len(rows)


def _f(x, fmt="{:,.1f}", suffix=""):
    return "n/a" if x is None or (isinstance(x, float) and not math.isfinite(x)) else fmt.format(x) + suffix


def message(a, n_scored, n_total):
    if not a:
        return f"🏢 Company of the day: none today (scored {n_scored} of {n_total} NSE companies so far)."
    px = a["px"]
    good = [k for k, v in a["ftests"].items() if v]
    bad = [k for k, v in a["ftests"].items() if not v]
    parts = " · ".join(f"{k} {v:g}" for k, v in a["parts"].items())
    trend = ("above" if px.get("vs_200", 0) > 0 else "below") + " its 200-day average" if "vs_200" in px else "trend n/a"
    lines = [
        f"🏢 <b>COMPANY OF THE DAY: {E(a['name'])} ({E(a['symbol'])})</b>",
        f"<i>{E(a.get('sector') or '')} · {E(a.get('industry') or '')}</i>",
        f"<b>Score {a['score']:.0f}/100</b> (best of {n_scored} companies analysed so far, out of {n_total} on NSE)",
        f"<pre>{parts}</pre>",
        "📋 <b>Snapshot</b>",
        f"<pre>Price        ₹{px['price']:,.2f}  (1-yr {px['ret_1y']:+.0f}%, {px['hi52_gap']:+.0f}% from 52-wk high)\n"
        f"Market cap   ₹{_f(a['mcap_cr'], '{:,.0f}')} cr   Traded ~₹{px['value_cr']:,.1f} cr/day\n"
        f"Revenue      ₹{_f(a['revenue_cr'], '{:,.0f}')} cr   Profit ₹{_f(a['profit_cr'], '{:,.0f}')} cr\n"
        f"Trend        {trend}</pre>",
        "🏆 <b>Business quality</b>",
        f"<pre>ROCE {_f(a['roce'], suffix='%')}   ROE {_f(a['roe'], suffix='%')}   Net margin {_f(a['net_margin'], suffix='%')} "
        f"(prev yr {_f(a['prev_margin'], suffix='%')})</pre>",
        "📈 <b>Growth</b> (" + str(a["years"]) + " years of statements)",
        f"<pre>Revenue {_f(a['rev_cagr'], suffix='%/yr')}   Profit {_f(a['profit_cagr'], suffix='%/yr')}</pre>",
        "🛡 <b>Financial health</b>",
        f"<pre>Debt/equity {_f(a['de'], '{:.2f}')}   Interest cover {_f(a['int_cover'], '{:.1f}', 'x')}   "
        f"Current ratio {_f(a['current_ratio'], '{:.2f}')}</pre>",
        "💵 <b>Cash flow</b>",
        f"<pre>Operating cash ₹{_f(a['ocf_cr'], '{:,.0f}')} cr ({_f(a['ocf_to_profit'], '{:.2f}', 'x')} of profit)   "
        f"Free cash ₹{_f(a['fcf_cr'], '{:,.0f}')} cr</pre>",
        "🏷 <b>Valuation</b>",
        f"<pre>P/E {_f(a['pe'], '{:.1f}')}   P/B {_f(a['pb'], '{:.1f}')}   Promoter/insider {_f(a['promoter_pct'], '{:.0f}', '%')}</pre>",
        f"🧪 <b>Piotroski F-score {a['fscore']}/9</b>",
        "✅ " + E(", ".join(good) or "none"),
        "❌ " + E(", ".join(bad) or "none"),
    ]
    if a.get("summary"):
        lines += ["🏭 <b>What it does</b>", E(a["summary"][:400] + ("…" if len(a["summary"]) > 400 else ""))]
    lines += ["⚠️ <b>Check yourself before buying:</b> latest quarterly results, promoter pledge, news, management "
              "commentary. Figures are from Yahoo's annual statements and may be incomplete or restated.",
              "<i>Research pick, not a trade tip. Research, not advice.</i>"]
    return "\n".join(lines)


def run(send=True, batch=120):
    from . import telegram
    from .config import load_settings
    refresh_batch(batch)
    total = len(all_companies())
    a, n = pick_of_the_day()
    msg = message(a, n, total)
    if send:
        telegram.send(load_settings(), msg, html=True)
    return msg
