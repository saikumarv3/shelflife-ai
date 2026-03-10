"""Run drift detection on critical features.

Usage: uv run python -m scripts.run_drift_check
"""

import logging

from db.session import engine
from mlops.drift_detection import run_drift_check

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    results = run_drift_check(engine)

    drifted = [f for f, r in results.items() if r.get("drifted")]
    if drifted:
        print(f"\nWARNING: Drift detected in {len(drifted)} features: {', '.join(drifted)}")
    else:
        print("\nAll features stable. No drift detected.")
