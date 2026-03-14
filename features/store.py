"""
Feature store — persist and retrieve computed features from PostgreSQL.
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

BOOL_COLUMNS = {"is_weekend", "is_month_start", "is_month_end", "is_holiday", "is_promotion"}


def save_features(df: pd.DataFrame, engine: Engine, if_exists: str = "replace") -> int:
    """Write feature DataFrame to the feature_store table. Returns row count."""
    cols_to_save = [
        "store_id",
        "product_id",
        "date",
        *[
            c
            for c in df.columns
            if c
            not in (
                "store_id",
                "product_id",
                "date",
                "quantity_sold",
                "revenue",
                "units_wasted",
                "units_donated",
                "sale_id",
                "created_at",
                "quantity_on_hand",
                "days_until_expiry",
                "snapshot_id",
                "reorder_point",
                "last_delivery_date",
                "feature_id",
            )
        ],
    ]
    cols_to_save = [c for c in cols_to_save if c in df.columns]
    subset = df[cols_to_save].copy()

    for col in BOOL_COLUMNS:
        if col in subset.columns:
            subset[col] = subset[col].astype(bool)

    if if_exists == "replace":
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM feature_store"))

    subset.to_sql(
        "feature_store", engine, if_exists="append", index=False, method="multi", chunksize=2000
    )
    return len(subset)


def load_features(
    engine: Engine,
    store_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> pd.DataFrame:
    """Load features from the feature_store table with optional filters."""
    query = "SELECT * FROM feature_store WHERE 1=1"
    params: dict = {}
    if store_id is not None:
        query += " AND store_id = :store_id"
        params["store_id"] = store_id
    if date_from is not None:
        query += " AND date >= :date_from"
        params["date_from"] = date_from
    if date_to is not None:
        query += " AND date <= :date_to"
        params["date_to"] = date_to
    query += " ORDER BY store_id, product_id, date"

    return pd.read_sql(text(query), engine, params=params)
