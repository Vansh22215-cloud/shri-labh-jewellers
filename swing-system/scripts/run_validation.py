"""Full backtest + validation gate for the live strategy (or a named one): python scripts/run_validation.py [v1]"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from swing.config import load_settings
from swing import validation_report

if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else load_settings()["live_strategy"]
    res, _, table = validation_report.run(name)
    print(table.to_string())
    print("GATE PASSED" if res["gate"]["passed"] else "GATE FAILED")
    for c in res["gate"]["checks"]:
        print(("PASS " if c["passed"] else "FAIL ") + c["check"] + " | " + c["detail"])
