"""Run the retraining pipeline with validation gate.

Usage: uv run python -m scripts.run_retrain [--force]
"""

import argparse
import logging

from db.session import engine
from mlops.retrain import retrain_and_validate, should_retrain

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Force retrain even if no triggers")
    args = parser.parse_args()

    triggers = should_retrain(engine)
    logging.info("Retrain triggers: %s", triggers)

    if args.force or triggers["should_retrain"]:
        retrain_and_validate(engine)
    else:
        logging.info("No retraining needed. Use --force to override.")
