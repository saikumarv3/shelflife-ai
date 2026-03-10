"""
Central configuration — single source of truth for every tunable value.

All other modules import from here:
    from config.settings import settings
"""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────────────
    database_url: str = "postgresql://shelflife:shelflife@localhost:5432/shelflife"
    test_database_url: str = "postgresql://shelflife:shelflife@localhost:5432/shelflife_test"

    # ── Redis ─────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    test_redis_url: str = "redis://localhost:6379/1"

    # ── MLflow ────────────────────────────────────────────────
    mlflow_tracking_uri: str = "http://localhost:5001"

    # ── API ───────────────────────────────────────────────────
    api_key: str = "sk_shelflife_dev_abc123"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 1
    log_level: str = "INFO"

    # ── Models ────────────────────────────────────────────────
    demand_model_name: str = "shelflife-demand-forecast"
    waste_model_name: str = "shelflife-waste-risk"
    model_stage: str = "Production"

    # ── Cache TTLs (seconds) ──────────────────────────────────
    cache_ttl_same_day: int = 3600
    cache_ttl_future: int = 21600

    # ── Security ──────────────────────────────────────────────
    rate_limit_per_minute: int = 100
    cors_origins: str = "http://localhost:8501"

    # ── MLOps thresholds ──────────────────────────────────────
    retrain_schedule_days: int = 7
    drift_psi_threshold: float = 0.2
    mape_alert_threshold: float = 0.20
    mape_absolute_cap: float = 0.20
    business_cost_weight_over: float = 1.0
    business_cost_weight_under: float = 1.0

    # ── Synthetic data generator ──────────────────────────────
    num_stores: int = 3
    num_products: int = 50
    num_categories: int = 8
    data_start_date: str = "2024-01-01"
    data_end_date: str = "2024-12-31"
    random_seed: int = 42

    # ── Connection pooling ────────────────────────────────────
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800
    redis_max_connections: int = 20

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
