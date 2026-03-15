"""Page 8: Model Performance — MAPE trend, scatter plot, feature store stats, drift alerts."""

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard import queries as Q
from dashboard.styles import (
    BRAND_ACCENT,
    BRAND_BLUE,
    BRAND_ORANGE,
    BRAND_RED,
    apply_chart_style,
    chart_desc,
    kpi_card_row,
    page_header,
)


def render(store_id: int):
    page_header(
        "🤖",
        "Model Performance",
        "How accurate is the AI? This page tracks prediction quality over time. "
        "If accuracy drops below thresholds, the system automatically flags it for retraining.",
    )

    accuracy = Q.get_prediction_accuracy(store_id)

    if accuracy.empty:
        st.info("No prediction data available. Run the forecast pipeline to generate predictions, then check back.")
        _render_feature_store()
        _render_alerts()
        return

    avg_mape = float(accuracy["mape"].mean())
    best_day = accuracy.loc[accuracy["mape"].idxmin()]
    worst_day = accuracy.loc[accuracy["mape"].idxmax()]
    total_preds = int(accuracy["actual"].count())

    kpi_card_row(
        [
            ("Avg MAPE", f"{avg_mape:.1f}%", "lower is better"),
            ("Best Day", f"{float(best_day['mape']):.1f}%", str(best_day["date"])),
            ("Worst Day", f"{float(worst_day['mape']):.1f}%", str(worst_day["date"])),
            ("Forecast Days", f"{total_preds}", None),
        ]
    )
    chart_desc(
        f"The AI averages {avg_mape:.1f}% error. Below 15% is considered good for grocery demand forecasting. "
        f"The best day was {float(best_day['mape']):.1f}% — the model can be very accurate when patterns are stable."
    )

    st.markdown("###")

    col1, col2 = st.columns([3, 2])
    with col1:
        st.markdown("#### MAPE Over Time")
        chart_desc(
            "Daily prediction error. The red dashed line at 20% is the alert threshold — days above it trigger automatic model review. "
            "The orange dotted line is the average. Look for trends: is accuracy improving or degrading?"
        )
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=accuracy["date"],
                y=accuracy["mape"],
                line=dict(color=BRAND_BLUE, width=2),
                name="Daily MAPE",
            )
        )
        fig.add_hline(y=20, line_dash="dash", line_color=BRAND_RED, annotation_text="Alert (20%)")
        fig.add_hline(y=avg_mape, line_dash="dot", line_color=BRAND_ORANGE, annotation_text=f"Avg ({avg_mape:.1f}%)")
        apply_chart_style(fig, 380, title="Prediction Error Over Time", yaxis_title="MAPE (%)")
        st.plotly_chart(fig, width="stretch")

    with col2:
        st.markdown("#### Actual vs Predicted")
        chart_desc(
            "Each dot is one day's total. Dots close to the diagonal line = accurate predictions. "
            "Dots above the line = AI over-predicted (you ordered too much). Below = under-predicted (you may have run out)."
        )
        fig = px.scatter(
            accuracy,
            x="actual",
            y="predicted",
            title="Forecast Accuracy Scatter",
            color_discrete_sequence=[BRAND_ACCENT],
            opacity=0.7,
        )
        max_val = max(accuracy["actual"].max(), accuracy["predicted"].max()) * 1.1
        fig.add_trace(
            go.Scatter(
                x=[0, max_val],
                y=[0, max_val],
                mode="lines",
                line=dict(color="#CBD5E1", dash="dash"),
                name="Perfect prediction",
            )
        )
        apply_chart_style(fig, 380, xaxis_title="Actual Units", yaxis_title="Predicted Units")
        st.plotly_chart(fig, width="stretch")

    st.markdown("#### Error Distribution")
    chart_desc(
        "Left: how many days fall into each error bucket. Most days should be under 10%. "
        "Right: color-coded accuracy bands — green is excellent, red needs investigation."
    )
    col1, col2 = st.columns(2)
    with col1:
        fig = px.histogram(
            accuracy, x="mape", nbins=25, color_discrete_sequence=[BRAND_BLUE], title="MAPE Distribution (# of Days)"
        )
        fig.add_vline(x=20, line_dash="dash", line_color=BRAND_RED, annotation_text="Threshold")
        apply_chart_style(fig, 280, xaxis_title="MAPE (%)", yaxis_title="Days")
        st.plotly_chart(fig, width="stretch")

    with col2:
        accuracy_copy = accuracy.copy()
        accuracy_copy["error_band"] = accuracy_copy["mape"].apply(
            lambda x: "< 5%" if x < 5 else "5-10%" if x < 10 else "10-20%" if x < 20 else "> 20%"
        )
        band_counts = accuracy_copy.groupby("error_band").size().reset_index(name="days")
        band_order = ["< 5%", "5-10%", "10-20%", "> 20%"]
        fig = px.bar(
            band_counts,
            x="error_band",
            y="days",
            color="error_band",
            color_discrete_map={"< 5%": BRAND_ACCENT, "5-10%": BRAND_BLUE, "10-20%": BRAND_ORANGE, "> 20%": BRAND_RED},
            title="Accuracy Bands (Days per Band)",
            category_orders={"error_band": band_order},
        )
        apply_chart_style(fig, 280, showlegend=False)
        st.plotly_chart(fig, width="stretch")

    _render_feature_store()
    _render_alerts()


def _render_feature_store():
    st.markdown("#### Feature Store Health")
    chart_desc(
        "The feature store is the data the AI uses to make predictions. It should cover all your stores, all products, and recent dates. "
        "If the date range is stale or row count is low, the model may be using outdated information."
    )
    stats = Q.get_feature_store_stats()
    if not stats.empty:
        r = stats.iloc[0]
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Feature Rows", f"{int(r['total_rows']):,}")
        col2.metric("Products", int(r["products"]))
        col3.metric("Stores", int(r["stores"]))
        col4.metric("Date Range", f"{r['first_date']} → {r['last_date']}")
    else:
        st.info("Feature store is empty. Run the feature engineering pipeline.")


def _render_alerts():
    st.markdown("#### System Alerts")
    chart_desc(
        "Automated alerts from the MLOps pipeline. Red = critical (model performance dropped significantly). "
        "Yellow = warning (data drift detected). Blue = informational (model retrained or promoted)."
    )
    alerts = Q.get_alerts()
    if not alerts.empty:
        for _, a in alerts.iterrows():
            severity = a["severity"]
            icon = "🔴" if severity == "critical" else "🟡" if severity == "warning" else "🔵"
            st.markdown(
                f"{icon} **{a['alert_type']}** — {a['message']}  \n<small style='opacity:0.5;'>{a['created_at']}</small>",
                unsafe_allow_html=True,
            )
    else:
        st.success("No alerts — all systems healthy. The AI is performing within expected parameters.")
