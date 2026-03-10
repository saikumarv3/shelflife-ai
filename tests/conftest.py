"""Shared test fixtures — DB engine, API TestClient, sample data."""

import pytest
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from api.main import app
from config.settings import settings
from db.session import engine


@pytest.fixture(scope="session")
def db_engine():
    return engine


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


@pytest.fixture()
def auth_headers():
    return {"X-API-Key": settings.api_key, "Content-Type": "application/json"}


@pytest.fixture(scope="session")
def sample_sales_df():
    """Small DataFrame matching daily_sales schema for unit tests."""
    dates = pd.date_range("2024-01-01", periods=60, freq="D")
    rows = []
    for d in dates:
        for pid in [1, 2]:
            rows.append({
                "store_id": 1, "product_id": pid, "date": d,
                "quantity_sold": np.random.randint(5, 30),
                "revenue": round(np.random.uniform(20, 100), 2),
                "units_wasted": np.random.randint(0, 4),
                "units_donated": 0,
                "temperature_avg": round(np.random.uniform(30, 80), 1),
                "is_holiday": False, "is_promotion": False,
                "promotion_discount": 0.0, "day_of_week": d.dayofweek,
            })
    return pd.DataFrame(rows)


@pytest.fixture(scope="session")
def sample_products_df():
    return pd.DataFrame([
        {"product_id": 1, "category_id": 1, "unit_price": 3.99, "cost_price": 2.10, "shelf_life_days": 14},
        {"product_id": 2, "category_id": 2, "unit_price": 5.49, "cost_price": 3.20, "shelf_life_days": 7},
    ])


@pytest.fixture(scope="session")
def sample_inventory_df():
    dates = pd.date_range("2024-01-01", periods=60, freq="D")
    rows = []
    for d in dates:
        for pid in [1, 2]:
            rows.append({
                "store_id": 1, "product_id": pid, "date": d,
                "quantity_on_hand": np.random.randint(10, 60),
                "days_until_expiry": np.random.randint(1, 14),
            })
    return pd.DataFrame(rows)
