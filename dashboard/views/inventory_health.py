"""Page 4: Inventory Health — Expiry heatmap, stock levels, and action items."""

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard import queries as Q
from dashboard.styles import BRAND_ACCENT, BRAND_ORANGE, BRAND_RED, apply_chart_style, chart_desc, kpi_card_row, page_header


def render(store_id: int):
    page_header(
        "📦",
        "Inventory Health",
        "The live state of your shelves. See what's expiring, what's understocked, and where to act now to prevent waste.",
    )

    inv = Q.get_inventory_snapshot(store_id)
    if inv.empty:
        st.info("No inventory snapshot data available for this store.")
        return

    inv["days_until_expiry"] = inv["days_until_expiry"].fillna(999)

    critical = inv[inv["days_until_expiry"] <= 2]
    warning = inv[(inv["days_until_expiry"] > 2) & (inv["days_until_expiry"] <= 5)]
    below_reorder = inv[inv["quantity_on_hand"] < inv["reorder_point"]]

    kpi_card_row(
        [
            ("Total SKUs", f"{len(inv)}", None),
            ("Critical (≤2 days)", f"{len(critical)}", "needs action" if len(critical) > 0 else "all clear"),
            ("Warning (3-5 days)", f"{len(warning)}", "monitor" if len(warning) > 0 else "all clear"),
            ("Below Reorder Point", f"{len(below_reorder)}", "restock" if len(below_reorder) > 0 else "all clear"),
        ]
    )

    st.markdown("###")

    st.markdown("#### Expiry Risk Map")
    chart_desc(
        "Each bubble is a product category. Position shows avg days to expiry vs. total stock. Red bubbles near the left = categories with lots of stock about to expire. Green bubbles on the right = healthy."
    )
    inv_heat = inv[inv["days_until_expiry"] < 999].copy()
    if not inv_heat.empty:
        heat_data = (
            inv_heat.groupby("category")
            .agg(
                avg_expiry=("days_until_expiry", "mean"),
                total_stock=("quantity_on_hand", "sum"),
                items=("product", "count"),
            )
            .reset_index()
        )

        fig = px.scatter(
            heat_data,
            x="avg_expiry",
            y="total_stock",
            size="items",
            color="avg_expiry",
            color_continuous_scale=["#EF4444", "#F59E0B", "#10B981"],
            text="category",
            title="Category Expiry Risk vs Stock Level",
        )
        fig.update_traces(textposition="top center")
        apply_chart_style(fig, 380, xaxis_title="Avg Days Until Expiry", yaxis_title="Total Stock on Hand")
        st.plotly_chart(fig, width="stretch")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Stock vs Reorder Point")
        chart_desc(
            "Green bar = current stock. Orange bar = minimum reorder point. If green is shorter than orange, you're understocked and risk empty shelves."
        )
        sample = inv.head(25).copy()
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                y=sample["product"],
                x=sample["quantity_on_hand"],
                name="Current Stock",
                marker_color=BRAND_ACCENT,
                orientation="h",
            )
        )
        fig.add_trace(
            go.Bar(
                y=sample["product"],
                x=sample["reorder_point"],
                name="Reorder Point",
                marker_color=BRAND_ORANGE,
                orientation="h",
                opacity=0.5,
            )
        )
        apply_chart_style(
            fig,
            600,
            barmode="overlay",
            title="Stock Level vs Min Reorder",
            xaxis_title="Units",
            yaxis=dict(autorange="reversed", tickfont=dict(size=10)),
            legend=dict(orientation="h", y=1.02),
        )
        st.plotly_chart(fig, width="stretch")

    with col2:
        st.markdown("#### Expiry Distribution")
        chart_desc(
            "How many products fall into each expiry bucket. The red dashed line at 3 days is the critical threshold — everything to the left needs action today."
        )
        if not inv_heat.empty:
            fig = px.histogram(
                inv_heat,
                x="days_until_expiry",
                nbins=20,
                color_discrete_sequence=[BRAND_ACCENT],
                title="Products by Days Until Expiry",
            )
            fig.add_vline(x=3, line_dash="dash", line_color=BRAND_RED, annotation_text="Critical (3d)")
            apply_chart_style(fig, 300, xaxis_title="Days Until Expiry", yaxis_title="# Products")
            st.plotly_chart(fig, width="stretch")

        st.markdown("#### Action Required")
        chart_desc(
            "These items will expire within 2 days. Sorted by estimated loss value — take action on the top items first to save the most money."
        )
        if not critical.empty:
            st.error(f"**{len(critical)} items expiring within 2 days** — consider markdown or donation")
            action_df = critical[["product", "category", "quantity_on_hand", "days_until_expiry", "unit_price"]].copy()
            action_df["est_loss"] = action_df["quantity_on_hand"] * action_df["unit_price"].astype(float)
            action_df.columns = ["Product", "Category", "On Hand", "Days Left", "Price", "Est. Loss ($)"]
            action_df = action_df.sort_values("Est. Loss ($)", ascending=False)
            st.dataframe(action_df, width="stretch", hide_index=True)
        else:
            st.success("No critical expiry items — inventory is healthy!")

    st.markdown("#### Full Inventory Snapshot")
    chart_desc(
        "Complete list of every product's current stock, expiry, and reorder status. Use this to plan your next delivery or identify items that need immediate attention."
    )
    display = inv[["product", "category", "quantity_on_hand", "days_until_expiry", "reorder_point", "unit_price"]].copy()
    display.columns = ["Product", "Category", "On Hand", "Days to Expiry", "Reorder Pt", "Price"]
    st.dataframe(display, width="stretch", hide_index=True, height=400)
