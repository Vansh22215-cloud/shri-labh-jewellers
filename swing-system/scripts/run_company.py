"""Company of the Quarter (daemon job 'company', evenings): read ~150 companies' NSE filings; send the quarter's one
pick when it is due (first weekday of each quarter, 6:30 pm). Research, not a trade tip."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if __name__ == "__main__":
    from swing.config import on_github
    from swing.daemon import claim, retry_later
    if on_github() and not claim("company"):
        sys.exit(0)
    from swing import company_quarter
    r = company_quarter.run()
    print("company of the quarter:", r)
    if r == "Telegram failed":
        retry_later("company", minutes=15, max_tries=4)
    try:
        from swing.ci_save import save
        save("company of the quarter")
    except Exception as e:
        print("save failed:", e)
