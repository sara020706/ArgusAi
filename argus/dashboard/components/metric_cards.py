"""Streamlit metric-card helper components for the Argus dashboard."""

from __future__ import annotations

import streamlit as st


def render_metric_row(metrics: list[dict]) -> None:
    """Render a horizontal row of ``st.metric`` cards.

    Args:
        metrics: List of dicts, each with keys:

            * ``"label"`` (str): Card label.
            * ``"value"`` (str | int | float): Primary display value.
            * ``"delta"`` (str | None): Optional delta string shown below value.

    Example::

        render_metric_row([
            {"label": "Total Events", "value": 1024, "delta": "+12"},
            {"label": "Critical Alerts", "value": 3, "delta": None},
        ])
    """
    if not metrics:
        return
    cols = st.columns(len(metrics))
    for col, m in zip(cols, metrics):
        with col:
            st.metric(
                label=m.get("label", ""),
                value=m.get("value", "—"),
                delta=m.get("delta"),
            )


def render_stat_card(title: str, value: str, color: str) -> None:
    """Render a single coloured stat card using custom HTML.

    Useful for the overview summary row where more visual weight is desired
    than plain ``st.metric`` provides.

    Args:
        title: Short label displayed above the value.
        value: The primary statistic to display (string so caller controls
            formatting).
        color: Hex colour used as the card's left border accent.
    """
    st.markdown(
        f"""
        <div style="
            background: #1e293b;
            border-left: 4px solid {color};
            border-radius: 8px;
            padding: 16px 20px;
            margin-bottom: 8px;
        ">
            <div style="color:#94a3b8; font-size:0.78em; text-transform:uppercase;
                        letter-spacing:0.08em; margin-bottom:4px">{title}</div>
            <div style="color:#f1f5f9; font-size:1.6em; font-weight:700;
                        line-height:1">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_system_status(health: dict) -> None:
    """Render a compact status bar from the ``/health`` response.

    Displays API connection state plus the optional-layer flags
    (ML enabled, threat-intel enabled, DB connected).

    Args:
        health: Dict returned by :func:`~argus.dashboard.api_client.get_health`.
            Gracefully handles missing keys with safe defaults.
    """
    status = health.get("status", "unreachable")
    connected = status == "healthy"

    dot = "🟢" if connected else "🔴"
    label = "API Connected" if connected else "API Unreachable"

    ml_icon      = "✅" if health.get("ml_enabled") else "—"
    ti_icon      = "✅" if health.get("threat_intel_enabled") else "—"
    db_icon      = "✅" if health.get("db_connected") else "❌"

    st.markdown(
        f"""
        <div style="font-size:0.82em; color:#94a3b8; line-height:1.8">
            {dot} <b style="color:#f1f5f9">{label}</b><br>
            ML Layer &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {ml_icon}<br>
            Threat Intel &nbsp; {ti_icon}<br>
            DB &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {db_icon}
        </div>
        """,
        unsafe_allow_html=True,
    )
