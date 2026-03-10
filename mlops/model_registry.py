"""
Model registry — load/save models via MLflow or local file fallback.

Supports:
- Saving XGBoost/LightGBM models with MLflow
- Loading from MLflow model registry by name + stage
- Local joblib fallback when MLflow is unavailable
"""

from __future__ import annotations

import logging
from pathlib import Path

import joblib
import mlflow

from config.settings import settings

logger = logging.getLogger(__name__)

ARTIFACTS_DIR = Path("artifacts")
ARTIFACTS_DIR.mkdir(exist_ok=True)


class ModelRegistry:
    """Thin wrapper around MLflow model registry with local fallback."""

    def __init__(self, tracking_uri: str | None = None):
        self.tracking_uri = tracking_uri or settings.mlflow_tracking_uri
        mlflow.set_tracking_uri(self.tracking_uri)

    def save_model(self, model, model_name: str, run_id: str | None = None) -> str:
        """Save model to MLflow + local joblib backup. Returns model URI."""
        local_path = ARTIFACTS_DIR / f"{model_name}.joblib"
        joblib.dump(model, local_path)
        logger.info("Saved local backup: %s", local_path)

        try:
            if run_id:
                artifact_path = model_name.replace("-", "_")
                mlflow.sklearn.log_model(model, artifact_path)
                model_uri = f"runs:/{run_id}/{artifact_path}"
                logger.info("Logged model to MLflow: %s", model_uri)
                return model_uri
        except Exception:
            logger.warning("MLflow save failed, using local fallback", exc_info=True)

        return str(local_path)

    def load_model(self, model_name: str, stage: str = "Production"):
        """Load from MLflow registry. Falls back to local joblib."""
        try:
            model_uri = f"models:/{model_name}/{stage}"
            model = mlflow.sklearn.load_model(model_uri)
            logger.info("Loaded from MLflow: %s", model_uri)
            return model
        except Exception:
            logger.info("MLflow load failed, trying local fallback")

        local_path = ARTIFACTS_DIR / f"{model_name}.joblib"
        if local_path.exists():
            model = joblib.load(local_path)
            logger.info("Loaded from local: %s", local_path)
            return model

        raise FileNotFoundError(f"No model found for '{model_name}' (tried MLflow + local)")

    def register_model(self, run_id: str, model_name: str) -> str:
        """Register a logged model in MLflow model registry."""
        artifact_path = model_name.replace("-", "_")
        model_uri = f"runs:/{run_id}/{artifact_path}"
        result = mlflow.register_model(model_uri, model_name)
        logger.info("Registered %s version %s", model_name, result.version)
        return result.version
