"""FastAPI dependency injection — DB sessions, Redis, model manager."""

from __future__ import annotations

import logging
from pathlib import Path

import joblib
import numpy as np
import redis

from config.settings import settings
from db.session import SessionLocal, get_db  # noqa: F401 — re-exported for route imports
from features.engineering import FeatureEngineer

logger = logging.getLogger(__name__)

ARTIFACTS_DIR = Path("artifacts")


# ── Redis ────────────────────────────────────────────────────

_redis_pool: redis.ConnectionPool | None = None


def _get_redis_pool() -> redis.ConnectionPool:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis.ConnectionPool.from_url(
            settings.redis_url, max_connections=settings.redis_max_connections
        )
    return _redis_pool


def get_redis() -> redis.Redis:
    return redis.Redis(connection_pool=_get_redis_pool())


# ── Model Manager (singleton) ─────────────────────────────────


class ModelManager:
    """Holds loaded ML models in memory for fast inference."""

    def __init__(self):
        self.demand_model = None
        self.waste_model = None
        self.model_version: str = "unknown"
        self._loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def load(self):
        demand_path = ARTIFACTS_DIR / f"{settings.demand_model_name}.joblib"
        waste_path = ARTIFACTS_DIR / f"{settings.waste_model_name}.joblib"

        if not demand_path.exists() or not waste_path.exists():
            logger.warning("Model artifacts not found in %s — run training first", ARTIFACTS_DIR)
            return

        self.demand_model = joblib.load(demand_path)
        self.waste_model = joblib.load(waste_path)
        self.model_version = "v1"
        self._loaded = True
        logger.info("Models loaded: demand=%s, waste=%s", demand_path, waste_path)

    def predict_demand(self, features: np.ndarray) -> dict[str, np.ndarray]:
        return self.demand_model.predict_with_intervals(features)

    def predict_waste_risk(self, features: np.ndarray) -> tuple[np.ndarray, list[str]]:
        proba = self.waste_model.predict_proba(features)
        tiers = self.waste_model.predict_tier(features)
        return proba, tiers

    @property
    def feature_columns(self) -> list[str]:
        return FeatureEngineer.FEATURE_COLUMNS


_model_manager: ModelManager | None = None


def get_model_manager() -> ModelManager:
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager()
    return _model_manager
