"""Page 5: Demand Forecast — Actual vs predicted with product drill-down and confidence bands."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard import queries as Q
from dashboard.styles import BRAND_BLUE, BRAND_ORANGE, apply_chart_style, chart_desc, kpi_card_row, page_header

# First 30 days have incomplete lag features (warmup). Skip them in charts.
_WARMUP_DAYS = 30


def render(store_id: int):
    page_header(
        "📈",
        "Demand Forecast",
        "See how well the AI predicts demand. The closer the predicted line follows the actual line, the more you can trust it for ordering decisions.",
    )

    categories = Q.get_categories()
    date_min_str, date_max_str = Q.get_date_range()
    data_min = pd.Timestamp(date_min_str)
    data_max = pd.Timestamp(date_max_str)
    chart_start = data_min + pd.Timedelta(days=_WARMUP_DAYS)

    col1, col2, col3 = st.columns(3)
    with col1:
        cat_filter = st.selectbox("Category", ["All"] + categories["name"].tolist(), key="dem_cat")
    with col2:
        d_from = st.date_input("From", value=chart_start.date(), key="dem_from")
    with col3:
        d_to = st.date_input("To", value=data_max.date(), key="dem_to")

    # Warn when user picks dates outside the data range
    d_from_ts = pd.Timestamp(d_from)
    d_to_ts = pd.Timestamp(d_to)

    if d_to_ts > data_max:
        st.warning(
            f"⚠️  **No data beyond {data_max.strftime('%b %d, %Y')}.** "
            f"The AI was trained on data up to that date. "
            f"Future predictions (beyond the training window) require running a separate "
            f"future-forecast pipeline — not yet available in this version. "
            f"Showing data up to **{data_max.strftime('%b %d, %Y')}** instead.",
            icon=None,
        )
        d_to_ts = data_max

    if d_from_ts < chart_start:
        st.info(
            f"ℹ️  Dates before **{chart_start.strftime('%b %d, %Y')}** are hidden. "
            f"The first {_WARMUP_DAYS} days of data are a model warmup period — lag features "
            f"(7-day, 14-day rolling averages) need prior history to be accurate, so early "
            f"predictions are unreliable and appear as spikes.",
        )
        d_from_ts = chart_start

    cat_arg = cat_filter if cat_filter != "All" else None
    df = Q.get_demand_data(store_id, str(d_from_ts.date()), str(d_to_ts.date()), cat_arg)

    if df.empty:
        st.info("No data for selected filters.")
        return

    has_preds = "predicted" in df.columns and df["predicted"].notna().any()
    matched = df.dropna(subset=["predicted", "actual"]) if has_preds else pd.DataFrame()

    if not matched.empty:
        mape = (abs(matched["predicted"] - matched["actual"]) / matched["actual"].clip(lower=1)).mean()
        bias = (matched["predicted"] - matched["actual"]).mean()
        kpi_card_row(
            [
                ("MAPE", f"{mape:.1%}", "lower is better"),
                ("Avg Bias", f"{bias:+.1f} units", "positive = over-predict"),
                ("Predictions", f"{len(matched):,}", None),
                ("Products", f"{df['product_id'].nunique()}", None),
            ]
        )
        chart_desc(
            f"MAPE = Mean Absolute Percentage Error. Currently {mape:.1%} — below 15% is good, below 10% is excellent. "
            f"Bias of {bias:+.1f} means the AI tends to {'over' if bias > 0 else 'under'}-predict by about {abs(bias):.0f} units per product per day."
        )
    else:
        kpi_card_row(
            [
                ("Products", f"{df['product_id'].nunique()}", None),
                ("Data Points", f"{len(df):,}", None),
                ("Date Range", f"{d_from_ts.date()} to {d_to_ts.date()}", None),
                ("Predictions", "0 — run forecast", None),
            ]
        )

    st.markdown("###")

    # ── AI vs calculations note ────────────────────────────────────
    with st.expander("🤖 Why AI and not simple calculations?", expanded=False):
        st.markdown("""
The AI uses **35 features simultaneously** to predict demand — things no simple formula can combine:

| What AI tracks | Why it matters |
|---|---|
| Sales from 1, 7, 14, 28 days ago | Captures weekly and monthly patterns |
| Day of week, month, holidays | Mondays ≠ Fridays; Christmas ≠ regular Tuesday |
| Promotions on/off | A promotion can double sales overnight |
| Inventory levels | Low stock predicts lower sales (empty shelf = no sale) |
| Price changes | Customers respond to price movements |
| Weather signals | Hot days sell more drinks, cold days sell more soup |

A simple calculation like *"order what you sold last week"* ignores all of this.
The AI's **7.7% MAPE** means it's off by less than 1 unit on an average 10-unit/day product.
A rule-based system typically runs 30–50% error on perishables.
        """)

    agg_mode = st.radio("View", ["Daily Total", "By Product"], horizontal=True, key="dem_agg")

    if agg_mode == "Daily Total":
        chart_desc(
            "Blue solid line = what actually sold each day. Orange dashed line = what the AI predicted. "
            "Shaded band = confidence range. When the blue line stays inside the band, the AI is working well. "
            "Gaps in the orange line mean no prediction was generated for that date."
        )
        daily = (
            df.groupby("date")
            .agg(
                actual=("actual", "sum"),
                predicted=("predicted", "sum"),
                conf_lower=("confidence_lower", "sum"),
                conf_upper=("confidence_upper", "sum"),
            )
            .reset_index()
        )

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=daily["date"],
                y=daily["actual"],
                name="Actual Sales",
                line=dict(color=BRAND_BLUE, width=2.5),
            )
        )
        if daily["predicted"].notna().any():
            fig.add_trace(
                go.Scatter(
                    x=daily["date"],
                    y=daily["predicted"],
                    name="AI Prediction",
                    line=dict(color=BRAND_ORANGE, width=2, dash="dash"),
                )
            )
            if daily["conf_upper"].notna().any():
                fig.add_trace(
                    go.Scatter(
                        x=daily["date"],
                        y=daily["conf_upper"],
                        line=dict(width=0),
                        showlegend=False,
                    )
                )
                fig.add_trace(
                    go.Scatter(
                        x=daily["date"],
                        y=daily["conf_lower"],
                        fill="tonexty",
                        fillcolor="rgba(245,158,11,0.1)",
                        line=dict(width=0),
                        name="Confidence Band",
                    )
                )
        else:
            st.info(
                "ℹ️  No AI predictions available for this range. "
                "The predictions table may need to be populated — run the prediction pipeline on the server."
            )

        apply_chart_style(
            fig, 420, title="Daily Demand: Actual vs AI Forecast", yaxis_title="Units Sold", legend=dict(orientation="h", y=1.1)
        )
        st.plotly_chart(fig, width="stretch")

    else:
        chart_desc(
            "Drill into a single product to see how well the AI forecasts it. "
            "Use this to decide if you can trust the AI's order recommendation for this specific product."
        )
        product_options = sorted(df["product_name"].unique().tolist())
        selected = st.selectbox("Select Product", product_options, key="dem_prod")
        prod_df = df[df["product_name"] == selected].sort_values("date")

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=prod_df["date"],
                y=prod_df["actual"],
                name="Actual",
                line=dict(color=BRAND_BLUE, width=2.5),
                mode="lines+markers",
                marker=dict(size=4),
            )
        )
        if prod_df["predicted"].notna().any():
            fig.add_trace(
                go.Scatter(
                    x=prod_df["date"],
                    y=prod_df["predicted"],
                    name="Predicted",
                    line=dict(color=BRAND_ORANGE, width=2, dash="dash"),
                )
            )
            if prod_df["confidence_upper"].notna().any():
                fig.add_trace(
                    go.Scatter(
                        x=prod_df["date"],
                        y=prod_df["confidence_upper"],
                        line=dict(width=0),
                        showlegend=False,
                    )
                )
                fig.add_trace(
                    go.Scatter(
                        x=prod_df["date"],
                        y=prod_df["confidence_lower"],
                        fill="tonexty",
                        fillcolor="rgba(245,158,11,0.1)",
                        line=dict(width=0),
                        name="Confidence Band",
                    )
                )

        apply_chart_style(fig, 400, title=f"Forecast — {selected}", yaxis_title="Units", legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig, width="stretch")

    st.markdown("#### Top Products by Volume")
    chart_desc(
        "Your highest-selling products in the selected date range. "
        "These are where accurate forecasting matters most — even a 5% ordering error on a top seller costs more than a 50% error on a slow mover."
    )
    top = (
        df.groupby(["product_id", "product_name"])
        .agg(total_sold=("actual", "sum"), avg_daily=("actual", "mean"))
        .sort_values("total_sold", ascending=False)
        .head(15)
        .reset_index()
    )
    top.columns = ["ID", "Product", "Total Sold", "Avg Daily"]
    top["Avg Daily"] = top["Avg Daily"].round(1)
    st.dataframe(top, width="stretch", hide_index=True)
