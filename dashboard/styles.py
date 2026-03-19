"""ShelfLife AI — Premium CSS styles and branding constants."""

BRAND_PRIMARY = "#0F172A"
BRAND_ACCENT = "#10B981"
BRAND_ACCENT_LIGHT = "#D1FAE5"
BRAND_ORANGE = "#F59E0B"
BRAND_RED = "#EF4444"
BRAND_BLUE = "#3B82F6"
BRAND_PURPLE = "#8B5CF6"
BRAND_GRAY = "#64748B"
BRAND_BG = "#F8FAFC"

COLOR_PALETTE = ["#10B981", "#3B82F6", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899", "#06B6D4", "#84CC16"]

PLOTLY_LIGHT = dict(
    font=dict(family="Inter, sans-serif", color="#0F172A", size=13),
    title_font=dict(family="Inter, sans-serif", color="#0F172A", size=16),
    plot_bgcolor="white",
    paper_bgcolor="white",
    xaxis=dict(
        gridcolor="#E2E8F0",
        tickfont=dict(color="#0F172A", size=12),
        title_font=dict(color="#0F172A", size=13),
        linecolor="#CBD5E1",
        linewidth=1,
    ),
    yaxis=dict(
        gridcolor="#E2E8F0",
        tickfont=dict(color="#0F172A", size=12),
        title_font=dict(color="#0F172A", size=13),
        linecolor="#CBD5E1",
        linewidth=1,
    ),
    legend=dict(font=dict(color="#0F172A", size=12)),
    margin=dict(l=60, r=20, t=50, b=50),
    coloraxis=dict(colorbar=dict(tickfont=dict(color="#0F172A"), title_font=dict(color="#0F172A"))),
)

PLOTLY_DARK = dict(
    font=dict(family="Inter, sans-serif", color="#E2E8F0", size=13),
    title_font=dict(family="Inter, sans-serif", color="#F1F5F9", size=16),
    plot_bgcolor="#1E293B",
    paper_bgcolor="#0F172A",
    xaxis=dict(
        gridcolor="#334155",
        tickfont=dict(color="#E2E8F0", size=12),
        title_font=dict(color="#F1F5F9", size=13),
        linecolor="#475569",
        linewidth=1,
    ),
    yaxis=dict(
        gridcolor="#334155",
        tickfont=dict(color="#E2E8F0", size=12),
        title_font=dict(color="#F1F5F9", size=13),
        linecolor="#475569",
        linewidth=1,
    ),
    legend=dict(font=dict(color="#E2E8F0", size=12)),
    margin=dict(l=60, r=20, t=50, b=50),
    coloraxis=dict(colorbar=dict(tickfont=dict(color="#E2E8F0"), title_font=dict(color="#F1F5F9"))),
)

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

/* ─── Root ──────────────────────────────── */
.stApp { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }

/* ─── Remove default top gap above header ── */
.block-container {
    padding-top: 1rem !important;
}
section[data-testid="stMain"] > div:first-child {
    padding-top: 0 !important;
}

/* ─── Sidebar ───────────────────────────── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0B1120 0%, #0F172A 40%, #162032 100%) !important;
    border-right: 1px solid rgba(51, 65, 85, 0.5);
}
section[data-testid="stSidebar"] > div:first-child {
    background: transparent !important;
    padding-top: 0 !important;
}

/* Sidebar text defaults */
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    color: #94A3B8 !important;
}

/* ── Fully hide radio circles/dots ─────── */
section[data-testid="stSidebar"] .stRadio [role="radiogroup"] > label > div:first-child {
    display: none !important;
}
section[data-testid="stSidebar"] .stRadio [role="radiogroup"] > label {
    padding-left: 0 !important;
}

/* ── Nav item styling ──────────────────── */
section[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] {
    gap: 1px !important;
}
section[data-testid="stSidebar"] .stRadio [role="radiogroup"] > label {
    display: flex !important;
    align-items: center !important;
    padding: 9px 14px !important;
    border-radius: 8px !important;
    transition: all 0.12s ease !important;
    font-size: 0.88rem !important;
    font-weight: 500 !important;
    color: #94A3B8 !important;
    cursor: pointer !important;
    border-left: 3px solid transparent !important;
    margin: 0 !important;
}
section[data-testid="stSidebar"] .stRadio [role="radiogroup"] > label:hover {
    background: rgba(16, 185, 129, 0.06) !important;
    color: #CBD5E1 !important;
}

/* Active nav item */
section[data-testid="stSidebar"] .stRadio [role="radiogroup"] > label:has(input:checked) {
    background: rgba(16, 185, 129, 0.12) !important;
    color: #10B981 !important;
    font-weight: 600 !important;
    border-left: 3px solid #10B981 !important;
}

section[data-testid="stSidebar"] hr {
    border-color: rgba(51, 65, 85, 0.4) !important;
    margin: 10px 0 !important;
}

/* Sidebar selectbox */
section[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background: rgba(30, 41, 59, 0.7) !important;
    border-color: #334155 !important;
    border-radius: 8px !important;
    color: #E2E8F0 !important;
}

/* Sidebar toggle */
section[data-testid="stSidebar"] .stToggle label span {
    color: #94A3B8 !important;
    font-size: 0.82rem !important;
}

/* ─── KPI Cards ─────────────────────────── */
div[data-testid="stMetric"] {
    background: var(--secondary-background-color) !important;
    border: 1px solid rgba(128,128,128,0.12);
    border-radius: 12px;
    padding: 18px 20px;
    min-height: 110px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}
div[data-testid="stMetric"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 14px rgba(0,0,0,0.10);
}
div[data-testid="stMetric"] label {
    font-weight: 500 !important;
    font-size: 0.76rem !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    opacity: 0.65;
}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-weight: 700 !important;
    font-size: 1.6rem !important;
}
div[data-testid="stMetric"] [data-testid="stMetricDelta"] {
    font-size: 0.78rem !important;
    opacity: 0.6;
}
div[data-testid="stMetric"] [data-testid="stMetricDelta"] svg { display: none; }

/* ─── Equal-width KPI columns ───────────── */
div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] { flex: 1 1 0; min-width: 0; }

/* ─── Dataframes ────────────────────────── */
.stDataFrame { border-radius: 12px; overflow: hidden; }

/* ─── Tabs ──────────────────────────────── */
.stTabs [data-baseweb="tab-list"] { gap: 4px; }
.stTabs [data-baseweb="tab"] { border-radius: 8px 8px 0 0; font-weight: 500; padding: 8px 20px; }
.stTabs [aria-selected="true"] { background: #10B981 !important; color: white !important; }

/* ─── Selectbox ─────────────────────────── */
div[data-baseweb="select"] > div { border-radius: 8px !important; }

/* ─── Expander ──────────────────────────── */
details summary { font-weight: 600; }

/* ─── Scrollbar (sidebar) ───────────────── */
section[data-testid="stSidebar"] ::-webkit-scrollbar { width: 4px; }
section[data-testid="stSidebar"] ::-webkit-scrollbar-track { background: transparent; }
section[data-testid="stSidebar"] ::-webkit-scrollbar-thumb { background: #334155; border-radius: 4px; }
</style>
"""


def inject_css():
    """Inject custom CSS into the Streamlit app."""
    import streamlit as st

    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def is_dark_charts() -> bool:
    """Check if the user toggled dark charts in the sidebar."""
    import streamlit as st

    return st.session_state.get("chart_dark", True)


def apply_chart_style(fig, height: int = 350, **overrides):
    """Apply consistent styling to any Plotly figure, adapting to the dark charts toggle."""
    import copy

    source = PLOTLY_DARK if is_dark_charts() else PLOTLY_LIGHT
    base = copy.deepcopy(source)
    base["height"] = height

    if "title" not in overrides and not fig.layout.title.text:
        base["title"] = None

    for key, val in overrides.items():
        if isinstance(val, dict) and key in base and isinstance(base[key], dict):
            base[key].update(val)
        else:
            base[key] = val

    fig.update_layout(**base)
    return fig


def chart_desc(text: str):
    """Render a business-friendly description below a section heading."""
    import streamlit as st

    st.markdown(
        f"<p style='opacity:0.65; font-size:0.88rem; margin:-8px 0 14px 0; line-height:1.5;'>{text}</p>",
        unsafe_allow_html=True,
    )


def page_header(icon: str, title: str, subtitle: str):
    """Render a compact page header — smaller than the app brand."""
    import streamlit as st

    st.markdown(
        f"<div style='margin-bottom:2px;'>"
        f"<span style='font-size:1.15rem; font-weight:700;'>{icon} {title}</span>"
        f"</div>"
        f"<p style='font-size:0.82rem; opacity:0.55; margin:0 0 10px 0;'>{subtitle}</p>",
        unsafe_allow_html=True,
    )
    st.divider()


def kpi_card_row(metrics: list[tuple[str, str, str | None]]):
    """Render a row of KPI cards. Each tuple: (label, value, delta)."""
    import streamlit as st

    cols = st.columns(len(metrics))
    for col, (label, value, delta) in zip(cols, metrics):
        col.metric(label, value, delta)
