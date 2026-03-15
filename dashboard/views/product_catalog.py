"""Page 3: Product Catalog — Browse, filter, and explore product metrics per store."""

import plotly.express as px
import streamlit as st

from dashboard import queries as Q
from dashboard.styles import BRAND_ACCENT, COLOR_PALETTE, apply_chart_style, chart_desc, page_header


def render(store_id: int):
    stores = Q.get_stores()
    store_name = stores.loc[stores["store_id"] == store_id, "name"].values[0]

    page_header(
        "🛒",
        "Product Catalog",
        f"Every product stocked at **{store_name}** with real sales data. "
        "Use filters to narrow down by category, storage type, or perishability. Switch stores in the sidebar to compare.",
    )

    products = Q.get_products()
    sales = Q.get_product_sales(store_id)
    if products.empty:
        st.info("No products found.")
        return

    merged = products.merge(
        sales[["product_id", "total_sold", "total_revenue", "total_wasted", "avg_daily_sold"]], on="product_id", how="left"
    )
    merged["total_sold"] = merged["total_sold"].fillna(0).astype(int)
    merged["total_revenue"] = merged["total_revenue"].fillna(0)
    merged["total_wasted"] = merged["total_wasted"].fillna(0).astype(int)
    merged["avg_daily_sold"] = merged["avg_daily_sold"].fillna(0)

    col1, col2, col3 = st.columns(3)
    with col1:
        cat_filter = st.selectbox("Category", ["All"] + sorted(merged["category"].unique().tolist()))
    with col2:
        storage_filter = st.selectbox("Storage Type", ["All"] + sorted(merged["storage_temp"].unique().tolist()))
    with col3:
        perish_filter = st.selectbox("Perishability", ["All"] + sorted(merged["perishability"].unique().tolist()))

    filtered = merged.copy()
    if cat_filter != "All":
        filtered = filtered[filtered["category"] == cat_filter]
    if storage_filter != "All":
        filtered = filtered[filtered["storage_temp"] == storage_filter]
    if perish_filter != "All":
        filtered = filtered[filtered["perishability"] == perish_filter]

    st.markdown(f"**{len(filtered)} products** matching filters")
    st.divider()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Products", len(filtered))
    total_sold_store = int(filtered["total_sold"].sum())
    col2.metric("Units Sold", f"{total_sold_store:,}")
    total_rev_store = float(filtered["total_revenue"].sum())
    col3.metric("Revenue", f"${total_rev_store:,.0f}")
    total_waste_store = int(filtered["total_wasted"].sum())
    col4.metric("Units Wasted", f"{total_waste_store:,}")

    st.markdown("###")

    view = st.radio("View", ["📊 Table", "🃏 Cards"], horizontal=True, label_visibility="collapsed")

    if view == "📊 Table":
        chart_desc(
            "Full product list with sales data from this specific store. Sort any column by clicking the header. 'Avg Daily' helps you set reorder quantities."
        )
        display_df = filtered[
            [
                "product_id",
                "name",
                "category",
                "unit_price",
                "cost_price",
                "shelf_life_days",
                "total_sold",
                "avg_daily_sold",
                "total_wasted",
            ]
        ].copy()
        display_df.columns = ["ID", "Product", "Category", "Price", "Cost", "Shelf Life", "Sold", "Avg Daily", "Wasted"]
        display_df["Avg Daily"] = display_df["Avg Daily"].round(1)
        st.dataframe(display_df, width="stretch", hide_index=True, height=500)
    else:
        chart_desc(
            "Card view shows each product with margin color-coding: green = high margin (>30%), orange = medium (15-30%), red = low margin (<15%). Switch stores to see different sales numbers."
        )
        cols = st.columns(3)
        for idx, (_, p) in enumerate(filtered.iterrows()):
            margin = (float(p["unit_price"]) - float(p["cost_price"])) / float(p["unit_price"]) * 100
            color = BRAND_ACCENT if margin > 30 else "#F59E0B" if margin > 15 else "#EF4444"
            sold = int(p["total_sold"])
            wasted = int(p["total_wasted"])
            with cols[idx % 3]:
                st.markdown(
                    f"""
                <div style="background:var(--secondary-background-color); border:1px solid rgba(128,128,128,0.2); border-radius:12px;
                     padding:16px; margin-bottom:12px; border-left:4px solid {color};">
                    <div style="font-weight:700; font-size:1rem;">{p["name"]}</div>
                    <div style="opacity:0.6; font-size:0.8rem; margin:4px 0 10px 0;">{p["category"]} · {p["storage_temp"]} · {p["perishability"]}</div>
                    <div style="display:flex; gap:16px; font-size:0.85rem; flex-wrap:wrap;">
                        <div><span style="opacity:0.6;">Price:</span> <b>${float(p["unit_price"]):.2f}</b></div>
                        <div><span style="opacity:0.6;">Margin:</span> <b style="color:{color};">{margin:.0f}%</b></div>
                        <div><span style="opacity:0.6;">Sold:</span> <b>{sold:,}</b></div>
                        <div><span style="opacity:0.6;">Wasted:</span> <b style="color:#EF4444;">{wasted:,}</b></div>
                    </div>
                </div>
                """,
                    unsafe_allow_html=True,
                )

    st.markdown("###")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Sales by Category")
        chart_desc(
            "Which categories drive the most sales volume at this store? Larger slices = more units sold. Compare against waste to find your most and least efficient categories."
        )
        cat_sales = filtered.groupby("category").agg(sold=("total_sold", "sum")).reset_index()
        fig = px.pie(
            cat_sales, names="category", values="sold", title="Units Sold by Category", color_discrete_sequence=COLOR_PALETTE
        )
        apply_chart_style(fig, 300)
        st.plotly_chart(fig, width="stretch")

    with col2:
        st.markdown(f"#### Top Sellers at {store_name}")
        chart_desc(
            "The 10 best-selling products at this specific store. These are your must-stock items — running out of these costs you the most in lost sales."
        )
        top_sellers = filtered.nlargest(10, "total_sold")
        if not top_sellers.empty:
            fig = px.bar(
                top_sellers,
                y="name",
                x="total_sold",
                orientation="h",
                color="category",
                color_discrete_sequence=COLOR_PALETTE,
                title="Top 10 Products by Units Sold",
            )
            apply_chart_style(fig, 300, yaxis=dict(autorange="reversed"), showlegend=False)
            st.plotly_chart(fig, width="stretch")
