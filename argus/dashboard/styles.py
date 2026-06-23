"""Shared visual system for the Argus dashboard.

A light, calm B2B-SaaS aesthetic built for SOC analysts: white card surfaces on
a cool off-white ground, an indigo/violet signal accent, a disciplined semantic
risk ramp, and Inter for content with a monospace face reserved for data values.

All pages call :func:`inject_global_css` once at the top; the design tokens live
in CSS custom properties on ``:root`` so every page and component inherits them.
"""

import streamlit as st

# ── Design tokens (mirrored as CSS vars in inject_global_css) ──────────────────

GROUND   = "#F7F8FB"   # app background — cool off-white
SURFACE  = "#FFFFFF"   # cards
SURFACE_2 = "#F1F3F9"  # subtle inset / table header
BORDER   = "#E6E9F0"   # hairline borders
BORDER_2 = "#D7DCE8"   # stronger borders
TEXT     = "#0F172A"   # primary text
TEXT_2   = "#475569"   # secondary text
TEXT_3   = "#94A3B8"   # muted / captions
ACCENT   = "#6366F1"   # indigo — primary signal
ACCENT_2 = "#7C3AED"   # violet — DNA / heatmap

RISK = {
    "LOW":      "#16A34A",
    "MEDIUM":   "#D97706",
    "HIGH":     "#DC2626",
    "CRITICAL": "#7C3AED",
}
RISK_SOFT = {  # tinted backgrounds for badges
    "LOW":      "#ECFDF3",
    "MEDIUM":   "#FFFAEB",
    "HIGH":     "#FEF3F2",
    "CRITICAL": "#F4F0FE",
}
RISK_BORDER = {
    "LOW":      "#A6F4C5",
    "MEDIUM":   "#FEDF89",
    "HIGH":     "#FECDCA",
    "CRITICAL": "#D9C6FB",
}


def inject_global_css() -> None:
    """Inject the global stylesheet. Call once at the top of every page."""
    st.markdown(
        """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    :root {
        --ground:#F7F8FB; --surface:#FFFFFF; --surface-2:#F1F3F9;
        --border:#E6E9F0; --border-2:#D7DCE8;
        --text:#0F172A; --text-2:#475569; --text-3:#94A3B8;
        --accent:#6366F1; --accent-2:#7C3AED;
        --sans:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
        --mono:'JetBrains Mono',ui-monospace,'SF Mono',Menlo,monospace;
        --shadow-sm:0 1px 2px rgba(16,24,40,.05);
        --shadow-md:0 4px 12px -2px rgba(16,24,40,.08),0 2px 4px -2px rgba(16,24,40,.04);
        --radius:12px;
    }

    /* ── Base ── */
    html, body, [data-testid="stAppViewContainer"] {
        background-color: var(--ground) !important;
        color: var(--text) !important;
        font-family: var(--sans) !important;
        -webkit-font-smoothing: antialiased;
    }
    [data-testid="stAppViewContainer"] * { font-family: var(--sans); }
    .block-container { padding-top: 2.4rem !important; max-width: 1280px; }

    /* ── Hide Streamlit chrome ── */
    #MainMenu, footer, header { visibility: hidden; }
    [data-testid="stToolbar"] { display: none; }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background-color: var(--surface) !important;
        border-right: 1px solid var(--border) !important;
    }
    [data-testid="stSidebar"] * { color: var(--text-2) !important; }

    /* ── Metric cards (st.metric) ── */
    [data-testid="stMetric"] {
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius) !important;
        padding: 18px 20px !important;
        box-shadow: var(--shadow-sm) !important;
        transition: box-shadow .18s ease, border-color .18s ease;
    }
    [data-testid="stMetric"]:hover {
        box-shadow: var(--shadow-md) !important;
        border-color: var(--border-2) !important;
    }
    [data-testid="stMetricLabel"] {
        color: var(--text-3) !important;
        font-size: 0.72rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.06em !important;
        font-weight: 600 !important;
    }
    [data-testid="stMetricValue"] {
        color: var(--text) !important;
        font-size: 1.9rem !important;
        font-weight: 700 !important;
        font-family: var(--mono) !important;
        letter-spacing: -0.02em !important;
    }
    [data-testid="stMetricDelta"] { font-size: 0.74rem !important; }

    /* ── Dataframes ── */
    [data-testid="stDataFrame"] {
        border: 1px solid var(--border) !important;
        border-radius: var(--radius) !important;
        overflow: hidden !important;
        box-shadow: var(--shadow-sm) !important;
    }
    .stDataFrame th {
        background: var(--surface-2) !important;
        color: var(--text-3) !important;
        font-size: 0.66rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.06em !important;
        border-bottom: 1px solid var(--border) !important;
        padding: 11px 14px !important;
        font-weight: 600 !important;
    }
    .stDataFrame td {
        color: var(--text-2) !important;
        font-size: 0.82rem !important;
        border-bottom: 1px solid var(--border) !important;
        padding: 10px 14px !important;
        font-family: var(--mono) !important;
    }
    .stDataFrame tr:hover td { background: var(--surface-2) !important; }

    /* ── Buttons ── */
    .stButton > button {
        background: var(--surface) !important;
        border: 1px solid var(--border-2) !important;
        color: var(--text-2) !important;
        border-radius: 8px !important;
        font-size: 0.82rem !important;
        font-weight: 600 !important;
        padding: 7px 16px !important;
        box-shadow: var(--shadow-sm) !important;
        transition: all .15s ease !important;
    }
    .stButton > button:hover {
        border-color: var(--accent) !important;
        color: var(--accent) !important;
        background: #FAFAFF !important;
    }
    .stButton > button:focus-visible {
        outline: 2px solid var(--accent) !important;
        outline-offset: 2px !important;
    }

    /* ── Inputs ── */
    .stTextInput input, .stNumberInput input,
    .stSelectbox div[data-baseweb="select"] > div,
    .stMultiSelect div[data-baseweb="select"] > div {
        background: var(--surface) !important;
        border: 1px solid var(--border-2) !important;
        border-radius: 8px !important;
        color: var(--text) !important;
        font-size: 0.85rem !important;
    }
    .stTextInput input:focus { border-color: var(--accent) !important; }
    label, .stTextInput label, .stSelectbox label, .stSlider label,
    .stMultiSelect label, .stNumberInput label {
        color: var(--text-2) !important;
        font-size: 0.78rem !important;
        font-weight: 600 !important;
    }

    /* ── Multiselect tags ── */
    .stMultiSelect [data-baseweb="tag"] {
        background: #EEF0FF !important;
        color: var(--accent) !important;
        border-radius: 6px !important;
    }

    /* ── Sliders ── */
    .stSlider [data-baseweb="slider"] [role="slider"] { background: var(--accent) !important; }

    /* ── Expanders ── */
    [data-testid="stExpander"] {
        border: 1px solid var(--border) !important;
        border-radius: var(--radius) !important;
        background: var(--surface) !important;
        box-shadow: var(--shadow-sm) !important;
        margin-bottom: 8px !important;
    }
    [data-testid="stExpander"] summary {
        font-family: var(--mono) !important;
        font-size: 0.8rem !important;
        color: var(--text-2) !important;
        padding: 12px 16px !important;
    }
    [data-testid="stExpander"] summary:hover { color: var(--accent) !important; }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        background: transparent !important;
        border-bottom: 1px solid var(--border) !important;
        gap: 4px !important;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent !important;
        color: var(--text-3) !important;
        font-size: 0.78rem !important;
        font-weight: 600 !important;
        padding: 9px 16px !important;
        border-bottom: 2px solid transparent !important;
        letter-spacing: 0.02em !important;
    }
    .stTabs [aria-selected="true"] {
        color: var(--accent) !important;
        border-bottom: 2px solid var(--accent) !important;
    }

    /* ── Code blocks ── */
    .stCodeBlock, pre {
        border-radius: 10px !important;
        border: 1px solid var(--border) !important;
    }

    /* ── Divider ── */
    hr {
        border: none !important;
        border-top: 1px solid var(--border) !important;
        margin: 24px 0 !important;
    }

    /* ── Scrollbar ── */
    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: #D7DCE8; border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: #C2C9D8; }

    /* ── Risk badges ── */
    .badge {
        display: inline-flex; align-items: center; gap: 5px;
        padding: 3px 9px; border-radius: 999px;
        font-size: 0.66rem; font-weight: 700; letter-spacing: 0.04em;
        text-transform: uppercase; font-family: var(--sans);
        border: 1px solid transparent;
    }
    .badge-low      { background:#ECFDF3; color:#067647; border-color:#A6F4C5; }
    .badge-medium   { background:#FFFAEB; color:#B54708; border-color:#FEDF89; }
    .badge-high     { background:#FEF3F2; color:#B42318; border-color:#FECDCA; }
    .badge-critical { background:#F4F0FE; color:#6927DA; border-color:#D9C6FB; }

    /* ── Stat bar ── */
    .stat-bar-bg { background:#EDEFF5; border-radius:999px; height:6px; width:100%; overflow:hidden; }
    .stat-bar-fill { height:6px; border-radius:999px; transition: width .6s ease; }

    /* ── Cards & primitives (utility classes used by pages) ── */
    .card {
        background: var(--surface); border:1px solid var(--border);
        border-radius: var(--radius); box-shadow: var(--shadow-sm);
        overflow: hidden;
    }
    .card-pad { padding: 18px 20px; }

    /* ── Page header ── */
    .page-eyebrow {
        font-size: 0.7rem; font-weight: 700; color: var(--accent);
        text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 6px;
    }
    .page-title {
        font-size: 1.6rem; font-weight: 800; color: var(--text);
        letter-spacing: -0.025em; margin: 0 0 2px;
    }
    .page-subtitle {
        font-size: 0.86rem; color: var(--text-3); margin-bottom: 22px; font-weight: 500;
    }
    .section-label {
        font-size: 0.72rem; font-weight: 700; color: var(--text-2);
        text-transform: uppercase; letter-spacing: 0.07em; margin-bottom: 10px;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )


# ── Shared render helpers ──────────────────────────────────────────────────────

def render_kpi_row(stats: list) -> None:
    """Row of KPI metric cards. Each dict: label, value, sublabel (optional)."""
    if not stats:
        return
    cols = st.columns(len(stats))
    for col, s in zip(cols, stats):
        with col:
            st.metric(
                label=s.get("label", ""),
                value=s.get("value", "—"),
                delta=s.get("sublabel"),
            )


def render_page_header(title: str, subtitle: str, eyebrow: str = "Argus") -> None:
    """Page eyebrow + title + subtitle block."""
    st.markdown(
        f'<div class="page-eyebrow">{eyebrow}</div>'
        f'<div class="page-title">{title}</div>'
        f'<div class="page-subtitle">{subtitle}</div>',
        unsafe_allow_html=True,
    )


def section_label(label: str) -> None:
    """Render a small uppercase section label."""
    st.markdown(f'<div class="section-label">{label}</div>', unsafe_allow_html=True)


def empty_state(message: str = "No data available") -> None:
    """Render a styled empty-state placeholder."""
    st.markdown(
        f"""
    <div style="text-align:center;padding:44px 20px;color:var(--text-3);
    border:1px dashed var(--border-2);border-radius:var(--radius);background:var(--surface)">
    <div style="font-size:1.4rem;margin-bottom:8px;opacity:.5">&#9678;</div>
    <div style="font-size:0.84rem">{message}</div>
    </div>
    """,
        unsafe_allow_html=True,
    )


def fmt_ts(ts_str: str) -> str:
    """Format ISO timestamp as '23 Jun 02:15'."""
    try:
        from datetime import datetime

        dt = datetime.fromisoformat(str(ts_str).replace("Z", "+00:00"))
        return dt.strftime("%d %b %H:%M").lstrip("0")
    except Exception:
        try:
            return str(ts_str)[:16].replace("T", " ")
        except Exception:
            return str(ts_str)
