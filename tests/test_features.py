"""Tests for feature engineering pipeline."""

from features.engineering import FeatureEngineer


def test_feature_column_count():
    assert len(FeatureEngineer.FEATURE_COLUMNS) == 35


def test_feature_build_shape(sample_sales_df, sample_products_df, sample_inventory_df):
    fe = FeatureEngineer(sample_sales_df, sample_products_df, sample_inventory_df)
    df = fe.build()

    assert len(df) == len(sample_sales_df)
    for col in FeatureEngineer.FEATURE_COLUMNS:
        assert col in df.columns, f"Missing feature: {col}"


def test_no_nan_in_features(sample_sales_df, sample_products_df, sample_inventory_df):
    fe = FeatureEngineer(sample_sales_df, sample_products_df, sample_inventory_df)
    df = fe.build()

    for col in FeatureEngineer.FEATURE_COLUMNS:
        nan_count = df[col].isna().sum()
        assert nan_count == 0, f"Feature {col} has {nan_count} NaN values"


def test_temporal_features_range(sample_sales_df, sample_products_df, sample_inventory_df):
    fe = FeatureEngineer(sample_sales_df, sample_products_df, sample_inventory_df)
    df = fe.build()

    assert df["day_of_week"].min() >= 0
    assert df["day_of_week"].max() <= 6
    assert df["month"].min() >= 1
    assert df["month"].max() <= 12
    assert set(df["is_weekend"].unique()).issubset({0, 1})
