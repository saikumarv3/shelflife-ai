"""Page 1: Home Dashboard — Store-level overview with KPIs, trends, and scorecards."""

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard import queries as Q
from dashboard.styles import (
    BRAND_ACCENT,
    BRAND_ORANGE,
    BRAND_RED,
    COLOR_PALETTE,
    apply_chart_style,
    chart_desc,
    kpi_card_row,
    page_header,
)


def _product_intro():
    """Clean product intro — always visible, simple language for business audience."""
    st.markdown(
        "<div style='"
        "background:var(--secondary-background-color);"
        "border:1px solid rgba(128,128,128,0.12);"
        "border-left:3px solid #10B981;"
        "border-radius:10px;"
        "padding:18px 24px; margin-bottom:20px; line-height:1.7;"
        "'>"
        "<div style='font-size:1rem; font-weight:700; margin-bottom:8px;'>"
        "Welcome to ShelfLife AI"
        "</div>"
        "<div style='font-size:0.88rem; opacity:0.8;'>"
        "Your AI assistant for smarter grocery inventory. "
        "ShelfLife learns what sells, spots food about to expire, and tells you "
        "exactly what to discount, reorder, or donate — so you "
        "<strong>waste less and sell more</strong>."
        "</div>"
        "<div style='display:flex; flex-wrap:wrap; gap:16px; margin-top:14px; font-size:0.8rem;'>"
        "<span style='opacity:0.7;'>🔮 Demand forecasts</span>"
        "<span style='opacity:0.7;'>🚨 Expiry alerts</span>"
        "<span style='opacity:0.7;'>💡 Action recommendations</span>"
        "<span style='opacity:0.7;'>📊 Multi-store comparison</span>"
        "<span style='opacity:0.7;'>💰 15-25% less waste</span>"
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )


def render(store_id: int):
    _product_intro()

    page_header(
        "📊",
        "Command Center",
        "At-a-glance performance for this store — revenue, sales, waste, and donations.",
    )

    kpi = Q.get_kpi_summary(store_id)
    if kpi.empty:
        st.info("No data available yet. Run the database seeder first.")
        return

    r = kpi.iloc[0]
    total_rev = float(r["total_revenue"] or 0)
    total_sold = int(r["total_sold"] or 0)
    total_wasted = int(r["total_wasted"] or 0)
    waste_pct = float(r["waste_pct"] or 0)
    donated = int(r["total_donated"] or 0)
    days = int(r["days_tracked"] or 0)

    kpi_card_row(
        [
            ("Total Revenue", f"${total_rev:,.0f}", f"{days} days tracked"),
            ("Units Sold", f"{total_sold:,}", None),
            ("Units Wasted", f"{total_wasted:,}", f"-{waste_pct:.1f}% waste rate"),
            ("Units Donated", f"{donated:,}", None),
        ]
    )

    st.markdown("###")

    daily = Q.get_daily_metrics(store_id)
    if not daily.empty:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Revenue Trend")
            chart_desc(
                "How much money is this store making each day? Look for dips — they may signal supply issues or low foot traffic days."
            )
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=daily["date"],
                    y=daily["revenue"],
                    fill="tozeroy",
                    name="Revenue",
                    line=dict(color=BRAND_ACCENT, width=2),
                    fillcolor="rgba(16,185,129,0.1)",
                )
            )
            apply_chart_style(fig, 320, title="Daily Revenue ($)", yaxis_title="Revenue ($)")
            st.plotly_chart(fig, width="stretch")

        with col2:
            st.markdown("#### Waste Trend")
            chart_desc(
                "Daily units thrown away. The orange dotted line is the 7-day average — if it's going up, waste is getting worse and needs attention."
            )
            fig2 = go.Figure()
            fig2.add_trace(
                go.Bar(
                    x=daily["date"],
                    y=daily["wasted"],
                    name="Wasted",
                    marker_color=BRAND_RED,
                    opacity=0.7,
                )
            )
            fig2.add_trace(
                go.Scatter(
                    x=daily["date"],
                    y=daily["wasted"].rolling(7).mean(),
                    name="7-day Avg",
                    line=dict(color=BRAND_ORANGE, width=2, dash="dot"),
                )
            )
            apply_chart_style(
                fig2,
                320,
                title="Daily Waste (units)",
                yaxis_title="Units Wasted",
                showlegend=True,
                legend=dict(orientation="h", y=1.12),
            )
            st.plotly_chart(fig2, width="stretch")

    st.markdown("### 🏪 Store Scorecards")
    chart_desc(
        "Side-by-side comparison of each store. Quickly spot which store has the highest waste rate or lowest revenue — then drill into Store Overview for details."
    )
    stores = Q.get_store_comparison()
    if not stores.empty:
        cols = st.columns(len(stores))
        for col, (_, s) in zip(cols, stores.iterrows()):
            is_active = int(s["store_id"]) == store_id
            border_color = BRAND_ACCENT if is_active else "rgba(128,128,128,0.2)"
            border_width = "2px" if is_active else "1px"
            with col:
                st.markdown(
                    f"""
                <div style="background:var(--secondary-background-color); border:{border_width} solid {border_color}; border-radius:12px;
                     padding:20px; text-align:center; border-top:3px solid {BRAND_ACCENT if is_active else "rgba(128,128,128,0.3)"};">
                    <div style="font-size:1.1rem; font-weight:700;">{s["name"]}</div>
                    <div style="opacity:0.6; font-size:0.8rem; margin-bottom:12px;">{s["location"]} · {s["type"]}</div>
                    <div style="font-size:1.4rem; font-weight:700; color:{BRAND_ACCENT};">${float(s["revenue"]):,.0f}</div>
                    <div style="opacity:0.6; font-size:0.75rem;">Revenue</div>
                    <hr style="margin:10px 0; border-color:rgba(128,128,128,0.2);">
                    <div style="display:flex; justify-content:space-around;">
                        <div><div style="font-weight:600;">{int(s["units_sold"]):,}</div><div style="font-size:0.7rem; opacity:0.6;">Sold</div></div>
                        <div><div style="font-weight:600; color:{BRAND_RED};">{int(s["units_wasted"]):,}</div><div style="font-size:0.7rem; opacity:0.6;">Wasted</div></div>
                        <div><div style="font-weight:600; color:{BRAND_ORANGE};">{float(s["waste_pct"]):.1f}%</div><div style="font-size:0.7rem; opacity:0.6;">Waste</div></div>
                    </div>
                </div>
                """,
                    unsafe_allow_html=True,
                )

    st.markdown("###")

    col1, col2 = st.columns(2)
    waste_cat = Q.get_waste_by_category(store_id)
    if not waste_cat.empty:
        with col1:
            st.markdown("#### Waste by Category")
            chart_desc(
                "Which product categories are wasting the most? Darker red = higher waste rate. Focus reduction efforts on the tallest, darkest bars."
            )
            fig = px.bar(
                waste_cat,
                x="category",
                y="wasted",
                color="waste_rate",
                color_continuous_scale=["#D1FAE5", "#EF4444"],
                title="Units Wasted per Category",
            )
            apply_chart_style(fig, 350)
            st.plotly_chart(fig, width="stretch")

    top_wasted = Q.get_top_wasted_products(store_id=store_id, limit=8)
    if not top_wasted.empty:
        with col2:
            st.markdown("#### Top Wasted Products")
            chart_desc(
                "The products contributing the most to waste. Your #1 targets for markdown, portion adjustment, or donation before expiry."
            )
            fig = px.bar(
                top_wasted,
                y="product",
                x="wasted",
                orientation="h",
                color="category",
                color_discrete_sequence=COLOR_PALETTE,
                title="Most Wasted Products (units)",
            )
            apply_chart_style(fig, 350, yaxis=dict(autorange="reversed"), showlegend=False)
            st.plotly_chart(fig, width="stretch")
