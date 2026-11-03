"""Company of the day: refresh ~120 companies' statements and send the best-scoring one to Telegram."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from swing.company_research import run

if __name__ == "__main__":
    print(run(send="--dry" not in sys.argv, batch=int(sys.argv[sys.argv.index("--batch") + 1]) if "--batch" in sys.argv else 120))
