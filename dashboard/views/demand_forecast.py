"""Page 5: Demand Forecast — Actual vs predicted with product drill-down and confidence bands."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard import queries as Q
from dashboard.styles import BRAND_BLUE, BRAND_ORANGE, apply_chart_style, chart_desc, kpi_card_row, page_header


def render(store_id: int):
    page_header(
        "📈",
        "Demand Forecast",
        "See how well the AI predicts demand. The closer the predicted line follows the actual line, the more you can trust it for ordering decisions.",
    )

    categories = Q.get_categories()
    date_min, date_max = Q.get_date_range()

    col1, col2, col3 = st.columns(3)
    with col1:
        cat_filter = st.selectbox("Category", ["All"] + categories["name"].tolist(), key="dem_cat")
    with col2:
        d_from = st.date_input("From", value=pd.Timestamp(date_min), key="dem_from")
    with col3:
        d_to = st.date_input("To", value=pd.Timestamp(date_max), key="dem_to")

    cat_arg = cat_filter if cat_filter != "All" else None
    df = Q.get_demand_data(store_id, str(d_from), str(d_to), cat_arg)

    if df.empty:
        st.info("No data for selected filters. Run the forecast pipeline to generate predictions.")
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
                ("Date Range", f"{d_from} to {d_to}", None),
                ("Predictions", "0 — run forecast", None),
            ]
        )

    st.markdown("###")

    agg_mode = st.radio("Aggregation", ["Daily Total", "By Product"], horizontal=True, key="dem_agg")

    if agg_mode == "Daily Total":
        chart_desc(
            "Blue solid line = actual sales. Orange dashed line = AI prediction. Shaded band = 95% confidence range. "
            "When actual falls inside the band, the model is confident and accurate."
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
                        name="95% Confidence",
                    )
                )

        apply_chart_style(
            fig, 420, title="Daily Demand: Actual vs AI Forecast", yaxis_title="Units Sold", legend=dict(orientation="h", y=1.1)
        )
        st.plotly_chart(fig, width="stretch")

    else:
        chart_desc(
            "Drill into a single product to see how well the AI forecasts it. Use this to decide if you can trust the AI's order recommendation for this specific product."
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
                        name="95% Confidence",
                    )
                )

        apply_chart_style(fig, 400, title=f"Forecast — {selected}", yaxis_title="Units", legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig, width="stretch")

    st.markdown("#### Top Products by Volume")
    chart_desc(
        "Your highest-selling products in the selected date range and category. These are the products where accurate forecasting matters most — even a 5% error can mean big losses."
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
