"""Overview page — high-level threat summary.

Shows a table of recent alerts, an alert distribution pie chart,
a top-users ranking, and a full hourly activity heatmap to reveal
when anomalous behaviour is most likely to occur.
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from argus.dashboard.api_client import get_alerts
from argus.dashboard.components.charts import (
    hourly_activity_heatmap,
    risk_distribution_pie,
    top_users_bar,
)
from argus.dashboard.components.risk_badge import render_risk_badge, risk_emoji

st.set_page_config(page_title="Overview — Argus", page_icon="📊", layout="wide")
st.title("📊 Overview")
st.caption("High-level summary of recent threat activity across all monitored users.")


def _fmt_ts(ts: str) -> str:
    """Format an ISO timestamp to a human-friendly string."""
    try:
        dt = datetime.fromisoformat(ts[:19])
        return dt.strftime("%b %d, %Y %H:%M")
    except Exception:
        return ts or "—"


def _top_reason(alert: dict) -> str:
    """Extract the first (highest-weight) reason from an alert."""
    reasons = alert.get("reasons", [])
    return reasons[0] if reasons else "—"


# ── Fetch data ────────────────────────────────────────────────────────────────

col_refresh, _ = st.columns([1, 8])
with col_refresh:
    if st.button("🔄 Refresh"):
        st.cache_data.clear()

alerts = get_alerts(limit=100, min_risk_level="LOW")
recent_alerts = get_alerts(limit=20, min_risk_level="MEDIUM")

if not alerts:
    st.warning("⚠️ No alert data available. Is the Argus API running?")
    st.stop()

# ── Layout: two columns ───────────────────────────────────────────────────────

left, right = st.columns([6, 4])

with left:
    st.subheader("Recent Alerts")
    if recent_alerts:
        table_rows = []
        for a in recent_alerts:
            level = a.get("risk_level", "LOW")
            table_rows.append(
                {
                    "Time":       _fmt_ts(a.get("timestamp", "")),
                    "User":       a.get("user_id", "—"),
                    "Risk":       f"{risk_emoji(level)} {level}",
                    "Score":      f"{a.get('risk_score', 0):.0f}",
                    "Top Reason": _top_reason(a),
                }
            )
        st.dataframe(
            table_rows,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Risk": st.column_config.TextColumn("Risk Level", width="small"),
                "Score": st.column_config.TextColumn("Score", width="small"),
            },
        )
    else:
        st.info("No MEDIUM+ alerts in the last 20 records.")

with right:
    st.subheader("Alert Distribution")
    risk_distribution_pie(alerts)

    st.subheader("Top Users by Alert Count")
    top_users_bar(alerts)

# ── Full-width heatmap ────────────────────────────────────────────────────────

st.divider()
st.subheader("Hourly Activity Heatmap")
hourly_activity_heatmap(alerts)
st.caption(
    "Each cell shows how many events were recorded at a given hour of the day "
    "for each day of the week. Darker red indicates higher event concentration."
)
