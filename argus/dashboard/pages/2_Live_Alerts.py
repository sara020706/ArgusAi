"""Live Alerts page — drill down into individual scored events.

Provides filtering by risk level and user, then renders each matching alert
as an expandable row with a contribution breakdown chart.
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from argus.dashboard.api_client import get_alerts
from argus.dashboard.components.charts import reasons_breakdown_bar
from argus.dashboard.components.risk_badge import render_risk_badge, risk_emoji

st.set_page_config(page_title="Live Alerts — Argus", page_icon="🚨", layout="wide")
st.title("🚨 Live Alerts")
st.caption("Drill into individual scored events. Expand any row to see contributing factors and raw details.")


def _fmt_ts(ts: str) -> str:
    try:
        return datetime.fromisoformat(ts[:19]).strftime("%b %d, %Y %H:%M")
    except Exception:
        return ts or "—"


# ── Filter bar ────────────────────────────────────────────────────────────────

filter_col1, filter_col2, filter_col3 = st.columns([3, 3, 2])

with filter_col1:
    selected_levels = st.multiselect(
        "Risk Level",
        options=["LOW", "MEDIUM", "HIGH", "CRITICAL"],
        default=["HIGH", "CRITICAL"],
    )

with filter_col2:
    user_filter = st.text_input("Filter by User ID", placeholder="e.g. john")

with filter_col3:
    limit = st.slider("Max Results", min_value=10, max_value=200, value=50, step=10)

# ── Fetch and filter ──────────────────────────────────────────────────────────

min_level = selected_levels[0] if selected_levels else "LOW"
# Fetch with lowest selected level; filter others client-side
_level_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
if selected_levels:
    min_level = min(selected_levels, key=lambda l: _level_order.get(l, 0))

all_alerts = get_alerts(limit=limit, min_risk_level=min_level)

filtered = [
    a for a in all_alerts
    if (not selected_levels or a.get("risk_level") in selected_levels)
    and (not user_filter or user_filter.lower() in str(a.get("user_id", "")).lower())
]

st.caption(f"Showing **{len(filtered)}** alert(s)")

# ── Alert rows ────────────────────────────────────────────────────────────────

if not filtered:
    st.info("No alerts match the current filters.")
    st.stop()

for alert in filtered:
    level    = alert.get("risk_level", "LOW")
    user_id  = alert.get("user_id", "unknown")
    score    = alert.get("risk_score", 0)
    ts       = _fmt_ts(alert.get("timestamp", ""))
    emoji    = risk_emoji(level)

    with st.expander(f"{emoji} {user_id} — {level} ({score:.0f}/100) @ {ts}"):

        left, right = st.columns([1, 1])

        with left:
            st.markdown("**Contributing Factors**")
            reasons = alert.get("reasons", [])
            rule_c  = alert.get("rule_contributions", {})
            stat_c  = alert.get("stat_contributions", {})

            # Merge contributions for point lookup
            all_c: dict = {}
            for k, v in rule_c.items():
                all_c[k] = float(v) if isinstance(v, (int, float)) else float(v[0]) if v else 0
            for k, v in stat_c.items():
                all_c[k] = float(v) if isinstance(v, (int, float)) else float(v[0]) if v else 0

            if reasons:
                for r in reasons:
                    st.markdown(f"- {r}")
            else:
                st.markdown("_No reasons recorded._")

        with right:
            reasons_breakdown_bar(alert)

        with st.expander("Raw event details", expanded=False):
            st.json(alert)
