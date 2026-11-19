"""ATLAS research budget manager + meta-intelligence (owner 19 Nov: "build ATLAS ... improve itself").
Every evening the Learner's open questions are put in ONE ranked list of what is worth testing next:
  - beliefs whose live check says "at risk" / "broken" (the most valuable: something we rely on may be wrong),
  - lessons the Learner found in live tips ("to research"),
  - big risers the system never detected (opportunity intelligence),
  - known blind spots (beliefs.json "unknowns").
Meta-intelligence: each idea is weighted by how often ideas of the same KIND have passed in the 77+ tested
(experiments.json), and ideas that repeat an already-failed test are pushed down with the test named, so research
time goes where passes are likely. Budget: at most 2 pre-registered tests a week; nothing here changes a live tip.
Output: journal/research_queue.md (market ideas only, no money or holdings)."""
import json

import pandas as pd

from .config import ROOT, get_logger

log = get_logger()
VAL = ROOT.parent / "vantage-ai" / "validation"
OUT = ROOT / "journal" / "research_queue.md"
LEADS_F = ROOT / "strategies" / "why_leads.json"
BUDGET = 2
# already-tested ideas by the situation a live lesson is about (so a lesson is not retested blindly)
TESTED_BY_SITUATION = {   # LAB-1 = the auto-lab tested every bucket of these facts on 13 years (AUTO_LAB_RESULTS.md)
    "market": ["R1-F1", "R6-G", "X-market-break", "LAB-1"], "market_mood": ["R8-6", "R6-G", "X-market-break", "LAB-1"],
    "day_type": ["R1-F1", "R6-G", "R8-6", "LAB-1"], "liquidity": ["R1-U", "R23", "LAB-1"],
    "mistake": ["R1-E1", "R20-G1", "R20-G2"], "weekday": ["LAB-1"], "from_52w_high": ["FP", "LAB-1"],
    "results_week": ["R2-R4", "LAB-1"],
}
FAMILY_OF = {"why-lead": "discovery", "belief": "adversarial", "lesson": "filter", "mistake": "exit", "missed": "discovery", "unknown": "exploration"}
VALUE = {"broken": 4.0, "at risk": 3.0, "strong": 2.0, "medium": 1.0, "weak": 0.5, "missed": 2.0, "unknown": 1.0}


def _score_verdict(v):
    v = str(v).lower()
    if v.startswith("pass") or v.startswith("passed"):
        return 1.0
    if "near miss" in v or "mixed" in v or "fragile" in v:
        return 0.5
    return 0.0


def family_rates(X=None):
    """-> {family: (tested, pass score, smoothed rate)}; smoothed = (passes + 1) / (tested + 2)."""
    if X is None:
        try:
            X = json.loads((VAL / "experiments.json").read_text())["experiments"]
        except Exception:
            return {}
    out = {}
    for e in X:
        if "not worth" in str(e.get("verdict", "")):
            continue                                   # explorations that found nothing to test
        f = e.get("family", "other")
        n, p = out.get(f, (0, 0.0))[:2]
        out[f] = (n + 1, p + _score_verdict(e.get("verdict")))
    return {f: (n, p, (p + 1) / (n + 2)) for f, (n, p) in out.items()}


def candidates(checks=(), queue=None, missed_n=0, unknowns=()):
    C = []
    for c in checks:                     # (id, belief, level, status, detail, wrong_if)
        if c[3] in ("at risk", "broken"):
            C.append({"kind": "belief", "idea": f"{c[0]}: is \"{c[1]}\" still true? Live: {c[3]} ({c[4]})",
                      "value": VALUE[c[3]], "tested": ""})
    if queue is not None and len(queue):
        for r in queue[queue["status"].astype(str).str.startswith("to research")].itertuples():
            kind = "mistake" if r.situation == "mistake" else "lesson"
            done = TESTED_BY_SITUATION.get(str(r.situation), [])
            C.append({"kind": kind, "idea": str(r.lesson), "value": VALUE.get(str(r.evidence), 0.5),
                      "tested": ", ".join(done)})
    if missed_n >= 10:
        C.append({"kind": "missed", "idea": f"{missed_n} of the top 20 risers were never detected: is there a testable "
                  "pattern in them (most started far from their 52-week high)?", "value": VALUE["missed"], "tested": "FP, X-missed"})
    try:   # why-engine leads: live surprises confirmed on 13 years -> the weekly research tests them
        L = json.loads(LEADS_F.read_text())["leads"]
    except Exception:
        L = []
    for x in L:
        C.append({"kind": "why-lead", "idea": f"Why-engine: {x['col']} {x['side']} ({x['setup']}) - {x['verdict']}; seen in "
                  f"{', '.join(x['seen_in'][:4])} (tested every week as a rule)", "value": 2.0, "tested": ""})
    for u in unknowns:
        C.append({"kind": "unknown", "idea": f"Blind spot: {u}", "value": VALUE["unknown"], "tested": ""})
    return C


def rank(C, rates):
    base = sum(r[2] for r in rates.values()) / len(rates) if rates else 0.2
    for c in C:
        fam = FAMILY_OF[c["kind"]]
        c["family"] = fam
        c["prior"] = rates.get(fam, (0, 0, base))[2]
        c["score"] = c["value"] * c["prior"] * (0.3 if c["tested"] else 1.0)
    return sorted(C, key=lambda c: -c["score"])


def write(C, rates, today=None):
    today = today or pd.Timestamp.now(tz="Asia/Kolkata").strftime("%d %b %Y")
    L = [f"# Research queue ({today})", "",
         "What is worth testing next, ranked. Score = value of the question x how often ideas of the same kind passed "
         f"before (x 0.3 when it repeats a failed test). Budget: the top {BUDGET} a week, each pre-registered and tested on "
         "all years before any live change (owner's yes needed).", "",
         "## Which kinds of ideas pass (meta-intelligence)", "", "| Kind | Tested | Passed (near miss = half) | Chance used |",
         "|---|---|---|---|"]
    for f, (n, p, r) in sorted(rates.items(), key=lambda x: -x[1][2]):
        L.append(f"| {f} | {n} | {p:g} | {r * 100:.0f}% |")
    L += ["", "## Ranked queue", ""]
    if not C:
        L.append("- Nothing new: no belief at risk, no new lesson. Live record keeps building.")
    for i, c in enumerate(C, 1):
        tag = "THIS WEEK" if i <= BUDGET else "later"
        L.append(f"{i}. [{tag}] ({c['kind']}, score {c['score']:.2f}) {c['idea']}"
                 + (f" - already tested: {c['tested']}" if c["tested"] else ""))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(L) + "\n")
    return L


def build(checks=(), missed_n=0, today=None):
    try:
        q = pd.read_csv(ROOT / "journal" / "learning_queue.csv", dtype=str)
    except Exception:
        q = None
    try:
        unk = json.loads((VAL / "beliefs.json").read_text()).get("unknowns", [])
    except Exception:
        unk = []
    rates = family_rates()
    try:   # an idea already explored and closed is not queued again
        done = {e["id"] for e in json.loads((VAL / "experiments.json").read_text())["experiments"]}
    except Exception:
        done = set()
    C = rank(candidates(checks, q, 0 if "X-missed" in done else missed_n, unk), rates)
    write(C, rates, today)
    log.info("Research queue: %d ideas ranked", len(C))
    return C
