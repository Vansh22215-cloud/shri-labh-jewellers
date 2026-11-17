"""Monthly basket of the 20 strongest NSE stocks (daemon job 'basket', weekday evenings; sends once a month)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from swing.config import redact  # noqa: E402
from swing import basket  # noqa: E402

if __name__ == "__main__":
    try:
        print("basket:", basket.run(force="--force" in sys.argv))
    except Exception as e:
        print("basket failed:", redact(f"{type(e).__name__}: {e}"))
        raise
