"""
Feature engineering pipeline for ShelfLife AI.

Transforms raw sales, product, and inventory data into a 35+ column feature
matrix suitable for XGBoost / LightGBM training and inference.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Map store type strings to integers for model consumption
STORE_TYPE_MAP = {"urban": 0, "suburban": 1, "rural": 2}


class FeatureEngineer:
    """Builds the full feature matrix from raw DataFrames."""

    FEATURE_COLUMNS: list[str] = [
        # Temporal (7)
        "day_of_week",
        "day_of_month",
        "week_of_year",
        "month",
        "is_weekend",
        "is_month_start",
        "is_month_end",
        # Lags (7)
        "sales_lag_1d",
        "sales_lag_7d",
        "sales_lag_14d",
        "sales_lag_28d",
        "waste_lag_1d",
        "waste_lag_7d",
        "inventory_lag_1d",
        # Rolling (8)
        "sales_rolling_7d_mean",
        "sales_rolling_7d_std",
        "sales_rolling_14d_mean",
        "sales_rolling_28d_mean",
        "waste_rolling_7d_sum",
        "waste_rolling_7d_rate",
        "revenue_rolling_7d",
        "sales_rolling_7d_median",
        # Product (5)
        "unit_price",
        "cost_price",
        "shelf_life_days",
        "margin_pct",
        "category_encoded",
        # Contextual (5)
        "is_holiday",
        "is_promotion",
        "promotion_discount",
        "temperature_avg",
        "store_type_encoded",
        # Derived (3)
        "days_since_last_promo",
        "stock_to_sales_ratio",
        "days_until_expiry_norm",
    ]

    def __init__(
        self,
        sales_df: pd.DataFrame,
        products_df: pd.DataFrame,
        inventory_df: pd.DataFrame,
        stores_df: pd.DataFrame | None = None,
    ):
        self.sales = sales_df.copy()
        self.products = products_df.copy()
        self.inventory = inventory_df.copy()
        self.stores = stores_df

    def build(self) -> pd.DataFrame:
        """Run the full pipeline and return the feature matrix."""
        df = self._prepare_base()
        df = self._add_temporal(df)
        df = self._add_lags(df)
        df = self._add_rolling(df)
        df = self._add_product_features(df)
        df = self._add_contextual(df)
        df = self._add_derived(df)
        df = self._fill_missing(df)
        return df

    # ── Base join ─────────────────────────────────────────

    def _prepare_base(self) -> pd.DataFrame:
        df = self.sales.copy()
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values(["store_id", "product_id", "date"]).reset_index(drop=True)

        inv = self.inventory[["store_id", "product_id", "date", "quantity_on_hand", "days_until_expiry"]].copy()
        inv["date"] = pd.to_datetime(inv["date"])

        df = df.merge(inv, on=["store_id", "product_id", "date"], how="left")
        return df

    # ── Temporal features ─────────────────────────────────

    def _add_temporal(self, df: pd.DataFrame) -> pd.DataFrame:
        df["day_of_week"] = df["date"].dt.dayofweek
        df["day_of_month"] = df["date"].dt.day
        df["week_of_year"] = df["date"].dt.isocalendar().week.astype(int)
        df["month"] = df["date"].dt.month
        df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
        df["is_month_start"] = (df["day_of_month"] <= 3).astype(int)
        df["is_month_end"] = (df["day_of_month"] >= 28).astype(int)
        return df

    # ── Lag features ──────────────────────────────────────

    def _add_lags(self, df: pd.DataFrame) -> pd.DataFrame:
        group = df.groupby(["store_id", "product_id"])

        df["sales_lag_1d"] = group["quantity_sold"].shift(1)
        df["sales_lag_7d"] = group["quantity_sold"].shift(7)
        df["sales_lag_14d"] = group["quantity_sold"].shift(14)
        df["sales_lag_28d"] = group["quantity_sold"].shift(28)

        df["waste_lag_1d"] = group["units_wasted"].shift(1)
        df["waste_lag_7d"] = group["units_wasted"].shift(7)

        df["inventory_lag_1d"] = group["quantity_on_hand"].shift(1)
        return df

    # ── Rolling window features ───────────────────────────

    def _add_rolling(self, df: pd.DataFrame) -> pd.DataFrame:
        group = df.groupby(["store_id", "product_id"])

        roll7 = group["quantity_sold"].transform(lambda x: x.shift(1).rolling(7, min_periods=1).mean())
        df["sales_rolling_7d_mean"] = roll7

        df["sales_rolling_7d_std"] = group["quantity_sold"].transform(lambda x: x.shift(1).rolling(7, min_periods=2).std())

        df["sales_rolling_14d_mean"] = group["quantity_sold"].transform(lambda x: x.shift(1).rolling(14, min_periods=1).mean())

        df["sales_rolling_28d_mean"] = group["quantity_sold"].transform(lambda x: x.shift(1).rolling(28, min_periods=1).mean())

        df["waste_rolling_7d_sum"] = group["units_wasted"].transform(lambda x: x.shift(1).rolling(7, min_periods=1).sum())

        sold_roll = group["quantity_sold"].transform(lambda x: x.shift(1).rolling(7, min_periods=1).sum())
        waste_roll = group["units_wasted"].transform(lambda x: x.shift(1).rolling(7, min_periods=1).sum())
        df["waste_rolling_7d_rate"] = (waste_roll / sold_roll.replace(0, np.nan)).fillna(0)

        df["revenue_rolling_7d"] = group["revenue"].transform(lambda x: x.shift(1).rolling(7, min_periods=1).sum())

        df["sales_rolling_7d_median"] = group["quantity_sold"].transform(lambda x: x.shift(1).rolling(7, min_periods=1).median())

        return df

    # ── Product features ──────────────────────────────────

    def _add_product_features(self, df: pd.DataFrame) -> pd.DataFrame:
        prod = self.products[["product_id", "unit_price", "cost_price", "shelf_life_days", "category_id"]].copy()
        prod["unit_price"] = prod["unit_price"].astype(float)
        prod["cost_price"] = prod["cost_price"].astype(float)
        prod["margin_pct"] = (prod["unit_price"] - prod["cost_price"]) / prod["unit_price"].replace(0, np.nan)
        prod["margin_pct"] = prod["margin_pct"].fillna(0)
        prod["category_encoded"] = prod["category_id"] - 1
        prod = prod.drop(columns=["category_id"])

        df = df.merge(prod, on="product_id", how="left")
        return df

    # ── Contextual features ───────────────────────────────

    def _add_contextual(self, df: pd.DataFrame) -> pd.DataFrame:
        df["is_holiday"] = df["is_holiday"].astype(int)
        df["is_promotion"] = df["is_promotion"].astype(int)
        df["promotion_discount"] = df["promotion_discount"].astype(float)
        df["temperature_avg"] = df["temperature_avg"].astype(float)

        if self.stores is not None:
            store_map = dict(zip(self.stores["store_id"], self.stores["type"].map(STORE_TYPE_MAP)))
            df["store_type_encoded"] = df["store_id"].map(store_map)
        else:
            df["store_type_encoded"] = 1
        return df

    # ── Derived features ──────────────────────────────────

    def _add_derived(self, df: pd.DataFrame) -> pd.DataFrame:
        group = df.groupby(["store_id", "product_id"])

        df["_promo_cumcount"] = group["is_promotion"].cumsum()
        df["_last_promo_date"] = df["date"].where(df["is_promotion"] == 1)
        df["_last_promo_date"] = group["_last_promo_date"].ffill()
        df["days_since_last_promo"] = (df["date"] - df["_last_promo_date"]).dt.days.fillna(999).astype(int)
        df = df.drop(columns=["_promo_cumcount", "_last_promo_date"])

        avg_sales_7d = df["sales_rolling_7d_mean"].replace(0, np.nan)
        df["stock_to_sales_ratio"] = (df["quantity_on_hand"] / avg_sales_7d).fillna(0)

        df["days_until_expiry_norm"] = df["days_until_expiry"] / df["shelf_life_days"].replace(0, 1)

        return df

    # ── Fill missing values ───────────────────────────────

    def _fill_missing(self, df: pd.DataFrame) -> pd.DataFrame:
        for col in self.FEATURE_COLUMNS:
            if col in df.columns and df[col].isna().any():
                median_val = df[col].median()
                df[col] = df[col].fillna(median_val if pd.notna(median_val) else 0)
        return df
