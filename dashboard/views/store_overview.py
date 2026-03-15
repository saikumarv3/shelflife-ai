"""Page 2: Store Overview — Deep-dive into a single store's performance."""

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard import queries as Q
from dashboard.styles import (
    BRAND_ACCENT,
    BRAND_BLUE,
    BRAND_RED,
    apply_chart_style,
    chart_desc,
    kpi_card_row,
    page_header,
)


def render(store_id: int):
    stores = Q.get_stores()
    store = stores[stores["store_id"] == store_id].iloc[0]

    page_header(
        "🏪",
        f"{store['name']}",
        f"{store['location']} · {store['type'].title()} · {store['size_sqft']:,} sq ft — "
        "Detailed performance breakdown for this location.",
    )

    kpi = Q.get_kpi_summary(store_id)
    if kpi.empty or kpi.iloc[0]["total_sold"] is None:
        st.info("No data for this store.")
        return

    r = kpi.iloc[0]
    kpi_card_row(
        [
            ("Revenue", f"${float(r['total_revenue'] or 0):,.0f}", None),
            ("Units Sold", f"{int(r['total_sold'] or 0):,}", None),
            ("Waste Rate", f"{float(r['waste_pct'] or 0):.1f}%", None),
            ("Products", f"{int(r['products'] or 0)}", f"{int(r['days_tracked'] or 0)} days"),
        ]
    )

    st.markdown("###")

    daily = Q.get_daily_metrics(store_id)
    if not daily.empty:
        tab1, tab2 = st.tabs(["📈 Revenue", "📦 Sales vs Waste"])

        with tab1:
            chart_desc(
                "Daily revenue for this store. Spikes often align with weekends or promotions. Consistent dips may indicate staffing or stock issues."
            )
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=daily["date"],
                    y=daily["revenue"],
                    fill="tozeroy",
                    line=dict(color=BRAND_ACCENT, width=2),
                    fillcolor="rgba(16,185,129,0.1)",
                    name="Revenue",
                )
            )
            apply_chart_style(fig, 320, title="Daily Revenue ($)", yaxis_title="$")
            st.plotly_chart(fig, width="stretch")

        with tab2:
            chart_desc(
                "Blue bars = units sold, red bars = units wasted (stacked). If the red portion is growing relative to blue, waste is becoming a bigger problem at this store."
            )
            fig2 = go.Figure()
            fig2.add_trace(
                go.Bar(
                    x=daily["date"],
                    y=daily["sold"],
                    name="Sold",
                    marker_color=BRAND_BLUE,
                    opacity=0.7,
                )
            )
            fig2.add_trace(
                go.Bar(
                    x=daily["date"],
                    y=daily["wasted"],
                    name="Wasted",
                    marker_color=BRAND_RED,
                    opacity=0.7,
                )
            )
            apply_chart_style(
                fig2, 320, barmode="stack", title="Units Sold vs Wasted", yaxis_title="Units", legend=dict(orientation="h", y=1.1)
            )
            st.plotly_chart(fig2, width="stretch")

    col1, col2 = st.columns(2)
    waste_cat = Q.get_waste_by_category(store_id)
    if not waste_cat.empty:
        with col1:
            st.markdown("#### Category Breakdown")
            chart_desc(
                "Treemap sized by sales volume, colored by waste rate. Large red boxes = high-volume categories with a waste problem. Green = healthy categories."
            )
            fig = px.treemap(
                waste_cat,
                path=["category"],
                values="sold",
                color="waste_rate",
                color_continuous_scale=["#D1FAE5", "#FEE2E2"],
                title="Sales by Category (color = waste rate %)",
            )
            apply_chart_style(fig, 380, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig, width="stretch")

    top_sold = Q.run(
        """
        SELECT p.name as product, c.name as category,
               SUM(ds.quantity_sold) as sold, SUM(ds.revenue) as revenue
        FROM daily_sales ds
        JOIN products p ON p.product_id = ds.product_id
        JOIN categories c ON c.category_id = p.category_id
        WHERE ds.store_id = :sid
        GROUP BY p.name, c.name
        ORDER BY sold DESC LIMIT 10
    """,
        {"sid": store_id},
    )

    top_wasted = Q.get_top_wasted_products(store_id, limit=10)

    with col2:
        tab_s, tab_w = st.tabs(["🏆 Top Sellers", "⚠️ Top Wasters"])
        with tab_s:
            chart_desc(
                "Your best-selling products at this store. These are your revenue drivers — make sure they're always in stock."
            )
            if not top_sold.empty:
                st.dataframe(top_sold, width="stretch", hide_index=True)
        with tab_w:
            chart_desc(
                "Products wasting the most units. These need urgent attention: reduce order quantity, mark down before expiry, or donate."
            )
            if not top_wasted.empty:
                st.dataframe(top_wasted, width="stretch", hide_index=True)

    st.markdown("### 🚨 Inventory Alerts")
    chart_desc(
        "Items that need immediate action — either expiring soon or running below the minimum stock level needed to avoid lost sales."
    )
    inv = Q.get_inventory_snapshot(store_id)
    if not inv.empty:
        critical = inv[inv["days_until_expiry"].notna() & (inv["days_until_expiry"] <= 3)]
        low_stock = inv[inv["quantity_on_hand"] < inv["reorder_point"]]

        c1, c2 = st.columns(2)
        c1.metric("Expiring Soon (≤3 days)", len(critical))
        c2.metric("Below Reorder Point", len(low_stock))

        if not critical.empty:
            st.error(f"**{len(critical)} items expiring within 3 days** — consider markdown pricing or donation")
            st.dataframe(
                critical[["product", "category", "quantity_on_hand", "days_until_expiry", "unit_price"]],
                width="stretch",
                hide_index=True,
            )
    else:
        st.info("No inventory snapshot data available.")
