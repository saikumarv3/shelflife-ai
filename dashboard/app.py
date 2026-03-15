"""ShelfLife AI — Premium Dashboard.

AI-powered inventory intelligence for grocery retail.
Reduces food waste, optimizes demand forecasting, and maximizes profit.
"""

from datetime import date

import streamlit as st

from dashboard import queries as Q
from dashboard.styles import inject_css
from dashboard.views import (
    demand_forecast,
    home,
    inventory_health,
    model_performance,
    product_catalog,
    recommendations,
    store_overview,
    waste_analytics,
)

st.set_page_config(
    page_title="ShelfLife AI — Smart Inventory Intelligence",
    page_icon="🥬",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()

PAGES = {
    "📊  Command Center": "home",
    "🏪  Store Overview": "store",
    "🛒  Product Catalog": "catalog",
    "📦  Inventory Health": "inventory",
    "📈  Demand Forecast": "demand",
    "🗑️  Waste Analytics": "waste",
    "💡  Recommendations": "recs",
    "🤖  Model Performance": "model",
}


def _section_label(text: str):
    """Tiny uppercase section label for sidebar groups."""
    st.markdown(
        f"<p style='font-size:0.6rem; text-transform:uppercase; letter-spacing:0.12em; "
        f"color:#475569; font-weight:700; margin:0 0 6px 2px; padding:0;'>{text}</p>",
        unsafe_allow_html=True,
    )


def sidebar():
    with st.sidebar:
        # ── Store selector at the very top — most important for a manager ──
        stores = Q.get_stores()
        if not stores.empty:
            st.markdown(
                "<div style='padding:16px 10px 4px 10px;'>"
                "<p style='font-size:0.58rem; text-transform:uppercase; letter-spacing:0.12em; "
                "color:#475569; font-weight:700; margin:0 0 6px 0;'>Active Store</p>"
                "</div>",
                unsafe_allow_html=True,
            )
            store_id = st.selectbox(
                "store",
                stores["store_id"].tolist(),
                format_func=lambda x: stores.loc[stores["store_id"] == x, "name"].values[0],
                label_visibility="collapsed",
            )
        else:
            store_id = 1

        st.markdown(
            "<div style='margin:6px 12px 10px; height:1px; "
            "background:linear-gradient(90deg, #10B981, rgba(51,65,85,0.2));'></div>",
            unsafe_allow_html=True,
        )

        # ── Navigation ──
        _section_label("Menu")
        page = st.radio("nav", list(PAGES.keys()), label_visibility="collapsed")

        st.divider()

        # ── Display Settings ──
        _section_label("Display")
        dark_charts = st.toggle("🌙 Dark Charts", value=True, key="dark_charts")
        st.session_state["chart_dark"] = dark_charts

        # ── Footer ──
        st.markdown(
            "<div style='"
            "margin-top:24px; padding:14px 12px 10px 12px; "
            "border-top:1px solid rgba(51,65,85,0.35); text-align:center;"
            "'>"
            "<div style='font-size:0.6rem; color:#475569; line-height:1.9; letter-spacing:0.02em;'>"
            "<span style='color:#10B981;'>XGBoost</span> · "
            "<span style='color:#3B82F6;'>LightGBM</span> · "
            "<span style='color:#F59E0B;'>MLflow</span><br>"
            "FastAPI · Streamlit · PostgreSQL<br>"
            f"<span style='color:#334155;'>v1.0 · {date.today().strftime('%b %Y')}</span>"
            "</div></div>",
            unsafe_allow_html=True,
        )

    return PAGES[page], store_id


def header_bar(store_id: int):
    """Branded top header bar."""
    stores = Q.get_stores()
    store_name = "All Stores"
    if not stores.empty and store_id in stores["store_id"].values:
        store_name = stores.loc[stores["store_id"] == store_id, "name"].values[0]

    today_str = date.today().strftime("%b %d, %Y")

    html = (
        "<div style='"
        "background:linear-gradient(135deg, #0B1120 0%, #162032 50%, #0F172A 100%);"
        "border:1px solid rgba(51,65,85,0.35); border-radius:14px;"
        "padding:20px 30px; margin-bottom:22px;"
        "display:flex; justify-content:space-between; align-items:center;"
        "flex-wrap:wrap; gap:16px;"
        "'>"
        # left — logo + tagline
        "<div style='display:flex; align-items:center; gap:16px;'>"
        "<div style='"
        "width:48px; height:48px; border-radius:12px;"
        "background:linear-gradient(135deg, #10B981, #059669);"
        "display:flex; align-items:center; justify-content:center;"
        "font-size:1.6rem; flex-shrink:0;"
        "box-shadow:0 3px 10px rgba(16,185,129,0.3);"
        "'>🥬</div>"
        "<div>"
        "<div style='font-size:1.55rem; font-weight:800; color:#F8FAFC; letter-spacing:-0.02em; line-height:1.15;'>"
        "ShelfLife <span style='color:#10B981;'>AI</span>"
        "</div>"
        "<div style='font-size:0.82rem; color:#64748B; margin-top:3px;'>"
        "AI-powered demand forecasting &amp; waste prevention"
        "</div>"
        "<a href='https://chotulab.com' target='_blank' style='"
        "display:inline-flex; align-items:center; gap:5px; margin-top:6px;"
        "font-size:0.68rem; font-weight:600; color:#475569; text-decoration:none;"
        "background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08);"
        "border-radius:20px; padding:3px 10px; transition:color 0.2s;"
        "letter-spacing:0.04em;"
        "'>"
        "<span style='font-size:0.6rem;'>⚗️</span> by ChoutuLab"
        "</a>"
        "</div></div>"
        # right — context pills
        "<div style='display:flex; gap:12px; align-items:center; flex-wrap:wrap;'>"
        "<div style='"
        "background:rgba(30,41,59,0.6); border:1px solid rgba(51,65,85,0.5);"
        "border-radius:8px; padding:7px 16px; text-align:center;"
        "'>"
        "<div style='font-size:0.55rem; text-transform:uppercase; letter-spacing:0.1em; color:#475569; margin-bottom:2px;'>Store</div>"
        f"<div style='font-size:0.88rem; font-weight:600; color:#10B981;'>{store_name}</div>"
        "</div>"
        "<div style='"
        "background:rgba(30,41,59,0.6); border:1px solid rgba(51,65,85,0.5);"
        "border-radius:8px; padding:7px 16px; text-align:center;"
        "'>"
        "<div style='font-size:0.55rem; text-transform:uppercase; letter-spacing:0.1em; color:#475569; margin-bottom:2px;'>Date</div>"
        f"<div style='font-size:0.88rem; font-weight:600; color:#E2E8F0;'>{today_str}</div>"
        "</div>"
        "<div style='"
        "background:linear-gradient(135deg, #10B981, #059669);"
        "color:white; padding:5px 14px; border-radius:20px;"
        "font-size:0.62rem; font-weight:700; letter-spacing:0.06em;"
        "text-transform:uppercase; box-shadow:0 2px 6px rgba(16,185,129,0.3);"
        "display:flex; align-items:center; gap:5px;"
        "'>"
        "<span style='display:inline-block; width:6px; height:6px; border-radius:50%; background:white;'></span>"
        "Live</div>"
        "</div></div>"
    )

    st.markdown(html, unsafe_allow_html=True)


def scroll_to_top():
    """Scroll to top using an anchor element at the start of main content."""
    st.markdown("<div id='shelflife-top'></div>", unsafe_allow_html=True)
    js = (
        "<script>"
        "var attempts = 0;"
        "function scrollUp() {"
        "  var el = document.getElementById('shelflife-top');"
        "  if (el) { el.scrollIntoView({behavior: 'instant', block: 'start'}); return; }"
        "  var main = document.querySelector('section[data-testid=\"stMain\"]');"
        "  if (main) { main.scrollTop = 0; }"
        "  window.scrollTo(0,0);"
        "  document.documentElement.scrollTop = 0;"
        "  if (++attempts < 5) setTimeout(scrollUp, 100);"
        "}"
        "scrollUp();"
        "</script>"
    )
    st.markdown(js, unsafe_allow_html=True)


def _render_page(page_key: str, store_id: int):
    if page_key == "home":
        home.render(store_id)
    elif page_key == "store":
        store_overview.render(store_id)
    elif page_key == "catalog":
        product_catalog.render(store_id)
    elif page_key == "inventory":
        inventory_health.render(store_id)
    elif page_key == "demand":
        demand_forecast.render(store_id)
    elif page_key == "waste":
        waste_analytics.render(store_id)
    elif page_key == "recs":
        recommendations.render(store_id)
    elif page_key == "model":
        model_performance.render(store_id)


def main():
    page_key, store_id = sidebar()
    scroll_to_top()
    header_bar(store_id)
    _render_page(page_key, store_id)


if __name__ == "__main__":
    main()
