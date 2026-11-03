"""NEWS intelligence (ROADMAP I4): public RSS headlines from major Indian business media, matched to stocks.

Only headlines/links are stored (personal research use). Each run appends new items to data/news/news.csv
(kept 60 days). Matching: NSE symbol or a distinctive part of the company name in the headline.
Red-flag words (fraud, raid, SEBI order, default, downgrade, resigns, probe, pledge, insolvency, ...) are flagged.
Corporate announcements from NSE/BSE are not used: both block automated access from this cloud.
Claude sessions may add a short judgement on top; the rules below are deterministic.
"""
import re
import xml.etree.ElementTree as ET

import pandas as pd
import requests

from .config import DATA, get_logger

log = get_logger()
NEWS = DATA / "news"
NEWS.mkdir(parents=True, exist_ok=True)
STORE = NEWS / "news.csv"
FEEDS = {
    "ET Markets": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "ET Stocks": "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms",
    "Moneycontrol Markets": "https://www.moneycontrol.com/rss/marketreports.xml",
    "Moneycontrol Business": "https://www.moneycontrol.com/rss/business.xml",
    "Moneycontrol Latest": "https://www.moneycontrol.com/rss/latestnews.xml",
    "Business Standard Markets": "https://www.business-standard.com/rss/markets-106.rss",
    "Mint Markets": "https://www.livemint.com/rss/markets",
}
RED = ["fraud", "raid", "sebi order", "sebi bans", "penalty", "default", "downgrade", "resign", "probe", "pledge",
       "insolvency", "nclt", "forensic", "auditor quits", "income tax search", " ed ", "enforcement directorate",
       "loss widens", "profit falls", "profit declines", "plunges", "crashes", "cut to sell", "sell rating"]
GREEN = ["profit rises", "profit jumps", "record", "order win", "bags order", "upgrade", "buy rating", "beats",
         "surges", "rallies", "approval", "acquires", "wins contract"]


def fetch():
    rows = []
    for src, url in FEEDS.items():
        try:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
            root = ET.fromstring(r.content)
            for it in root.findall(".//item"):
                t = (it.findtext("title") or "").strip()
                if t:
                    rows.append({"source": src, "title": t, "link": it.findtext("link") or "",
                                 "published": pd.to_datetime(it.findtext("pubDate"), errors="coerce", utc=True)})
        except Exception as e:
            log.warning("news feed %s failed: %s", src, e)
    new = pd.DataFrame(rows)
    if STORE.exists():
        old = pd.read_csv(STORE, parse_dates=["published"])
        new = pd.concat([old, new]) if len(new) else old
    if len(new):
        new["published"] = pd.to_datetime(new["published"], utc=True, errors="coerce")
        new = new.drop_duplicates(subset=["title"]).sort_values("published")
        new = new[new["published"] >= pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=60)]
        new.to_csv(STORE, index=False)
    log.info("News items stored: %d", len(new))
    return new


def _keys(sym, name):
    keys = {sym.upper()}
    n = re.sub(r"\b(LIMITED|LTD|INDIA|THE|COMPANY|CORPORATION|INDUSTRIES|ENTERPRISES|OF)\b", " ", str(name).upper())
    words = [w for w in re.findall(r"[A-Z][A-Z&]+", n) if len(w) >= 3]
    if words:
        keys.add(" ".join(words[:2]) if len(words) > 1 and len(words[0]) < 5 else words[0])
    return keys


def news_for(sym, name="", days=5):
    if not STORE.exists():
        return []
    df = pd.read_csv(STORE, parse_dates=["published"])
    df = df[pd.to_datetime(df["published"], utc=True) >= pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days)]
    keys = _keys(sym, name)
    hits = []
    for _, r in df.iterrows():
        t = " " + str(r["title"]).upper() + " "
        if any(re.search(r"(?<![A-Z])" + re.escape(k) + r"(?![A-Z])", t) for k in keys):
            low = t.lower()
            tone = "RED FLAG" if any(w in low for w in RED) else "positive" if any(w in low for w in GREEN) else "neutral"
            hits.append({"title": r["title"], "source": r["source"], "tone": tone,
                         "published": str(pd.Timestamp(r["published"]).tz_convert("Asia/Kolkata").date())})
    return hits[-5:]


def line(sym, name=""):
    h = news_for(sym, name)
    if not h:
        return ""
    flag = any(x["tone"] == "RED FLAG" for x in h)
    top = h[-1]
    return (("⚠️ NEWS RED FLAG: " if flag else "News: ") + f"{top['title'][:110]} ({top['source']}, {top['published']})"
            + (f" +{len(h) - 1} more" if len(h) > 1 else ""))
