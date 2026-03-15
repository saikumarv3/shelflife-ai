"""Page 7: Smart Recommendations — AI-generated actions grouped by urgency."""

import plotly.express as px
import streamlit as st

from dashboard import queries as Q
from dashboard.styles import BRAND_ACCENT, BRAND_ORANGE, BRAND_RED, apply_chart_style, chart_desc, kpi_card_row, page_header


def render(store_id: int):
    page_header(
        "💡",
        "Smart Recommendations",
        "The AI analyzes your inventory, forecasts, and waste patterns to suggest specific actions. "
        "High-priority items at the top can save you the most money if acted on quickly.",
    )

    df = Q.get_recommendations(store_id)

    if df.empty:
        st.markdown(
            """
        <div style="background:var(--secondary-background-color); border:1px solid rgba(128,128,128,0.2); border-radius:12px;
             padding:40px; text-align:center; margin:20px 0;">
            <div style="font-size:3rem; margin-bottom:16px;">💡</div>
            <div style="font-size:1.2rem; font-weight:600; margin-bottom:8px;">
                No Recommendations Yet
            </div>
            <div style="opacity:0.6; max-width:500px; margin:0 auto;">
                The AI engine analyzes current inventory levels, demand forecasts, and waste patterns
                to generate smart recommendations. Check back after the system processes your store data —
                actions like markdowns, reorder adjustments, and donations will appear here automatically.
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )
        return

    total = len(df)
    pending = len(df[df["status"] == "pending"])
    accepted = len(df[df["status"] == "accepted"])
    expected_savings = float(df["expected_cost_saved_usd"].sum())
    actual_savings = float(df["actual_cost_saved_usd"].fillna(0).sum())

    kpi_card_row(
        [
            ("Total Actions", f"{total}", f"{pending} pending"),
            ("Accepted", f"{accepted}", f"{accepted / max(total, 1):.0%} rate"),
            ("Expected Savings", f"${expected_savings:,.0f}", None),
            ("Realized Savings", f"${actual_savings:,.0f}", None),
        ]
    )

    st.markdown("###")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Actions by Type")
        chart_desc(
            "What kinds of actions is the AI suggesting? Darker green = higher expected savings. Markdown = discount to move product. Donate = redirect to food banks before expiry."
        )
        by_action = (
            df.groupby("action_type")
            .agg(
                count=("rec_id", "count"),
                savings=("expected_cost_saved_usd", "sum"),
            )
            .reset_index()
        )
        fig = px.bar(
            by_action,
            x="action_type",
            y="count",
            color="savings",
            color_continuous_scale=["#D1FAE5", BRAND_ACCENT],
            title="Recommendation Types",
        )
        apply_chart_style(fig, 300)
        st.plotly_chart(fig, width="stretch")

    with col2:
        st.markdown("#### Status Breakdown")
        chart_desc(
            "How many recommendations have been accepted, are still pending, or were rejected. A low acceptance rate means either the AI needs tuning or the team needs training."
        )
        by_status = df.groupby("status").size().reset_index(name="count")
        status_colors = {"pending": BRAND_ORANGE, "accepted": BRAND_ACCENT, "rejected": BRAND_RED, "expired": "#94A3B8"}
        fig = px.pie(
            by_status, names="status", values="count", title="Action Status", color="status", color_discrete_map=status_colors
        )
        apply_chart_style(fig, 300)
        st.plotly_chart(fig, width="stretch")

    st.markdown("#### Recommendations by Priority")
    chart_desc(
        "Grouped by potential dollar impact. Start with High Priority — these items have the biggest savings opportunity if you act today. Expand each group to see the specific products and actions."
    )

    high_urgency = df[df["expected_cost_saved_usd"] >= df["expected_cost_saved_usd"].quantile(0.75)]
    medium_urgency = df[
        (df["expected_cost_saved_usd"] >= df["expected_cost_saved_usd"].quantile(0.25))
        & (df["expected_cost_saved_usd"] < df["expected_cost_saved_usd"].quantile(0.75))
    ]
    low_urgency = df[df["expected_cost_saved_usd"] < df["expected_cost_saved_usd"].quantile(0.25)]

    for label, subset in [
        ("High Priority", high_urgency),
        ("Medium Priority", medium_urgency),
        ("Low Priority", low_urgency),
    ]:
        if not subset.empty:
            with st.expander(
                f"{label} — {len(subset)} actions (${float(subset['expected_cost_saved_usd'].sum()):,.0f} potential savings)",
                expanded=(label == "High Priority"),
            ):
                display = subset[
                    [
                        "product",
                        "category",
                        "action_type",
                        "expected_waste_reduction",
                        "expected_cost_saved_usd",
                        "status",
                        "date",
                    ]
                ].copy()
                display.columns = ["Product", "Category", "Action", "Waste Reduction", "Savings ($)", "Status", "Date"]
                st.dataframe(display, width="stretch", hide_index=True)

    st.markdown("#### Savings Tracker")
    chart_desc(
        "Once recommendations are accepted, track cumulative savings over time. The green line shows expected savings, orange shows actual realized savings. The gap shows unrealized potential."
    )
    if accepted > 0:
        savings_data = df[df["status"] == "accepted"].copy()
        if not savings_data.empty:
            savings_data["date"] = savings_data["date"].astype("datetime64[ns]")
            savings_by_date = (
                savings_data.groupby("date")
                .agg(
                    expected=("expected_cost_saved_usd", "sum"),
                    actual=("actual_cost_saved_usd", "sum"),
                )
                .reset_index()
            )
            savings_by_date["cumulative_expected"] = savings_by_date["expected"].cumsum()
            savings_by_date["cumulative_actual"] = savings_by_date["actual"].cumsum()

            fig = px.line(
                savings_by_date,
                x="date",
                y=["cumulative_expected", "cumulative_actual"],
                title="Cumulative Savings Over Time ($)",
                color_discrete_sequence=[BRAND_ACCENT, BRAND_ORANGE],
            )
            apply_chart_style(fig, 300, yaxis_title="Savings ($)", legend=dict(orientation="h", y=1.1))
            st.plotly_chart(fig, width="stretch")
    else:
        st.info("Accept some recommendations to start tracking savings over time.")
