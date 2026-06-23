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

st.set_page_config(
    page_title="Argus — Threat Detection",
    page_icon="👁️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        "<h1 style='font-size:1.8em; margin-bottom:0'>👁️ ARGUS</h1>"
        "<p style='color:#94a3b8; margin-top:0; font-size:0.9em'>"
        "Insider Threat Detection</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    api_url = st.text_input(
        "API URL",
        value=os.environ.get("ARGUS_API_URL", "http://localhost:8000"),
        help="Base URL of the running Argus API server.",
    )
    os.environ["ARGUS_API_URL"] = api_url

    auto_refresh = st.toggle("Auto-refresh", value=False)
    refresh_interval = 30
    if auto_refresh:
        refresh_interval = st.slider(
            "Refresh interval (s)", min_value=10, max_value=60, value=30, step=5
        )

    st.divider()
    health = get_health()
    render_system_status(health)

# ── Auto-refresh ─────────────────────────────────────────────────────────────

if auto_refresh:
    try:
        from streamlit_autorefresh import st_autorefresh  # type: ignore
        st_autorefresh(interval=refresh_interval * 1000, key="argus_refresh")
    except ImportError:
        st.sidebar.warning(
            "Install `streamlit-autorefresh` to enable auto-refresh.",
            icon="⚠️",
        )

# ── Home page ─────────────────────────────────────────────────────────────────

st.markdown(
    "<h2 style='margin-bottom:4px'>Security Operations Centre</h2>",
    unsafe_allow_html=True,
)
st.caption(
    "Argus monitors user behaviour and detects insider threats in real time. "
    "Use the sidebar to navigate between views."
)

st.divider()

# Pull live summary data
stats = get_alert_stats()
metrics_data = get_metrics()

total_events_today = stats.get("total_events_today", 0)
alerts_today = stats.get("alerts_today", 0)
critical_today = stats.get("critical_count", 0)
users_tracked = metrics_data.get("total_users_tracked", 0)

if health.get("status") == "unreachable":
    st.warning(
        "⚠️ Cannot reach the Argus API at **{}**. "
        "Ensure the server is running (`argus-serve`) and the URL above is correct.".format(
            api_url
        ),
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
