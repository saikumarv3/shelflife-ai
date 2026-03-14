"""Compute rolling MAPE from recent predictions for all stores.

Usage: uv run python -m scripts.run_feedback
"""

import logging

from config.settings import settings
from db.session import engine
from monitoring.feedback import check_mape_threshold, compute_rolling_mape
from monitoring.metrics import FORECAST_MAPE_7D

logger = logging.getLogger(__name__)


def run():
    for store_id in range(1, settings.num_stores + 1):
        mape = compute_rolling_mape(engine, store_id)
        if mape is not None:
            FORECAST_MAPE_7D.labels(store_id=str(store_id)).set(mape)
            degraded = check_mape_threshold(engine, store_id, settings.mape_alert_threshold)
            status = "DEGRADED" if degraded else "OK"
            logger.info("Store %d: 7d MAPE=%.2f%% [%s]", store_id, mape * 100, status)
        else:
            logger.info("Store %d: no prediction data with actuals", store_id)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    run()
