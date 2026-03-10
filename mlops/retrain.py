"""Automated retraining pipeline with validation gate.

Only promotes a new model if it outperforms the current production model
on a held-out validation set. Otherwise keeps the existing model and logs an alert.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta, timezone

import joblib
import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from config.settings import settings
from db.session import engine as default_engine
from features.engineering import FeatureEngineer
from models.demand_forecast import DemandForecaster
from models.waste_risk import WasteRiskClassifier
from models.evaluation import evaluate_forecast, evaluate_waste_risk
from mlops.model_registry import ModelRegistry, ARTIFACTS_DIR
from monitoring.metrics import RETRAIN_RUNS

logger = logging.getLogger(__name__)


def should_retrain(engine: Engine) -> dict:
    """Check if retraining triggers are met. Returns dict with trigger details."""
    triggers = {"schedule": False, "drift": False, "mape_degraded": False}

    with engine.connect() as conn:
        last_alert = conn.execute(
            text("""
                SELECT created_at FROM alerts
                WHERE alert_type = 'model_promoted'
                ORDER BY created_at DESC LIMIT 1
            """)
        ).mappings().first()

    if last_alert:
        days_since = (datetime.now(timezone.utc).replace(tzinfo=None) - last_alert["created_at"]).days
        triggers["schedule"] = days_since >= settings.retrain_schedule_days
    else:
        triggers["schedule"] = True

    with engine.connect() as conn:
        drift_alert = conn.execute(
            text("""
                SELECT alert_id FROM alerts
                WHERE alert_type = 'data_drift' AND acknowledged = false
                ORDER BY created_at DESC LIMIT 1
            """)
        ).mappings().first()
    triggers["drift"] = drift_alert is not None

    from monitoring.feedback import check_mape_threshold
    for store_id in range(1, settings.num_stores + 1):
        if check_mape_threshold(engine, store_id, settings.mape_alert_threshold):
            triggers["mape_degraded"] = True
            break

    triggers["should_retrain"] = any([triggers["schedule"], triggers["drift"], triggers["mape_degraded"]])
    return triggers


def retrain_and_validate(engine: Engine | None = None) -> dict:
    """Full retrain cycle: train new model, compare to current, promote if better."""
    engine = engine or default_engine
    start = time.time()
    logger.info("=" * 50)
    logger.info("RETRAINING PIPELINE — %s", datetime.now().isoformat())
    logger.info("=" * 50)

    with engine.connect() as conn:
        sales_df = pd.read_sql(text("SELECT * FROM daily_sales ORDER BY store_id, product_id, date"), conn)
        products_df = pd.read_sql(text("SELECT * FROM products"), conn)
        inventory_df = pd.read_sql(text("SELECT * FROM inventory_snapshots ORDER BY store_id, product_id, date"), conn)
        stores_df = pd.read_sql(text("SELECT * FROM stores"), conn)

    logger.info("Data: %d sales, %d products", len(sales_df), len(products_df))

    fe = FeatureEngineer(sales_df, products_df, inventory_df, stores_df)
    feat_df = fe.build()

    feature_cols = FeatureEngineer.FEATURE_COLUMNS
    feat_df["date"] = pd.to_datetime(feat_df["date"])

    val_start = feat_df["date"].max() - timedelta(days=45)
    test_start = feat_df["date"].max() - timedelta(days=15)

    train_mask = feat_df["date"] < val_start
    val_mask = (feat_df["date"] >= val_start) & (feat_df["date"] < test_start)
    test_mask = feat_df["date"] >= test_start

    X_train = feat_df.loc[train_mask, feature_cols].values.astype(np.float32)
    y_train = feat_df.loc[train_mask, "quantity_sold"].values.astype(np.float32)
    X_val = feat_df.loc[val_mask, feature_cols].values.astype(np.float32)
    y_val = feat_df.loc[val_mask, "quantity_sold"].values.astype(np.float32)
    X_test = feat_df.loc[test_mask, feature_cols].values.astype(np.float32)
    y_test = feat_df.loc[test_mask, "quantity_sold"].values.astype(np.float32)

    logger.info("Split: train=%d, val=%d, test=%d", len(X_train), len(X_val), len(X_test))

    # Train new demand model
    new_forecaster = DemandForecaster()
    new_forecaster.train(X_train, y_train, X_val, y_val)
    new_pred = new_forecaster.predict(X_test)

    test_meta = feat_df.loc[test_mask, ["unit_price", "cost_price"]].copy()
    new_metrics = evaluate_forecast(
        y_test, new_pred,
        test_meta["unit_price"].values.astype(float),
        test_meta["cost_price"].values.astype(float),
    )
    logger.info("New model: RMSE=%.2f, MAPE=%.4f, R²=%.4f",
                 new_metrics["rmse"], new_metrics["mape"], new_metrics["r2"])

    # Train new waste model
    waste_labels = WasteRiskClassifier.build_labels(sales_df)
    y_waste_test = waste_labels.loc[test_mask].values

    new_classifier = WasteRiskClassifier()
    new_classifier.train(X_train, waste_labels.loc[train_mask].values, X_val, waste_labels.loc[val_mask].values)
    new_waste_proba = new_classifier.predict_proba(X_test)
    new_waste_metrics = evaluate_waste_risk(y_waste_test, new_waste_proba)

    # Compare with current production model
    promoted = False
    try:
        current_demand = joblib.load(ARTIFACTS_DIR / f"{settings.demand_model_name}.joblib")
        current_pred = current_demand.predict(X_test)
        current_metrics = evaluate_forecast(
            y_test, current_pred,
            test_meta["unit_price"].values.astype(float),
            test_meta["cost_price"].values.astype(float),
        )
        logger.info("Current model: RMSE=%.2f, MAPE=%.4f, R²=%.4f",
                     current_metrics["rmse"], current_metrics["mape"], current_metrics["r2"])

        if new_metrics["mape"] < current_metrics["mape"]:
            promoted = True
            improvement = (current_metrics["mape"] - new_metrics["mape"]) / current_metrics["mape"] * 100
            logger.info("NEW MODEL WINS — MAPE improved by %.1f%%", improvement)
        else:
            logger.info("Current model is better or equal — keeping existing")
    except FileNotFoundError:
        promoted = True
        logger.info("No existing model found — promoting new model")
        current_metrics = {}

    if promoted:
        registry = ModelRegistry()
        registry.save_model(new_forecaster, settings.demand_model_name)
        registry.save_model(new_classifier, settings.waste_model_name)
        RETRAIN_RUNS.labels(outcome="promoted").inc()

        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO alerts (alert_type, severity, message, metadata_json)
                    VALUES ('model_promoted', 'info', :msg, :meta)
                """),
                {
                    "msg": f"New model promoted: MAPE={new_metrics['mape']:.4f}",
                    "meta": json.dumps({"demand": new_metrics, "waste": new_waste_metrics}),
                },
            )
    else:
        RETRAIN_RUNS.labels(outcome="kept_current").inc()
        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO alerts (alert_type, severity, message, metadata_json)
                    VALUES ('retrain_completed', 'info', :msg, :meta)
                """),
                {
                    "msg": "Retrain completed but current model retained",
                    "meta": json.dumps({"new": new_metrics, "current": current_metrics}),
                },
            )

    elapsed = time.time() - start
    summary = {
        "promoted": promoted,
        "new_demand_metrics": new_metrics,
        "new_waste_metrics": new_waste_metrics,
        "current_demand_metrics": current_metrics if not promoted else None,
        "elapsed_seconds": round(elapsed, 1),
    }

    print("\n" + "=" * 50)
    print("  RETRAINING SUMMARY")
    print("=" * 50)
    print(f"  Outcome:  {'PROMOTED' if promoted else 'KEPT CURRENT'}")
    print(f"  New MAPE: {new_metrics['mape']:.4f}")
    print(f"  New RMSE: {new_metrics['rmse']:.2f}")
    print(f"  Waste F1: {new_waste_metrics['f1']:.4f}")
    print(f"  Elapsed:  {elapsed:.1f}s")
    print("=" * 50)

    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    triggers = should_retrain(default_engine)
    logger.info("Retrain triggers: %s", triggers)

    if triggers["should_retrain"]:
        retrain_and_validate()
    else:
        logger.info("No retraining needed at this time")
