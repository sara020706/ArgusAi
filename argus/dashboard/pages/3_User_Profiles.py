"""User Profiles page — per-user behavioral baseline and activity history.

Search for a user or click one from the known-users list to view their
behavioral profile, activity timeline, and risk summary.
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from argus.dashboard.api_client import (
    get_all_users,
    get_user_events,
    get_user_profile,
    get_user_risk_summary,
)
from argus.dashboard.components.charts import (
    download_trend_chart,
    risk_score_timeline,
)
from argus.dashboard.components.metric_cards import render_metric_row
from argus.dashboard.components.risk_badge import render_risk_badge, risk_emoji

st.set_page_config(page_title="User Profiles — Argus", page_icon="👤", layout="wide")
st.title("👤 User Profiles")
st.caption("Inspect an individual user's behavioral baseline, activity history, and current risk posture.")


def _fmt_ts(ts: str | None) -> str:
    if not ts:
        return "—"
    try:
        return datetime.fromisoformat(ts[:19]).strftime("%b %d, %Y %H:%M")
    except Exception:
        return ts


# ── User selection ────────────────────────────────────────────────────────────

search_col, btn_col = st.columns([5, 1])
with search_col:
    user_input = st.text_input("User ID", placeholder="Type a user ID and click Load")
with btn_col:
    st.markdown("<br>", unsafe_allow_html=True)
    load_clicked = st.button("Load Profile", use_container_width=True)

# Maintain selected user in session state
if load_clicked and user_input.strip():
    st.session_state["selected_user"] = user_input.strip()

selected_user: str | None = st.session_state.get("selected_user")

# ── Known-users list (shown when no user is selected) ─────────────────────────

if not selected_user:
    st.divider()
    st.subheader("Known Users")
    users = get_all_users()
    if not users:
        st.info("No users found in the system yet. Score some events first.")
    else:
        cols = st.columns(min(len(users), 6))
        for i, uid in enumerate(users):
            with cols[i % 6]:
                if st.button(uid, key=f"user_btn_{uid}", use_container_width=True):
                    st.session_state["selected_user"] = uid
                    st.rerun()
    st.stop()

# ── Fetch data for selected user ──────────────────────────────────────────────

profile  = get_user_profile(selected_user)
events   = get_user_events(selected_user, limit=50)
summary  = get_user_risk_summary(selected_user)

if st.button("← Back to user list"):
    del st.session_state["selected_user"]
    st.rerun()

if profile is None:
    st.warning(f"No profile found for user **{selected_user}**.")
    st.stop()

st.markdown(
    f"<h3 style='margin-bottom:0'>🔍 {selected_user}</h3>",
    unsafe_allow_html=True,
)
st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────

tab1, tab2, tab3 = st.tabs(["🧠 Behavioral Profile", "📈 Activity Timeline", "⚠️ Risk Summary"])

with tab1:
    col_l, col_r = st.columns(2)

    with col_l:
        st.subheader("Identity")
        known_ips = profile.get("known_ips", [])
        known_dev = profile.get("known_devices", [])
        last_seen = _fmt_ts(profile.get("last_seen"))
        evt_count = profile.get("event_count", 0)
        mature    = profile.get("profile_mature", False)

        st.markdown(f"**Event count:** {evt_count}")
        st.markdown(f"**Last seen:** {last_seen}")
        st.markdown(
            f"**Profile mature:** "
            + ("✅ Yes" if mature else "⚠️ No (< 20 events)"),
        )
        st.markdown(f"**Known IPs ({len(known_ips)}):**")
        for ip in known_ips:
            st.code(ip, language=None)
        st.markdown(f"**Known Devices ({len(known_dev)}):**")
        for dev in known_dev:
            st.code(dev, language=None)

    with col_r:
        st.subheader("Behavioral Baseline")
        st.metric("Avg Download", f"{profile.get('avg_download_mb', 0):.1f} MB")
        st.metric("Std Download",  f"{profile.get('std_download_mb', 0):.1f} MB")
        st.metric("Avg Files Accessed", f"{profile.get('avg_files_accessed', 0):.1f}")
        st.metric("Std Files Accessed", f"{profile.get('std_files_accessed', 0):.1f}")

with tab2:
    if not events:
        st.info("No event history available.")
    else:
        risk_score_timeline(events)
        download_trend_chart(events)

with tab3:
    if summary is None:
        st.info("No risk summary available.")
    else:
        trend   = summary.get("risk_trend", "stable")
        last_sc = summary.get("last_risk_score")
        last_lv = summary.get("last_risk_level", "—")
        hi_cnt  = summary.get("recent_high_alerts", 0)

        trend_emoji = {"increasing": "📈", "decreasing": "📉", "stable": "➡️"}.get(trend, "➡️")

        render_metric_row([
            {"label": "Recent High Alerts", "value": hi_cnt,                        "delta": None},
            {"label": "Last Risk Score",    "value": f"{last_sc:.0f}" if last_sc is not None else "—", "delta": None},
            {"label": "Risk Trend",         "value": f"{trend_emoji} {trend.capitalize()}", "delta": None},
        ])

        if last_lv and last_lv != "—":
            st.markdown(
                f"**Last Risk Level:** {render_risk_badge(last_lv)}",
                unsafe_allow_html=True,
            )

        st.divider()
        st.subheader("Last 10 Events")
        if events:
            rows = []
            for e in events[:10]:
                level = e.get("risk_level", "LOW")
                rows.append({
                    "Time":    _fmt_ts(e.get("timestamp", "")),
                    "Action":  e.get("action", "—"),
                    "Risk":    f"{risk_emoji(level)} {level}",
                    "Score":   f"{e.get('risk_score', 0):.0f}",
                    "IP":      e.get("ip", "—"),
                })
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.info("No events recorded.")
