"""
End-to-end training pipeline for ShelfLife AI.

Orchestrates:
1. Data extraction from PostgreSQL
2. Feature engineering
3. Train/val/test split (time-based)
4. Demand forecast training + evaluation
5. Waste risk classifier training + evaluation
6. Baseline comparison
7. MLflow experiment tracking
8. Model saving via ModelRegistry
"""

from __future__ import annotations

import logging
import time
from datetime import datetime

import mlflow
import numpy as np
import pandas as pd
from sqlalchemy import text

from config.settings import settings
from db.session import engine
from features.engineering import FeatureEngineer
from features.store import save_features
from models.demand_forecast import DemandForecaster
from models.waste_risk import WasteRiskClassifier
from models.evaluation import (
    evaluate_forecast,
    evaluate_waste_risk,
    compute_baselines,
)
from mlops.model_registry import ModelRegistry

logger = logging.getLogger(__name__)


class TrainPipeline:
    """Full training pipeline: extract → features → split → train → evaluate → register."""

    TRAIN_CUTOFF = "2024-10-01"
    VAL_CUTOFF = "2024-11-15"

    def __init__(self):
        self.registry = ModelRegistry()

    def run(self) -> dict:
        """Execute the full pipeline. Returns summary metrics."""
        start = time.time()
        logger.info("=" * 60)
        logger.info("TRAINING PIPELINE START — %s", datetime.now().isoformat())
        logger.info("=" * 60)

        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        mlflow.set_experiment("shelflife-training")

        with mlflow.start_run(run_name=f"train_{datetime.now():%Y%m%d_%H%M%S}") as run:
            run_id = run.info.run_id

            # Step 1: Extract
            sales_df, products_df, inventory_df, stores_df = self._extract_data()

            # Step 2: Feature engineering
            feat_df = self._build_features(sales_df, products_df, inventory_df, stores_df)

            # Step 3: Time-based split
            X_train, y_train, X_val, y_val, X_test, y_test, test_meta = self._split(feat_df)

            # Step 4: Demand forecast
            demand_metrics = self._train_demand(X_train, y_train, X_val, y_val, X_test, y_test, test_meta, run_id)

            # Step 5: Waste risk
            waste_labels = WasteRiskClassifier.build_labels(sales_df)
            waste_metrics = self._train_waste_risk(feat_df, waste_labels, X_train, X_val, X_test, run_id)

            # Step 6: Baselines
            baselines = self._compute_baselines(feat_df, y_test, X_test)

            # Step 7: Log summary
            elapsed = time.time() - start
            summary = {
                "run_id": run_id,
                "elapsed_seconds": round(elapsed, 1),
                "demand": demand_metrics,
                "waste_risk": waste_metrics,
                "baselines": baselines,
                "train_size": len(X_train),
                "val_size": len(X_val),
                "test_size": len(X_test),
            }
            mlflow.log_metrics({
                "pipeline_elapsed_s": elapsed,
                "train_size": len(X_train),
                "val_size": len(X_val),
                "test_size": len(X_test),
            })

        logger.info("PIPELINE COMPLETE in %.1fs — run_id=%s", elapsed, run_id)
        self._print_summary(summary)
        return summary

    # ── Step 1: Extract ────────────────────────────────────────

    def _extract_data(self):
        logger.info("[1/7] Extracting data from PostgreSQL...")
        with engine.connect() as conn:
            sales_df = pd.read_sql(text("SELECT * FROM daily_sales ORDER BY store_id, product_id, date"), conn)
            products_df = pd.read_sql(text("SELECT * FROM products"), conn)
            inventory_df = pd.read_sql(text("SELECT * FROM inventory_snapshots ORDER BY store_id, product_id, date"), conn)
            stores_df = pd.read_sql(text("SELECT * FROM stores"), conn)

        logger.info("  Sales: %d rows | Products: %d | Inventory: %d | Stores: %d",
                     len(sales_df), len(products_df), len(inventory_df), len(stores_df))
        return sales_df, products_df, inventory_df, stores_df

    # ── Step 2: Features ───────────────────────────────────────

    def _build_features(self, sales_df, products_df, inventory_df, stores_df) -> pd.DataFrame:
        logger.info("[2/7] Engineering %d features...", len(FeatureEngineer.FEATURE_COLUMNS))
        fe = FeatureEngineer(sales_df, products_df, inventory_df, stores_df)
        feat_df = fe.build()

        saved = save_features(feat_df, engine, if_exists="replace")
        logger.info("  Feature matrix: %d rows × %d cols → saved %d to feature_store",
                     len(feat_df), len(feat_df.columns), saved)
        mlflow.log_metric("feature_count", len(FeatureEngineer.FEATURE_COLUMNS))
        mlflow.log_metric("feature_rows", len(feat_df))
        return feat_df

    # ── Step 3: Split ──────────────────────────────────────────

    def _split(self, feat_df: pd.DataFrame):
        logger.info("[3/7] Time-based split: train < %s | val < %s | test = rest",
                     self.TRAIN_CUTOFF, self.VAL_CUTOFF)

        feature_cols = FeatureEngineer.FEATURE_COLUMNS
        target = "quantity_sold"

        feat_df["date"] = pd.to_datetime(feat_df["date"])
        train_mask = feat_df["date"] < self.TRAIN_CUTOFF
        val_mask = (feat_df["date"] >= self.TRAIN_CUTOFF) & (feat_df["date"] < self.VAL_CUTOFF)
        test_mask = feat_df["date"] >= self.VAL_CUTOFF

        X_train = feat_df.loc[train_mask, feature_cols].values.astype(np.float32)
        y_train = feat_df.loc[train_mask, target].values.astype(np.float32)

        X_val = feat_df.loc[val_mask, feature_cols].values.astype(np.float32)
        y_val = feat_df.loc[val_mask, target].values.astype(np.float32)

        X_test = feat_df.loc[test_mask, feature_cols].values.astype(np.float32)
        y_test = feat_df.loc[test_mask, target].values.astype(np.float32)

        test_meta = feat_df.loc[test_mask, ["store_id", "product_id", "date", "unit_price", "cost_price"]].copy()

        logger.info("  Train: %d | Val: %d | Test: %d", len(X_train), len(X_val), len(X_test))
        return X_train, y_train, X_val, y_val, X_test, y_test, test_meta

    # ── Step 4: Demand forecast ─────────────────────────────────

    def _train_demand(self, X_train, y_train, X_val, y_val, X_test, y_test, test_meta, run_id) -> dict:
        logger.info("[4/7] Training demand forecast (XGBoost + LightGBM ensemble)...")
        forecaster = DemandForecaster()
        forecaster.train(X_train, y_train, X_val, y_val)

        y_pred = forecaster.predict(X_test)

        unit_prices = test_meta["unit_price"].values.astype(float)
        cost_prices = test_meta["cost_price"].values.astype(float)
        metrics = evaluate_forecast(y_test, y_pred, unit_prices, cost_prices)

        for k, v in metrics.items():
            mlflow.log_metric(f"demand_{k}", v)
        logger.info("  RMSE=%.2f | MAE=%.2f | MAPE=%.4f | R²=%.4f | BizCost=$%.2f",
                     metrics["rmse"], metrics["mae"], metrics["mape"], metrics["r2"],
                     metrics.get("business_cost", 0))

        top_feats = forecaster.get_feature_importance(FeatureEngineer.FEATURE_COLUMNS)
        top5 = list(top_feats.items())[:5]
        logger.info("  Top 5 features: %s", top5)

        self.registry.save_model(forecaster, settings.demand_model_name, run_id)
        return metrics

    # ── Step 5: Waste risk ──────────────────────────────────────

    def _train_waste_risk(self, feat_df, waste_labels, X_train, X_val, X_test, run_id) -> dict:
        logger.info("[5/7] Training waste risk classifier...")
        feature_cols = FeatureEngineer.FEATURE_COLUMNS
        feat_df["date"] = pd.to_datetime(feat_df["date"])

        train_mask = feat_df["date"] < self.TRAIN_CUTOFF
        val_mask = (feat_df["date"] >= self.TRAIN_CUTOFF) & (feat_df["date"] < self.VAL_CUTOFF)
        test_mask = feat_df["date"] >= self.VAL_CUTOFF

        y_waste_train = waste_labels.loc[train_mask].values
        y_waste_val = waste_labels.loc[val_mask].values
        y_waste_test = waste_labels.loc[test_mask].values

        classifier = WasteRiskClassifier()
        train_info = classifier.train(X_train, y_waste_train, X_val, y_waste_val)
        logger.info("  Pos rate: %.2f%% | scale_pos_weight: %.2f",
                     train_info["pos_rate"] * 100, train_info["scale_pos_weight"])

        y_proba = classifier.predict_proba(X_test)
        metrics = evaluate_waste_risk(y_waste_test, y_proba)

        for k, v in metrics.items():
            mlflow.log_metric(f"waste_{k}", v)
        logger.info("  Precision=%.4f | Recall=%.4f | F1=%.4f | AUC-ROC=%.4f",
                     metrics["precision"], metrics["recall"], metrics["f1"], metrics["auc_roc"])

        self.registry.save_model(classifier, settings.waste_model_name, run_id)
        return metrics

    # ── Step 6: Baselines ───────────────────────────────────────

    def _compute_baselines(self, feat_df, y_test, X_test) -> dict:
        logger.info("[6/7] Computing baseline models...")
        feature_cols = FeatureEngineer.FEATURE_COLUMNS
        lag1_idx = feature_cols.index("sales_lag_1d")
        lag7_idx = feature_cols.index("sales_lag_7d")

        y_lag1 = X_test[:, lag1_idx]
        y_lag7 = X_test[:, lag7_idx]

        baselines = compute_baselines(y_test, y_lag1, y_lag7)
        for k, v in baselines.items():
            mlflow.log_metric(k, v)

        for name, val in baselines.items():
            logger.info("  %s = %.4f", name, val)
        return baselines

    # ── Summary ─────────────────────────────────────────────────

    def _print_summary(self, summary: dict):
        print("\n" + "=" * 60)
        print("  SHELFLIFE AI — TRAINING SUMMARY")
        print("=" * 60)
        print(f"  Run ID:        {summary['run_id'][:12]}...")
        print(f"  Elapsed:       {summary['elapsed_seconds']}s")
        print(f"  Data split:    {summary['train_size']} / {summary['val_size']} / {summary['test_size']}")
        print()
        print("  DEMAND FORECAST:")
        for k, v in summary["demand"].items():
            print(f"    {k:20s} = {v:.4f}")
        print()
        print("  WASTE RISK CLASSIFIER:")
        for k, v in summary["waste_risk"].items():
            print(f"    {k:20s} = {v:.4f}")
        print()
        print("  BASELINES:")
        for k, v in summary["baselines"].items():
            print(f"    {k:20s} = {v:.4f}")
        print("=" * 60)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    pipeline = TrainPipeline()
    pipeline.run()
