"""Batch predict all store-product pairs for today (or a given date).

Usage: uv run python -m scripts.run_daily_forecast [--date 2024-12-15]
"""

from __future__ import annotations

import argparse
import logging
from datetime import date

import joblib
import numpy as np
from sqlalchemy import text

from config.settings import settings
from db.session import engine
from features.engineering import FeatureEngineer
from mlops.model_registry import ARTIFACTS_DIR
from monitoring.feedback import record_prediction

logger = logging.getLogger(__name__)


def run(target_date: date | None = None):
    target_date = target_date or date.today()
    logger.info("Daily forecast for %s", target_date)

    demand_model = joblib.load(ARTIFACTS_DIR / f"{settings.demand_model_name}.joblib")
    waste_model = joblib.load(ARTIFACTS_DIR / f"{settings.waste_model_name}.joblib")
    model_version = "v1"

    with engine.connect() as conn:
        pairs = conn.execute(
            text("""
                SELECT DISTINCT store_id, product_id
                FROM feature_store
                ORDER BY store_id, product_id
            """)
        ).all()

    cols = FeatureEngineer.FEATURE_COLUMNS
    count = 0

    for store_id, product_id in pairs:
        with engine.connect() as conn:
            row = conn.execute(
                text("""
                    SELECT * FROM feature_store
                    WHERE store_id = :sid AND product_id = :pid
                    ORDER BY date DESC LIMIT 1
                """),
                {"sid": store_id, "pid": product_id},
            ).mappings().first()

        if row is None:
            continue

        vector = [float(row.get(c, 0) or 0) for c in cols]
        X = np.array([vector], dtype=np.float32)

        result = demand_model.predict_with_intervals(X)
        proba = waste_model.predict_proba(X)
        tier = waste_model.predict_tier(X)

        record_prediction(
            engine=engine,
            store_id=store_id,
            product_id=product_id,
            pred_date=target_date,
            predicted_demand=round(float(result["predicted_demand"][0]), 2),
            confidence_lower=round(float(result["confidence_lower"][0]), 2),
            confidence_upper=round(float(result["confidence_upper"][0]), 2),
            waste_risk_score=round(float(proba[0]), 4),
            waste_risk_tier=tier[0],
            model_version=model_version,
        )
        count += 1

    logger.info("Generated %d predictions for %s", count, target_date)
    return count


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=str, default=None)
    args = parser.parse_args()

    target = date.fromisoformat(args.date) if args.date else None
    run(target)
