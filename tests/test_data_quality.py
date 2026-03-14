"""Data quality tests — schema validation, null checks, FK integrity."""

from sqlalchemy import text


def test_stores_not_empty(db_engine):
    with db_engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM stores")).scalar()
    assert count > 0


def test_products_not_empty(db_engine):
    with db_engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM products")).scalar()
    assert count > 0


def test_daily_sales_row_count(db_engine):
    with db_engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM daily_sales")).scalar()
    assert count > 50000


def test_no_negative_quantities(db_engine):
    with db_engine.connect() as conn:
        neg = conn.execute(text("SELECT COUNT(*) FROM daily_sales WHERE quantity_sold < 0")).scalar()
    assert neg == 0


def test_no_orphan_sales(db_engine):
    with db_engine.connect() as conn:
        orphans = conn.execute(
            text("""
            SELECT COUNT(*) FROM daily_sales ds
            LEFT JOIN products p ON p.product_id = ds.product_id
            WHERE p.product_id IS NULL
        """)
        ).scalar()
    assert orphans == 0


def test_feature_store_populated(db_engine):
    with db_engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM feature_store")).scalar()
    assert count > 0


def test_no_null_feature_columns(db_engine):
    critical = ["sales_lag_7d", "sales_rolling_7d_mean", "unit_price"]
    with db_engine.connect() as conn:
        for col in critical:
            null_count = conn.execute(text(f"SELECT COUNT(*) FROM feature_store WHERE {col} IS NULL")).scalar()
            assert null_count == 0, f"feature_store.{col} has {null_count} nulls"
