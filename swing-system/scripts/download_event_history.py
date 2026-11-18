"""Research data (owner 18 Nov): NSE history of bulk deals (#5), insider/promoter trades (#4) and buyback
announcements (#9), 2013 -> today, month by month, into data/events/history/ (not in git: data/ is private cache).
Resumable: months already saved are skipped. Polite: one request every ~1.5 s.
python3 scripts/download_event_history.py [bulk|insider|buyback|all]"""
import json
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from swing.config import DATA  # noqa: E402
from swing import nse_filings as nf  # noqa: E402

OUT = DATA / "events" / "history"
API = "https://www.nseindia.com/api"


def months(start="2013-01-01"):
    m = pd.date_range(start, pd.Timestamp.today(), freq="MS")
    return [(a, (a + pd.offsets.MonthEnd(0))) for a in m]


def fetch(kind, a, b, s):
    f, t = f"{a:%d-%m-%Y}", f"{b:%d-%m-%Y}"
    if kind == "bulk":           # the JSON form stops at 70 rows; the CSV form is complete
        import io
        r = s.get(f"{API}/historicalOR/bulk-block-short-deals?optionType=bulk_deals&from={f}&to={t}&csv=true",
                  headers=nf.UA, timeout=120)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.content.decode("utf-8-sig", "ignore")), thousands=",")
        df.columns = [c.strip() for c in df.columns]
        return df
    if kind == "insider":
        d = nf._get_json(s, f"{API}/corporates-pit?index=equities&from_date={f}&to_date={t}")
        rows = d.get("data") or []
        keep = ["symbol", "personCategory", "acqMode", "tdpTransactionType", "secAcq", "secVal", "acqfromDt", "acqtoDt",
                "intimDt", "date", "befAcqSharesPer", "afterAcqSharesPer"]
        return pd.DataFrame([{k: r.get(k) for k in keep} for r in rows])     # no person names kept
    if kind == "buyback":
        d = nf._get_json(s, f"{API}/corporate-announcements?index=equities&from_date={f}&to_date={t}")
        rows = [r for r in (d or []) if "buy" in (str(r.get("desc", "")) + str(r.get("attchmntText", ""))).lower()
                and "back" in (str(r.get("desc", "")) + str(r.get("attchmntText", ""))).lower()]
        return pd.DataFrame([{"symbol": r.get("symbol"), "an_dt": r.get("an_dt"), "desc": r.get("desc"),
                              "text": str(r.get("attchmntText", ""))[:300]} for r in rows])
    if kind == "bonus":
        d = nf._get_json(s, f"{API}/corporate-announcements?index=equities&from_date={f}&to_date={t}")
        rows = [r for r in (d or []) if "bonus" in (str(r.get("desc", "")) + " " + str(r.get("attchmntText", ""))).lower()]
        return pd.DataFrame([{"symbol": r.get("symbol"), "an_dt": r.get("an_dt"), "desc": r.get("desc"),
                              "text": str(r.get("attchmntText", ""))[:300]} for r in rows])
    if kind == "index":
        d = nf._get_json(s, f"{API}/press-release-cms20?fromDate={f}&toDate={t}")
        rows = []
        for x in d or []:
            c = x.get("content") or {}
            body = str(c.get("body") or "")
            att = (c.get("field_file_attachement") or {}).get("url")
            if str(c.get("title", "")).strip().upper() == "NSE INDICES" and "eplacement" in body and att:
                pdf = OUT / "index_pdfs" / att.rsplit("/", 1)[-1]
                if not pdf.exists():
                    pdf.parent.mkdir(parents=True, exist_ok=True)
                    r = s.get(att.replace("in//", "in/"), headers=nf.UA, timeout=60)
                    if r.status_code == 200 and r.content[:4] == b"%PDF":
                        pdf.write_bytes(r.content)
                    time.sleep(1.5)
                rows.append({"date": x.get("changed"), "title": body[:200], "pdf": pdf.name if pdf.exists() else ""})
        return pd.DataFrame(rows)
    raise ValueError(kind)


def run(kind):
    out = OUT / kind
    out.mkdir(parents=True, exist_ok=True)
    s, n_new, fails = nf._session(), 0, 0
    for a, b in months():
        f = out / f"{a:%Y-%m}.csv"
        if f.exists() and a + pd.offsets.MonthEnd(0) < pd.Timestamp.today() - pd.Timedelta(days=3):
            continue
        for attempt in range(3):
            try:
                df = fetch(kind, a, b, s)
                df.to_csv(f, index=False)
                n_new += 1
                break
            except Exception as e:
                fails += 1
                time.sleep(5 * (attempt + 1))
                s = nf._session()
                if attempt == 2:
                    print(kind, f"{a:%Y-%m}", "failed:", type(e).__name__, flush=True)
        time.sleep(1.5)
    print(kind, "months saved:", n_new, "retries:", fails, flush=True)


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    for k in (["bulk", "insider", "buyback", "index"] if which == "all" else [which]):
        run(k)
