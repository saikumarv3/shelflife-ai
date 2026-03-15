"""ShelfLife AI — Centralized database queries for the dashboard."""

import pandas as pd
import streamlit as st
from sqlalchemy import text

from db.session import engine


@st.cache_data(ttl=300)
def run(sql: str, params: dict | None = None) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params)


def get_stores() -> pd.DataFrame:
    return run("SELECT store_id, name, location, size_sqft, type FROM stores ORDER BY store_id")


def get_categories() -> pd.DataFrame:
    return run("SELECT category_id, name, perishability, avg_shelf_days FROM categories ORDER BY name")


def get_products() -> pd.DataFrame:
    return run("""
        SELECT p.product_id, p.name, p.unit_price, p.cost_price,
               p.shelf_life_days, p.storage_temp,
               c.name as category, c.perishability
        FROM products p
        JOIN categories c ON c.category_id = p.category_id
        ORDER BY p.name
    """)


def get_date_range() -> tuple[str, str]:
    df = run("SELECT MIN(date) as min_d, MAX(date) as max_d FROM daily_sales")
    if df.empty:
        return "2025-12-15", "2026-03-07"
    return str(df.iloc[0]["min_d"]), str(df.iloc[0]["max_d"])


def get_kpi_summary(store_id: int | None = None) -> pd.DataFrame:
    where = "WHERE ds.store_id = :sid" if store_id else ""
    params = {"sid": store_id} if store_id else {}
    return run(
        f"""
        SELECT
            COUNT(DISTINCT ds.store_id) as stores,
            COUNT(DISTINCT ds.product_id) as products,
            SUM(ds.quantity_sold) as total_sold,
            SUM(ds.revenue) as total_revenue,
            SUM(ds.units_wasted) as total_wasted,
            SUM(ds.units_donated) as total_donated,
            ROUND(SUM(ds.units_wasted)::numeric / NULLIF(SUM(ds.quantity_sold), 0) * 100, 1) as waste_pct,
            COUNT(DISTINCT ds.date) as days_tracked
        FROM daily_sales ds
        {where}
    """,
        params,
    )


def get_daily_metrics(store_id: int | None = None) -> pd.DataFrame:
    where = "WHERE ds.store_id = :sid" if store_id else ""
    params = {"sid": store_id} if store_id else {}
    return run(
        f"""
        SELECT ds.date,
               SUM(ds.quantity_sold) as sold,
               SUM(ds.revenue) as revenue,
               SUM(ds.units_wasted) as wasted
        FROM daily_sales ds
        {where}
        GROUP BY ds.date
        ORDER BY ds.date
    """,
        params,
    )


def get_waste_by_category(store_id: int | None = None) -> pd.DataFrame:
    where = "WHERE ds.store_id = :sid" if store_id else ""
    params = {"sid": store_id} if store_id else {}
    return run(
        f"""
        SELECT c.name as category,
               SUM(ds.units_wasted) as wasted,
               SUM(ds.quantity_sold) as sold,
               ROUND(SUM(ds.units_wasted)::numeric / NULLIF(SUM(ds.quantity_sold), 0) * 100, 1) as waste_rate
        FROM daily_sales ds
        JOIN products p ON p.product_id = ds.product_id
        JOIN categories c ON c.category_id = p.category_id
        {where}
        GROUP BY c.name
        ORDER BY wasted DESC
    """,
        params,
    )


def get_top_wasted_products(store_id: int | None = None, limit: int = 10) -> pd.DataFrame:
    where = "WHERE ds.store_id = :sid" if store_id else ""
    params = {"sid": store_id} if store_id else {}
    return run(
        f"""
        SELECT p.name as product, c.name as category,
               SUM(ds.units_wasted) as wasted,
               SUM(ds.quantity_sold) as sold,
               ROUND(p.unit_price * SUM(ds.units_wasted), 2) as waste_cost
        FROM daily_sales ds
        JOIN products p ON p.product_id = ds.product_id
        JOIN categories c ON c.category_id = p.category_id
        {where}
        GROUP BY p.name, c.name, p.unit_price
        ORDER BY wasted DESC
        LIMIT {limit}
    """,
        params,
    )


def get_demand_data(store_id: int, date_from: str, date_to: str, category: str | None = None) -> pd.DataFrame:
    cat_filter = "AND c.name = :cat" if category else ""
    params = {"sid": store_id, "d1": date_from, "d2": date_to}
    if category:
        params["cat"] = category
    return run(
        f"""
        SELECT ds.date, ds.product_id, p.name as product_name, c.name as category,
               ds.quantity_sold as actual, pr.predicted_demand as predicted,
               pr.confidence_lower, pr.confidence_upper
        FROM daily_sales ds
        JOIN products p ON p.product_id = ds.product_id
        JOIN categories c ON c.category_id = p.category_id
        LEFT JOIN predictions pr ON pr.store_id = ds.store_id
            AND pr.product_id = ds.product_id AND pr.date = ds.date
        WHERE ds.store_id = :sid AND ds.date BETWEEN :d1 AND :d2
        {cat_filter}
        ORDER BY ds.date
    """,
        params,
    )


def get_inventory_snapshot(store_id: int) -> pd.DataFrame:
    return run(
        """
        SELECT i.product_id, p.name as product, c.name as category,
               i.quantity_on_hand, i.days_until_expiry, i.reorder_point,
               i.last_delivery_date, p.shelf_life_days, p.unit_price
        FROM inventory_snapshots i
        JOIN products p ON p.product_id = i.product_id
        JOIN categories c ON c.category_id = p.category_id
        WHERE i.store_id = :sid AND i.date = (SELECT MAX(date) FROM inventory_snapshots WHERE store_id = :sid)
        ORDER BY i.days_until_expiry ASC NULLS LAST
    """,
        {"sid": store_id},
    )


def get_recommendations(store_id: int) -> pd.DataFrame:
    return run(
        """
        SELECT r.rec_id, r.date, r.product_id, p.name as product,
               c.name as category, r.action_type, r.markdown_pct,
               r.expected_waste_reduction, r.expected_cost_saved_usd,
               r.status, r.actual_waste_reduction, r.actual_cost_saved_usd,
               r.created_at
        FROM recommendations_log r
        JOIN products p ON p.product_id = r.product_id
        JOIN categories c ON c.category_id = p.category_id
        WHERE r.store_id = :sid
        ORDER BY r.created_at DESC
        LIMIT 200
    """,
        {"sid": store_id},
    )


def get_product_sales(store_id: int) -> pd.DataFrame:
    return run(
        """
        SELECT p.product_id, p.name as product, c.name as category,
               SUM(ds.quantity_sold) as total_sold,
               SUM(ds.revenue) as total_revenue,
               SUM(ds.units_wasted) as total_wasted,
               ROUND(AVG(ds.quantity_sold), 1) as avg_daily_sold,
               COUNT(DISTINCT ds.date) as days_on_shelf
        FROM products p
        JOIN categories c ON c.category_id = p.category_id
        LEFT JOIN daily_sales ds ON ds.product_id = p.product_id AND ds.store_id = :sid
        GROUP BY p.product_id, p.name, c.name
        ORDER BY total_sold DESC NULLS LAST
    """,
        {"sid": store_id},
    )


def get_alerts(limit: int = 30) -> pd.DataFrame:
    return run(f"""
        SELECT alert_type, severity, message, created_at
        FROM alerts ORDER BY created_at DESC LIMIT {limit}
    """)


def get_feature_store_stats() -> pd.DataFrame:
    return run("""
        SELECT COUNT(*) as total_rows,
               COUNT(DISTINCT product_id) as products,
               COUNT(DISTINCT store_id) as stores,
               MIN(date) as first_date,
               MAX(date) as last_date
        FROM feature_store
    """)


def get_prediction_accuracy(store_id: int | None = None) -> pd.DataFrame:
    where = "WHERE pr.predicted_demand IS NOT NULL AND ds.quantity_sold > 0"
    if store_id:
        where += " AND ds.store_id = :sid"
    params = {"sid": store_id} if store_id else {}
    return run(
        f"""
        SELECT ds.date,
               SUM(ds.quantity_sold) as actual,
               SUM(pr.predicted_demand) as predicted,
               ROUND(AVG(ABS(pr.predicted_demand - ds.quantity_sold)::numeric / NULLIF(ds.quantity_sold, 0) * 100), 1) as mape
        FROM daily_sales ds
        JOIN predictions pr ON pr.store_id = ds.store_id
            AND pr.product_id = ds.product_id AND pr.date = ds.date
        {where}
        GROUP BY ds.date
        ORDER BY ds.date
    """,
        params,
    )


def get_store_comparison() -> pd.DataFrame:
    return run("""
        SELECT s.store_id, s.name, s.location, s.type,
               SUM(ds.revenue) as revenue,
               SUM(ds.quantity_sold) as units_sold,
               SUM(ds.units_wasted) as units_wasted,
               ROUND(SUM(ds.units_wasted)::numeric / NULLIF(SUM(ds.quantity_sold), 0) * 100, 1) as waste_pct,
               COUNT(DISTINCT ds.product_id) as products
        FROM stores s
        JOIN daily_sales ds ON ds.store_id = s.store_id
        GROUP BY s.store_id, s.name, s.location, s.type
        ORDER BY revenue DESC
    """)
