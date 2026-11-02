"""Optional Claude risk review (settings: claude_review: true).

Runs the Claude Code CLI headlessly ("claude -p") once per shortlisted stock (max 5-8
per night). Claude can only COMMENT; it never changes the rules-based list. Its verdict
(OK / CAUTION / AVOID) is saved in the journal so the weekly job can measure whether
the review ever improved results. If it doesn't, it remains an explainer only.
If the CLI is missing or a usage limit is hit, we stop for the night (back-off) and the
report simply has no review.
"""
import shutil
import subprocess
from datetime import date, timedelta

from .config import load_state, save_state, get_logger

log = get_logger()

PROMPT = """You are a cautious risk reviewer for a personal swing-trading research system (NSE India).
Do NOT give buy/sell advice. Review the RISKS of the following rules-based trade idea in at most 120 words,
using only the information provided (you may not browse). End with exactly one line:
VERDICT: OK  or  VERDICT: CAUTION  or  VERDICT: AVOID

{notes}
"""


def review(plans, max_stocks=6, timeout=180):
    st = load_state()
    if st.get("claude_backoff_until") and str(date.today()) < st["claude_backoff_until"]:
        return "Claude review paused until " + st["claude_backoff_until"] + " (usage limit back-off)"
    exe = shutil.which("claude")
    if not exe:
        return "Claude review is switched on but the 'claude' command was not found on this PC"
    done = 0
    for pl in plans[:max_stocks]:
        notes = "\n".join(f"{k}: {v}" for k, v in pl.items() if k not in ("chart",))
        try:
            r = subprocess.run([exe, "-p", PROMPT.format(notes=notes)], capture_output=True, text=True,
                               timeout=timeout, encoding="utf-8")
            txt = (r.stdout or "").strip()
            low = (txt + r.stderr).lower()
            if r.returncode != 0 or "limit" in low and "verdict" not in low:
                st["claude_backoff_until"] = str(date.today() + timedelta(days=1))
                save_state(st)
                log.warning("Claude review stopped (rc=%s): %s", r.returncode, (r.stderr or txt)[:200])
                break
            verdict = "UNKNOWN"
            for v in ("AVOID", "CAUTION", "OK"):
                if f"VERDICT: {v}" in txt.upper():
                    verdict = v
                    break
            pl["claude_review"] = txt.replace("\n", " ")[:900]
            pl["claude_verdict"] = verdict
            done += 1
        except Exception as e:
            log.warning("Claude review failed for %s: %s", pl["symbol"], e)
            break
    return f"Claude reviewed {done} stock(s)"
