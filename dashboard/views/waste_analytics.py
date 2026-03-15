"""Page 6: Waste Analytics — Day-of-week analysis, cost calculator, category hotspots."""

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard import queries as Q
from dashboard.styles import BRAND_ORANGE, BRAND_RED, COLOR_PALETTE, apply_chart_style, chart_desc, kpi_card_row, page_header


def render(store_id: int):
    page_header(
        "🗑️",
        "Waste Analytics",
        "Every wasted unit is lost revenue and wasted resources. Use this page to find patterns, identify the worst offenders, and estimate how much you could save.",
    )

    daily = Q.get_daily_metrics(store_id)
    if daily.empty:
        st.info("No waste data available for this store.")
        return

    total_wasted = int(daily["wasted"].sum())
    total_sold = int(daily["sold"].sum())
    waste_rate = total_wasted / max(total_sold, 1) * 100
    est_kg = total_wasted * 0.3
    est_meals = int(est_kg * 2.5)
    avg_price = 3.50
    est_cost = total_wasted * avg_price

    kpi_card_row(
        [
            ("Units Wasted", f"{total_wasted:,}", f"{waste_rate:.1f}% of sales"),
            ("Est. Cost Lost", f"${est_cost:,.0f}", None),
            ("Est. Kg Wasted", f"{est_kg:,.0f}", None),
            ("Est. Meals Lost", f"{est_meals:,}", None),
        ]
    )

    st.markdown("###")

    col1, col2 = st.columns([3, 2])
    with col1:
        st.markdown("#### Waste Trend")
        chart_desc(
            "Red bars show daily waste. The orange line is a 7-day rolling average — watch its direction. Rising = waste getting worse. Falling = your efforts are working."
        )
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=daily["date"],
                y=daily["wasted"],
                name="Daily Waste",
                marker_color=BRAND_RED,
                opacity=0.5,
            )
        )
        fig.add_trace(
            go.Scatter(
                x=daily["date"],
                y=daily["wasted"].rolling(7).mean(),
                name="7-day Moving Avg",
                line=dict(color=BRAND_ORANGE, width=2.5),
            )
        )
        apply_chart_style(
            fig, 350, title="Daily Waste Over Time", yaxis_title="Units Wasted", legend=dict(orientation="h", y=1.1)
        )
        st.plotly_chart(fig, width="stretch")

    with col2:
        st.markdown("#### Waste by Day of Week")
        chart_desc(
            "Which days have the most waste? If weekends are high, you may be over-ordering for Saturday. If Mondays spike, weekend leftovers are expiring."
        )
        daily_copy = daily.copy()
        daily_copy["date"] = daily_copy["date"].astype("datetime64[ns]")
        daily_copy["dow"] = daily_copy["date"].dt.day_name()
        dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        dow_agg = daily_copy.groupby("dow").agg(avg_waste=("wasted", "mean")).reindex(dow_order).reset_index()

        fig = px.bar(
            dow_agg,
            x="dow",
            y="avg_waste",
            color="avg_waste",
            color_continuous_scale=["#D1FAE5", "#EF4444"],
            title="Avg Daily Waste by Weekday",
        )
        apply_chart_style(fig, 350, coloraxis_showscale=False)
        st.plotly_chart(fig, width="stretch")

    st.markdown("#### Waste by Category")
    chart_desc(
        "Left chart: total waste per category (darker = higher waste rate). Right chart: bubble plot showing categories with both high sales AND high waste — those are your biggest opportunities."
    )
    waste_cat = Q.get_waste_by_category(store_id)
    if not waste_cat.empty:
        col1, col2 = st.columns(2)
        with col1:
            fig = px.bar(
                waste_cat,
                x="category",
                y="wasted",
                color="waste_rate",
                color_continuous_scale=["#D1FAE5", "#EF4444"],
                title="Total Waste per Category",
            )
            apply_chart_style(fig, 320)
            st.plotly_chart(fig, width="stretch")

        with col2:
            fig = px.scatter(
                waste_cat,
                x="sold",
                y="wasted",
                size="waste_rate",
                color="category",
                text="category",
                color_discrete_sequence=COLOR_PALETTE,
                title="Sales vs Waste — Category Hotspots",
            )
            fig.update_traces(textposition="top center")
            apply_chart_style(fig, 320, xaxis_title="Total Sold", yaxis_title="Total Wasted", showlegend=False)
            st.plotly_chart(fig, width="stretch")

    st.markdown("#### Top Wasted Products")
    chart_desc(
        "The products costing you the most in waste, ranked by estimated dollar loss. Target the top 3-5 items for immediate action — even small improvements here make a big impact."
    )
    top = Q.get_top_wasted_products(store_id, limit=15)
    if not top.empty:
        fig = px.bar(
            top,
            y="product",
            x="waste_cost",
            orientation="h",
            color="category",
            color_discrete_sequence=COLOR_PALETTE,
            title="Waste Cost by Product ($)",
        )
        apply_chart_style(fig, 450, yaxis=dict(autorange="reversed"), xaxis_title="Est. Cost ($)")
        st.plotly_chart(fig, width="stretch")

    st.markdown("#### Waste Savings Calculator")
    chart_desc(
        "Slide the target to see how much you'd save by reducing waste. For example, a 20% reduction in waste could save thousands per month — use this to set goals for your team."
    )
    col1, col2, col3 = st.columns(3)
    with col1:
        target_reduction = st.slider("Target Waste Reduction", 5, 50, 20, 5, format="%d%%")
    with col2:
        avg_unit_cost = st.number_input("Avg Unit Cost ($)", 1.0, 20.0, 3.50, 0.50)
    with col3:
        st.markdown("###")
        saved_units = int(total_wasted * target_reduction / 100)
        saved_cost = saved_units * avg_unit_cost
        st.metric("Projected Savings", f"${saved_cost:,.0f}", f"{saved_units:,} units saved")
