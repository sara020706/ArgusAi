"""Live Alerts page — drill down into individual scored events."""

from __future__ import annotations

import streamlit as st

from argus.dashboard.api_client import get_alerts
from argus.dashboard.components.charts import reasons_breakdown_bar
from argus.dashboard.components.risk_badge import level_border_style, render_risk_badge
from argus.dashboard.styles import empty_state, fmt_ts, inject_global_css, render_page_header, section_label

st.set_page_config(page_title="Live Alerts — Argus AI", page_icon="⬡", layout="wide")
inject_global_css()

render_page_header("Live Alerts", "real-time threat feed")

# ── Filter controls ───────────────────────────────────────────────────────────

fc1, fc2, fc3 = st.columns([3, 3, 2])

with fc1:
    selected_levels = st.multiselect(
        "Risk Level",
        options=["LOW", "MEDIUM", "HIGH", "CRITICAL"],
        default=["HIGH", "CRITICAL"],
    )

with fc2:
    user_filter = st.text_input("Filter by User ID", placeholder="e.g. john")

with fc3:
    limit = st.slider("Max Results", min_value=10, max_value=100, value=25, step=5)

# ── Fetch and filter ──────────────────────────────────────────────────────────

_level_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}

try:
    if selected_levels:
        min_level = min(selected_levels, key=lambda l: _level_order.get(l, 0))
    else:
        min_level = "LOW"
    all_alerts = get_alerts(limit=limit, min_risk_level=min_level)
except Exception:
    all_alerts = []

filtered = [
    a for a in all_alerts
    if (not selected_levels or a.get("risk_level") in selected_levels)
    and (not user_filter or user_filter.lower() in str(a.get("user_id", "")).lower())
]

# ── Alert feed header ─────────────────────────────────────────────────────────

st.markdown('<hr style="border:none;border-top:1px solid #1e293b;margin:16px 0"/>', unsafe_allow_html=True)

col_label, col_count = st.columns([6, 1])
with col_label:
    section_label("Alert Feed")
with col_count:
    st.markdown(
        f'<p style="font-size:0.72rem;color:#475569;text-align:right;margin-top:2px">'
        f'{len(filtered)} result(s)</p>',
        unsafe_allow_html=True,
    )

# Live indicator dot
st.markdown(
    '<span style="display:inline-block;width:6px;height:6px;border-radius:50%;'
    'background:#4ade80;margin-right:6px;vertical-align:middle"></span>'
    '<span style="font-size:0.7rem;color:#4ade80;font-family:monospace">LIVE</span>',
    unsafe_allow_html=True,
)

# ── Alert rows ────────────────────────────────────────────────────────────────

if not filtered:
    empty_state("No alerts match the current filters")
    st.stop()

for alert in filtered:
    level   = alert.get("risk_level", "LOW")
    user_id = alert.get("user_id", "unknown")
    score   = float(alert.get("risk_score", 0))
    ip      = str(alert.get("ip", "—"))
    ts      = fmt_ts(str(alert.get("timestamp", "")))
    border  = level_border_style(level)

    # Build expander title with fixed-width fields
    expander_title = f"{level:<8} {user_id:<12} {score:>3.0f}/100  {ip:<16}  {ts}"

    with st.expander(expander_title):
        # Left border accent via markdown
        if border:
            st.markdown(
                f'<div style="{border}margin-bottom:12px;font-size:0.78rem;color:#64748b">'
                f'{render_risk_badge(level)} &nbsp; {user_id} &nbsp;·&nbsp; {score:.0f}/100</div>',
                unsafe_allow_html=True,
            )

        col_left, col_right = st.columns([1, 1])

        with col_left:
            st.markdown(
                '<p style="font-size:0.65rem;font-weight:700;color:#475569;'
                'text-transform:uppercase;letter-spacing:0.1em;margin-bottom:8px">'
                'Contributing Factors</p>',
                unsafe_allow_html=True,
            )
            reasons = alert.get("reasons", [])
            rule_c  = alert.get("rule_contributions", {}) or {}
            stat_c  = alert.get("stat_contributions", {}) or {}

            if reasons:
                for i, r in enumerate(reasons, 1):
                    st.markdown(
                        f'<div style="font-size:0.78rem;color:#94a3b8;padding:3px 0;font-family:monospace">'
                        f'<span style="color:#334155">{i:02d}.</span> {r}</div>',
                        unsafe_allow_html=True,
                    )
            elif rule_c or stat_c:
                all_c = {}
                for k, v in rule_c.items():
                    all_c[k] = float(v) if isinstance(v, (int, float)) else (float(v[0]) if v else 0)
                for k, v in stat_c.items():
                    all_c[k] = float(v) if isinstance(v, (int, float)) else (float(v[0]) if v else 0)
                for i, (k, pts) in enumerate(sorted(all_c.items(), key=lambda x: -x[1])[:8], 1):
                    label = k.replace("rule_", "").replace("stat_", "").replace("_", " ")
                    st.markdown(
                        f'<div style="font-size:0.78rem;color:#94a3b8;padding:3px 0;font-family:monospace">'
                        f'<span style="color:#334155">{i:02d}.</span> {label} '
                        f'<span style="color:#7c3aed">(+{pts:.0f})</span></div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown(
                    '<span style="font-size:0.78rem;color:#334155;font-style:italic">No reasons recorded.</span>',
                    unsafe_allow_html=True,
                )

        with col_right:
            reasons_breakdown_bar(alert, title="Score Breakdown")

        # Raw JSON
        st.markdown(
            '<p style="font-size:0.65rem;font-weight:700;color:#334155;'
            'text-transform:uppercase;letter-spacing:0.1em;margin:12px 0 4px">Raw Event</p>',
            unsafe_allow_html=True,
        )
        import json
        st.code(json.dumps(alert, indent=2, default=str), language="json")
