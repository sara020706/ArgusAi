"""Argus dashboard — main entry point.

This module configures the Streamlit app, renders the sidebar (API URL,
auto-refresh controls, system status), and displays the home page with a
live summary row. Individual views live in the ``pages/`` sub-directory and
are handled automatically by Streamlit's multi-page routing.
"""

from __future__ import annotations

import os

import streamlit as st

from argus.dashboard.api_client import get_alert_stats, get_health, get_metrics
from argus.dashboard.components.metric_cards import (
    render_metric_row,
    render_system_status,
)
from argus.dashboard.styles import inject_global_css, render_page_header

st.set_page_config(
    page_title="Argus AI",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_global_css()

# ── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        "<h1 style='font-size:1.6rem;font-weight:900;color:#f1f5f9;"
        "letter-spacing:-1px;margin-bottom:0;font-family:monospace'>ARGUS AI</h1>"
        "<p style='color:#475569;margin-top:2px;font-size:0.72rem;"
        "text-transform:uppercase;letter-spacing:0.12em'>Threat Detection</p>",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<hr style="border:none;border-top:1px solid #1e293b;margin:12px 0"/>',
        unsafe_allow_html=True,
    )

    # System status dots
    try:
        health = get_health()
    except Exception:
        health = {"status": "unreachable"}
    render_system_status(health)

    st.markdown(
        '<hr style="border:none;border-top:1px solid #1e293b;margin:12px 0"/>',
        unsafe_allow_html=True,
    )

    # API URL config
    api_url = st.text_input(
        "API URL",
        value=os.environ.get("ARGUS_API_URL", "http://localhost:8000"),
        help="Base URL of the running Argus API server.",
    )
    os.environ["ARGUS_API_URL"] = api_url

    st.markdown(
        '<hr style="border:none;border-top:1px solid #1e293b;margin:12px 0"/>',
        unsafe_allow_html=True,
    )

    # Auto-refresh controls
    auto_refresh = st.toggle("Auto-refresh", value=False)
    refresh_interval = 30
    if auto_refresh:
        refresh_interval = st.slider(
            "Interval (s)", min_value=10, max_value=60, value=30, step=5
        )

    st.markdown(
        '<hr style="border:none;border-top:1px solid #1e293b;margin:12px 0"/>',
        unsafe_allow_html=True,
    )

    # Navigation links
    st.markdown(
        '<p style="font-size:0.6rem;font-weight:700;color:#334155;'
        'text-transform:uppercase;letter-spacing:0.12em;margin-bottom:8px">Navigation</p>',
        unsafe_allow_html=True,
    )
    nav_links = [
        ("Overview",       "pages/1_Overview"),
        ("Live Alerts",    "pages/2_Live_Alerts"),
        ("User Profiles",  "pages/3_User_Profiles"),
        ("Threat Map",     "pages/4_Threat_Map"),
    ]
    for label, _ in nav_links:
        st.markdown(
            f'<div style="padding:4px 0;font-size:0.78rem;color:#64748b">'
            f'&#9656; {label}</div>',
            unsafe_allow_html=True,
        )

    # Version footer pinned at bottom
    st.markdown(
        '<div style="position:fixed;bottom:16px;left:0;width:220px;'
        'text-align:center;font-size:0.6rem;color:#1e293b;font-family:monospace">'
        'ARGUS v0.1.0 · argus-ai</div>',
        unsafe_allow_html=True,
    )

# ── Auto-refresh ─────────────────────────────────────────────────────────────

if auto_refresh:
    try:
        from streamlit_autorefresh import st_autorefresh  # type: ignore
        st_autorefresh(interval=refresh_interval * 1000, key="argus_refresh")
    except ImportError:
        st.sidebar.warning(
            "Install `streamlit-autorefresh` to enable auto-refresh.",
        )

# ── Home page ─────────────────────────────────────────────────────────────────

render_page_header("Security Operations Centre", "argus insider threat detection · live")

# Pull live summary data
try:
    stats = get_alert_stats()
except Exception:
    stats = {}
try:
    metrics_data = get_metrics()
except Exception:
    metrics_data = {}

total_events_today = stats.get("total_events_today", 0)
alerts_today = stats.get("alerts_today", 0)
critical_today = stats.get("critical_count", 0)
users_tracked = metrics_data.get("total_users_tracked", 0)

if health.get("status") == "unreachable":
    st.markdown(
        '<div style="background:#1c0a0a;border:1px solid #991b1b;border-radius:8px;'
        'padding:12px 16px;color:#f87171;font-size:0.82rem;margin-bottom:16px">'
        f'Cannot reach the Argus API at <code>{api_url}</code>. '
        'Ensure the server is running (<code>argus-serve</code>) and the URL above is correct.'
        '</div>',
        unsafe_allow_html=True,
    )
else:
    render_metric_row(
        [
            {"label": "Events Today",     "value": total_events_today, "delta": None},
            {"label": "Active Alerts",    "value": alerts_today,       "delta": None},
            {"label": "Critical Alerts",  "value": critical_today,     "delta": None},
            {"label": "Users Monitored",  "value": users_tracked,      "delta": None},
        ]
    )

    avg_score = metrics_data.get("avg_score_last_100", 0.0)
    uptime = metrics_data.get("engine_uptime_seconds", 0.0)
    uptime_str = f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m"

    st.markdown("")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Avg Score (last 100 events)", f"{avg_score:.1f} / 100")
    with col2:
        st.metric("Engine Uptime", uptime_str)


def main() -> None:
    """CLI entry point for the ``argus-dashboard`` command.

    Launches the Streamlit app from the command line by invoking
    ``streamlit run`` on this file via subprocess.
    """
    import subprocess
    import sys

    dashboard_path = os.path.join(os.path.dirname(__file__), "app.py")
    subprocess.run([sys.executable, "-m", "streamlit", "run", dashboard_path])
