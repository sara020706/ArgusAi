"""Overview page — high-level threat summary."""

from __future__ import annotations

import streamlit as st

from argus.dashboard.api_client import get_alert_stats, get_alerts, get_metrics
from argus.dashboard.components.charts import (
    hourly_activity_heatmap,
    risk_distribution_pie,
    top_users_bar,
)
from argus.dashboard.components.risk_badge import render_risk_badge, render_score_bar
from argus.dashboard.styles import (
    empty_state,
    fmt_ts,
    inject_global_css,
    render_kpi_row,
    render_page_header,
    section_label,
)

st.set_page_config(page_title="Overview — Argus AI", page_icon="⬡", layout="wide")
inject_global_css()

render_page_header("Overview", "threat activity · last 24 hours")

# ── Refresh button ────────────────────────────────────────────────────────────

col_refresh, _ = st.columns([1, 9])
with col_refresh:
    if st.button("Refresh"):
        st.cache_data.clear()

# ── Fetch data ────────────────────────────────────────────────────────────────

try:
    alerts = get_alerts(limit=100, min_risk_level="LOW")
except Exception:
    alerts = []

try:
    recent_alerts = get_alerts(limit=20, min_risk_level="MEDIUM")
except Exception:
    recent_alerts = []

try:
    stats = get_alert_stats()
except Exception:
    stats = {}

try:
    metrics_data = get_metrics()
except Exception:
    metrics_data = {}

# ── KPI row ───────────────────────────────────────────────────────────────────

total_events = stats.get("total_events_today", len(alerts))
active_alerts = stats.get("alerts_today", len(recent_alerts))
critical_count = stats.get("critical_count", sum(1 for a in alerts if a.get("risk_level") == "CRITICAL"))
users_tracked = metrics_data.get("total_users_tracked", len({a.get("user_id") for a in alerts if a.get("user_id")}))

render_kpi_row([
    {"label": "Total Events",    "value": total_events},
    {"label": "Active Alerts",   "value": active_alerts},
    {"label": "Critical",        "value": critical_count},
    {"label": "Users Tracked",   "value": users_tracked},
])

st.markdown('<hr style="border:none;border-top:1px solid #1e293b;margin:20px 0"/>', unsafe_allow_html=True)

# ── Two-column layout ─────────────────────────────────────────────────────────

left, right = st.columns([55, 45])

with left:
    section_label("Recent Alerts")
    if recent_alerts:
        rows_html = []
        for a in recent_alerts:
            level = a.get("risk_level", "LOW")
            score = float(a.get("risk_score", 0))
            user  = a.get("user_id", "—")
            ts    = fmt_ts(a.get("timestamp", ""))
            badge = render_risk_badge(level)
            bar   = render_score_bar(score, level)
            reasons = a.get("reasons", [])
            top_reason = str(reasons[0])[:60] if reasons else "—"

            rows_html.append(f"""
            <div style="padding:10px 12px;border-bottom:1px solid #0f172a;
                        display:grid;grid-template-columns:1fr 80px 110px 1fr;
                        gap:12px;align-items:center;font-size:0.8rem">
                <div style="font-family:monospace;color:#94a3b8">{user}</div>
                <div>{badge}</div>
                <div style="font-family:monospace;color:#64748b">
                    <div style="color:#f1f5f9;font-weight:700">{score:.0f}/100</div>
                    {bar}
                </div>
                <div style="color:#475569;font-size:0.72rem">{top_reason}</div>
            </div>
            """)

        table_html = (
            '<div style="background:#0f1629;border:1px solid #1e293b;border-radius:8px;overflow:hidden">'
            '<div style="padding:8px 12px;background:#0a0f1e;border-bottom:1px solid #1e293b;'
            'display:grid;grid-template-columns:1fr 80px 110px 1fr;gap:12px">'
            '<span style="font-size:0.6rem;font-weight:700;color:#334155;text-transform:uppercase;letter-spacing:0.1em">User</span>'
            '<span style="font-size:0.6rem;font-weight:700;color:#334155;text-transform:uppercase;letter-spacing:0.1em">Level</span>'
            '<span style="font-size:0.6rem;font-weight:700;color:#334155;text-transform:uppercase;letter-spacing:0.1em">Score</span>'
            '<span style="font-size:0.6rem;font-weight:700;color:#334155;text-transform:uppercase;letter-spacing:0.1em">Top Reason</span>'
            '</div>'
            + "".join(rows_html)
            + '</div>'
        )
        st.markdown(table_html, unsafe_allow_html=True)
    else:
        empty_state("No MEDIUM+ alerts available")

with right:
    risk_distribution_pie(alerts, title="Alert Distribution")
    top_users_bar(alerts, title="Top Users")

# ── Full-width heatmap ────────────────────────────────────────────────────────

st.markdown('<hr style="border:none;border-top:1px solid #1e293b;margin:20px 0"/>', unsafe_allow_html=True)
section_label("Activity Heatmap")
if alerts:
    hourly_activity_heatmap(alerts, title="Hour × Day of Week")
else:
    empty_state("No event data for heatmap")
