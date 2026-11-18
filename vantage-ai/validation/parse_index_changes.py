"""#8 data: NSE 'Replacements in indices' press-release PDFs (swing-system/data/events/history/index_pdfs, Nov 2019 ->)
-> index_changes.csv: announce_date, effective_date, index, action (include/exclude), symbol."""
import glob
import re

import pandas as pd
import pdfplumber

SRC = "/home/user/shri-labh-jewellers/swing-system/data/events/history/index_pdfs"
OUT = "/home/user/shri-labh-jewellers/vantage-ai/validation/index_changes.csv"
MONTHS = r"(January|February|March|April|May|June|July|August|September|October|November|December)"


def parse(path):
    with pdfplumber.open(path) as pdf:
        text = "\n".join((p.extract_text() or "") for p in pdf.pages)
    ann = re.search(r"(?:Mumbai,\s*)?" + MONTHS + r"\s+(\d{1,2}),\s*(\d{4})", "\n".join(text.splitlines()[:6]))
    eff = re.search(r"effective from\s+" + MONTHS + r"\s+(\d{1,2}),\s*(\d{4})", text.replace("\n", " "))
    if not ann:
        return []
    a = pd.Timestamp(f"{ann.group(1)} {ann.group(2)} {ann.group(3)}")
    e = pd.Timestamp(f"{eff.group(1)} {eff.group(2)} {eff.group(3)}") if eff else pd.NaT
    rows, index, action = [], None, None
    for line in text.splitlines():
        s = line.strip()
        m = re.match(r"^(?:\d+|[a-z])\)\s*(.+)$", s)
        if m and "Sr." not in s:
            name = m.group(1).strip()
            if "eplacement" in name:
                index, action = None, None                 # a section heading, the index names follow
            elif re.match(r"^(NIFTY|Nifty)", name):
                index, action = name, None
            continue
        if "being excluded" in s:
            action = "exclude"
            continue
        if "being included" in s:
            action = "include"
            continue
        m = re.match(r"^\d+\s+.+\s+([A-Z0-9&\-]{2,20})$", s)
        if m and index and action:
            rows.append({"announce_date": a.date(), "effective_date": e.date() if pd.notna(e) else None,
                         "index": index, "action": action, "symbol": m.group(1)})
    return rows


def main():
    rows = []
    for f in sorted(glob.glob(f"{SRC}/*.pdf")):
        try:
            rows += parse(f)
        except Exception as ex:
            print("skip", f.rsplit("/", 1)[-1], type(ex).__name__)
    D = pd.DataFrame(rows).drop_duplicates()
    D.to_csv(OUT, index=False)
    print(len(D), "changes;", D["index"].nunique(), "indices;", D["announce_date"].min(), "->", D["announce_date"].max())
    print(D["index"].value_counts().head(25).to_string())


if __name__ == "__main__":
    main()
