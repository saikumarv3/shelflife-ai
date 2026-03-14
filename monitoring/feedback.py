"""Feedback loop: record predictions and actuals, compute rolling accuracy."""

from __future__ import annotations

import logging
from datetime import date, timedelta

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def record_prediction(
    engine: Engine,
    store_id: int,
    product_id: int,
    pred_date: date,
    predicted_demand: float,
    confidence_lower: float,
    confidence_upper: float,
    waste_risk_score: float | None,
    waste_risk_tier: str | None,
    model_version: str,
) -> None:
    """Insert a prediction into the predictions table for later comparison."""
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO predictions
                    (store_id, product_id, date, predicted_demand,
                     confidence_lower, confidence_upper,
                     waste_risk_score, waste_risk_tier, model_version)
                VALUES (:sid, :pid, :dt, :pred, :cl, :cu, :wrs, :wrt, :mv)
                ON CONFLICT (store_id, product_id, date, model_version)
                DO UPDATE SET
                    predicted_demand = EXCLUDED.predicted_demand,
                    confidence_lower = EXCLUDED.confidence_lower,
                    confidence_upper = EXCLUDED.confidence_upper,
                    waste_risk_score = EXCLUDED.waste_risk_score,
                    waste_risk_tier  = EXCLUDED.waste_risk_tier
            """),
            {
                "sid": store_id,
                "pid": product_id,
                "dt": pred_date,
                "pred": predicted_demand,
                "cl": confidence_lower,
                "cu": confidence_upper,
                "wrs": waste_risk_score,
                "wrt": waste_risk_tier,
                "mv": model_version,
            },
        )


def record_actual(
    engine: Engine,
    store_id: int,
    product_id: int,
    actual_date: date,
    actual_sold: int,
) -> dict | None:
    """Update prediction with actual demand and compute forecast error."""
    with engine.begin() as conn:
        row = (
            conn.execute(
                text("""
                UPDATE predictions
                SET actual_demand = :actual,
                    forecast_error = (predicted_demand - :actual)
                                     / GREATEST(:actual, 1)
                WHERE store_id = :sid
                  AND product_id = :pid
                  AND date = :dt
                  AND actual_demand IS NULL
                RETURNING predicted_demand, forecast_error
            """),
                {
                    "sid": store_id,
                    "pid": product_id,
                    "dt": actual_date,
                    "actual": actual_sold,
                },
            )
            .mappings()
            .first()
        )

    if row:
        return {
            "predicted": float(row["predicted_demand"]),
            "actual": actual_sold,
            "error": float(row["forecast_error"]),
        }
    return None


def compute_rolling_mape(
    engine: Engine,
    store_id: int,
    window_days: int = 7,
    as_of: date | None = None,
) -> float | None:
    """Compute rolling MAPE for a store over the last N days."""
    ref_date = as_of or date.today()
    start_date = ref_date - timedelta(days=window_days)

    with engine.connect() as conn:
        row = (
            conn.execute(
                text("""
                SELECT AVG(ABS(forecast_error)) as mape
                FROM predictions
                WHERE store_id = :sid
                  AND actual_demand IS NOT NULL
                  AND date BETWEEN :start_dt AND :end_dt
            """),
                {"sid": store_id, "start_dt": start_date, "end_dt": ref_date},
            )
            .mappings()
            .first()
        )

    if row and row["mape"] is not None:
        return round(float(row["mape"]), 4)
    return None


def check_mape_threshold(
    engine: Engine,
    store_id: int,
    threshold: float = 0.20,
    window_days: int = 7,
) -> bool:
    """Returns True if rolling MAPE exceeds threshold (degraded)."""
    mape = compute_rolling_mape(engine, store_id, window_days)
    if mape is None:
        return False
    degraded = mape > threshold
    if degraded:
        logger.warning(
            "Store %d MAPE=%.2f%% exceeds threshold %.0f%%",
            store_id,
            mape * 100,
            threshold * 100,
        )
    return degraded
