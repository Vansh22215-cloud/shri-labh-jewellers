"""Walk-forward search over ~550 strategy variants (20-90 minutes). Writes validation/search_latest.json."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from swing.search import run_search

if __name__ == "__main__":
    out = run_search()
    print(json.dumps({k: out[k] for k in ("passed", "checks", "picks", "holdout", "chain_cagr_pct",
                                          "niftybees_cagr_pct_wf", "cherry_picked_top10",
                                          "share_variants_beating_niftybees_cagr")}, indent=1, default=str))
