"""ShelfLife AI — Streamlit Dashboard (4 pages)."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import text

from config.settings import settings
from db.session import engine

st.set_page_config(page_title="ShelfLife AI", page_icon="🥬", layout="wide")

PAGES = ["Demand Forecast", "Waste Risk", "Recommendations", "Model Performance"]


@st.cache_data(ttl=300)
def query(sql: str, params: dict | None = None) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params)


def sidebar():
    st.sidebar.title("ShelfLife AI")
    page = st.sidebar.radio("Navigate", PAGES)

    stores = query("SELECT store_id, name FROM stores ORDER BY store_id")
    store_id = st.sidebar.selectbox(
        "Store", stores["store_id"].tolist(),
        format_func=lambda x: stores.loc[stores["store_id"] == x, "name"].values[0],
    )
    return page, store_id


# ── Page 1: Demand Forecast ──────────────────────────────────

def page_demand_forecast(store_id: int):
    st.header("Demand Forecast")

    categories = query("SELECT category_id, name FROM categories ORDER BY name")
    cat_filter = st.selectbox("Category", ["All"] + categories["name"].tolist())

    col1, col2 = st.columns(2)
    with col1:
        date_from = st.date_input("From", value=pd.Timestamp("2024-10-01"))
    with col2:
        date_to = st.date_input("To", value=pd.Timestamp("2024-12-31"))

    sql = """
        SELECT ds.date, ds.product_id, p.name as product_name, c.name as category,
               ds.quantity_sold as actual, pr.predicted_demand as predicted,
               pr.confidence_lower, pr.confidence_upper
        FROM daily_sales ds
        JOIN products p ON p.product_id = ds.product_id
        JOIN categories c ON c.category_id = p.category_id
        LEFT JOIN predictions pr ON pr.store_id = ds.store_id
            AND pr.product_id = ds.product_id AND pr.date = ds.date
        WHERE ds.store_id = :sid AND ds.date BETWEEN :d1 AND :d2
        ORDER BY ds.date
    """
    df = query(sql, {"sid": store_id, "d1": str(date_from), "d2": str(date_to)})

    if df.empty:
        st.info("No data for selected filters. Run `uv run python -m scripts.run_daily_forecast` to generate predictions.")
        return

    if cat_filter != "All":
        df = df[df["category"] == cat_filter]

    # KPI cards
    if "predicted" in df.columns and df["predicted"].notna().any():
        matched = df.dropna(subset=["predicted", "actual"])
        if not matched.empty:
            mape_val = (abs(matched["predicted"] - matched["actual"]) / matched["actual"].clip(lower=1)).mean()
            c1, c2, c3 = st.columns(3)
            c1.metric("MAPE", f"{mape_val:.1%}")
            c2.metric("Predictions", f"{len(matched):,}")
            c3.metric("Products", f"{df['product_id'].nunique()}")

    # Aggregate by date
    daily = df.groupby("date").agg(
        actual=("actual", "sum"),
        predicted=("predicted", "sum"),
    ).reset_index()

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=daily["date"], y=daily["actual"], name="Actual", line=dict(color="#2563eb")))
    if daily["predicted"].notna().any():
        fig.add_trace(go.Scatter(x=daily["date"], y=daily["predicted"], name="Predicted", line=dict(color="#f97316", dash="dash")))
    fig.update_layout(title="Daily Demand: Actual vs Predicted", xaxis_title="Date", yaxis_title="Units Sold", height=400)
    st.plotly_chart(fig, use_container_width=True)

    # Top products table
    top = df.groupby(["product_id", "product_name"]).agg(
        total_sold=("actual", "sum"),
        avg_daily=("actual", "mean"),
    ).sort_values("total_sold", ascending=False).head(10).reset_index()
    st.subheader("Top 10 Products by Sales")
    st.dataframe(top, use_container_width=True, hide_index=True)


# ── Page 2: Waste Risk ───────────────────────────────────────

def page_waste_risk(store_id: int):
    st.header("Waste Risk Monitor")

    sql = """
        SELECT ds.date, ds.product_id, p.name as product_name, c.name as category,
               ds.units_wasted, ds.quantity_sold,
               i.days_until_expiry, i.quantity_on_hand
        FROM daily_sales ds
        JOIN products p ON p.product_id = ds.product_id
        JOIN categories c ON c.category_id = p.category_id
        LEFT JOIN inventory_snapshots i ON i.store_id = ds.store_id
            AND i.product_id = ds.product_id AND i.date = ds.date
        WHERE ds.store_id = :sid AND ds.date >= '2024-10-01'
        ORDER BY ds.date
    """
    df = query(sql, {"sid": store_id})

    if df.empty:
        st.info("No waste data available.")
        return

    # KPI cards
    total_wasted = df["units_wasted"].sum()
    total_sold = df["quantity_sold"].sum()
    waste_rate = total_wasted / max(total_sold, 1)
    kg_wasted = total_wasted * 0.3

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Wasted", f"{total_wasted:,} units")
    c2.metric("Waste Rate", f"{waste_rate:.1%}")
    c3.metric("~Kg Wasted", f"{kg_wasted:,.0f}")
    c4.metric("~Meals Lost", f"{int(kg_wasted * 2.5):,}")

    # Waste by category
    by_cat = df.groupby("category").agg(wasted=("units_wasted", "sum")).sort_values("wasted", ascending=False).reset_index()
    fig = px.bar(by_cat, x="category", y="wasted", title="Waste by Category", color="wasted", color_continuous_scale="Reds")
    st.plotly_chart(fig, use_container_width=True)

    # Waste trend
    daily_waste = df.groupby("date").agg(wasted=("units_wasted", "sum")).reset_index()
    fig2 = px.area(daily_waste, x="date", y="wasted", title="Daily Waste Trend", color_discrete_sequence=["#ef4444"])
    st.plotly_chart(fig2, use_container_width=True)

    # At-risk items (low days to expiry, high stock)
    latest = df.loc[df["date"] == df["date"].max()].copy()
    if "days_until_expiry" in latest.columns:
        at_risk = latest[latest["days_until_expiry"].notna() & (latest["days_until_expiry"] <= 3)]
        if not at_risk.empty:
            st.subheader("At-Risk Items (3 days to expiry)")
            st.dataframe(
                at_risk[["product_name", "category", "quantity_on_hand", "days_until_expiry"]].sort_values("days_until_expiry"),
                use_container_width=True, hide_index=True,
            )


# ── Page 3: Recommendations ──────────────────────────────────

def page_recommendations(store_id: int):
    st.header("Recommendations")

    sql = """
        SELECT r.date, r.product_id, p.name as product_name,
               r.action_type, r.markdown_pct,
               r.expected_waste_reduction, r.expected_cost_saved_usd,
               r.status, r.actual_waste_reduction, r.actual_cost_saved_usd,
               r.created_at
        FROM recommendations_log r
        JOIN products p ON p.product_id = r.product_id
        WHERE r.store_id = :sid
        ORDER BY r.created_at DESC
        LIMIT 100
    """
    df = query(sql, {"sid": store_id})

    if df.empty:
        st.info("No recommendations generated yet. Use the `/recommend` API endpoint to generate some.")
        return

    # KPIs
    total = len(df)
    accepted = len(df[df["status"] == "accepted"])
    expected_savings = df["expected_cost_saved_usd"].sum()
    actual_savings = df["actual_cost_saved_usd"].sum() if "actual_cost_saved_usd" in df.columns else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Recs", total)
    c2.metric("Accepted", f"{accepted} ({accepted/max(total,1):.0%})")
    c3.metric("Expected Savings", f"${expected_savings:,.2f}")
    c4.metric("Actual Savings", f"${actual_savings:,.2f}")

    # By action type
    by_action = df.groupby("action_type").size().reset_index(name="count")
    fig = px.pie(by_action, names="action_type", values="count", title="Recommendations by Action Type")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Recent Recommendations")
    st.dataframe(df, use_container_width=True, hide_index=True)


# ── Page 4: Model Performance ────────────────────────────────

def page_model_performance(store_id: int):
    st.header("Model Performance & MLOps")

    # Alerts
    alerts_df = query("""
        SELECT alert_type, severity, message, created_at
        FROM alerts ORDER BY created_at DESC LIMIT 20
    """)

    if not alerts_df.empty:
        st.subheader("Recent Alerts")
        st.dataframe(alerts_df, use_container_width=True, hide_index=True)

    # Feature importance (from feature store stats)
    st.subheader("Feature Store Stats")
    feat_stats = query("""
        SELECT COUNT(*) as total_rows,
               COUNT(DISTINCT product_id) as products,
               COUNT(DISTINCT store_id) as stores,
               MIN(date) as first_date,
               MAX(date) as last_date
        FROM feature_store
    """)
    if not feat_stats.empty:
        row = feat_stats.iloc[0]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Feature Rows", f"{row['total_rows']:,}")
        c2.metric("Products", row["products"])
        c3.metric("Stores", row["stores"])
        c4.metric("Date Range", f"{row['first_date']} to {row['last_date']}")

    # Drift detection status
    st.subheader("Drift Detection Status")
    drift_alerts = query("""
        SELECT message, metadata_json, created_at
        FROM alerts WHERE alert_type = 'data_drift'
        ORDER BY created_at DESC LIMIT 5
    """)
    if drift_alerts.empty:
        st.success("No data drift detected. All features are stable.")
    else:
        st.warning(f"{len(drift_alerts)} drift alerts found")
        st.dataframe(drift_alerts, use_container_width=True, hide_index=True)

    # Model promotion history
    st.subheader("Model Promotion History")
    promo_df = query("""
        SELECT message, metadata_json, created_at
        FROM alerts WHERE alert_type = 'model_promoted'
        ORDER BY created_at DESC LIMIT 10
    """)
    if promo_df.empty:
        st.info("No model promotions recorded yet.")
    else:
        st.dataframe(promo_df, use_container_width=True, hide_index=True)


# ── Main ─────────────────────────────────────────────────────

def main():
    page, store_id = sidebar()

    if page == "Demand Forecast":
        page_demand_forecast(store_id)
    elif page == "Waste Risk":
        page_waste_risk(store_id)
    elif page == "Recommendations":
        page_recommendations(store_id)
    elif page == "Model Performance":
        page_model_performance(store_id)


if __name__ == "__main__":
    main()
