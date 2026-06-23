"""User Profiles page — per-user behavioral baseline and activity history."""

from __future__ import annotations

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
from argus.dashboard.components.risk_badge import render_risk_badge
from argus.dashboard.styles import empty_state, fmt_ts, inject_global_css, render_kpi_row, render_page_header, section_label

st.set_page_config(page_title="User Profiles — Argus AI", page_icon="⬡", layout="wide")
inject_global_css()

render_page_header("User Profiles", "behavioral baselines")

st.markdown('<hr style="border:none;border-top:1px solid #1e293b;margin:16px 0"/>', unsafe_allow_html=True)

# ── Two-column layout ─────────────────────────────────────────────────────────

col_users, col_detail = st.columns([30, 70])

with col_users:
    section_label("Users")

    search = st.text_input("Search", placeholder="Filter users...", label_visibility="collapsed")

    try:
        all_users = get_all_users()
    except Exception:
        all_users = []

    filtered_users = [u for u in all_users if not search or search.lower() in u.lower()]

    if not filtered_users:
        st.markdown(
            '<div style="font-size:0.72rem;color:#334155;padding:8px 0">No users found</div>',
            unsafe_allow_html=True,
        )
    else:
        for uid in filtered_users:
            is_selected = st.session_state.get("selected_user") == uid
            btn_style = "border-color:#7c3aed !important; color:#a78bfa !important;" if is_selected else ""
            if st.button(uid, key=f"user_btn_{uid}", use_container_width=True):
                st.session_state["selected_user"] = uid
                st.rerun()

with col_detail:
    selected_user: str | None = st.session_state.get("selected_user")

    if not selected_user:
        empty_state("Select a user to view their profile")
    else:
        # Back button
        if st.button("← Back"):
            del st.session_state["selected_user"]
            st.rerun()

        # Fetch data
        try:
            profile = get_user_profile(selected_user)
        except Exception:
            profile = None
        try:
            events = get_user_events(selected_user, limit=50)
        except Exception:
            events = []
        try:
            summary = get_user_risk_summary(selected_user)
        except Exception:
            summary = None

        if profile is None:
            st.markdown(
                f'<div style="background:#1c0a0a;border:1px solid #991b1b;border-radius:8px;'
                f'padding:12px 16px;color:#f87171;font-size:0.82rem">'
                f'No profile found for user <code>{selected_user}</code>.</div>',
                unsafe_allow_html=True,
            )
        else:
            evt_count = profile.get("event_count", len(events))
            last_level = (summary or {}).get("last_risk_level", "LOW")
            badge = render_risk_badge(last_level)

            # User header
            st.markdown(
                f'<div style="margin-bottom:16px">'
                f'<span style="font-size:1rem;font-weight:700;color:#f1f5f9;'
                f'font-family:monospace">{selected_user}</span>'
                f'&nbsp;&nbsp;{badge}'
                f'&nbsp;&nbsp;<span style="font-size:0.72rem;color:#475569">'
                f'{evt_count} events</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # KPI row
            avg_dl = profile.get("avg_download_mb", 0) or 0
            std_dl = profile.get("std_download_mb", 0) or 0
            avg_files = profile.get("avg_files_accessed", 0) or 0
            render_kpi_row([
                {"label": "Avg Download",  "value": f"{avg_dl:.1f} MB"},
                {"label": "Std Download",  "value": f"{std_dl:.1f} MB"},
                {"label": "Avg Files",     "value": f"{avg_files:.1f}"},
                {"label": "Event Count",   "value": evt_count},
            ])

            st.markdown('<hr style="border:none;border-top:1px solid #1e293b;margin:16px 0"/>', unsafe_allow_html=True)

            # Tabs
            tab_baseline, tab_activity, tab_risk = st.tabs(["BASELINE", "ACTIVITY", "RISK SUMMARY"])

            with tab_baseline:
                b_left, b_right = st.columns(2)

                with b_left:
                    section_label("Known IPs")
                    known_ips = profile.get("known_ips", []) or []
                    if known_ips:
                        for ip in known_ips:
                            st.markdown(
                                f'<code style="display:inline-block;background:#0a0f1e;'
                                f'border:1px solid #1e293b;border-radius:4px;padding:2px 8px;'
                                f'font-size:0.75rem;color:#94a3b8;margin:2px 0">{ip}</code>',
                                unsafe_allow_html=True,
                            )
                    else:
                        st.markdown('<span style="font-size:0.72rem;color:#334155">None recorded</span>', unsafe_allow_html=True)

                    st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)
                    section_label("Known Devices")
                    known_dev = profile.get("known_devices", []) or []
                    if known_dev:
                        for dev in known_dev:
                            st.markdown(
                                f'<code style="display:inline-block;background:#0a0f1e;'
                                f'border:1px solid #1e293b;border-radius:4px;padding:2px 8px;'
                                f'font-size:0.75rem;color:#94a3b8;margin:2px 0">{dev}</code>',
                                unsafe_allow_html=True,
                            )
                    else:
                        st.markdown('<span style="font-size:0.72rem;color:#334155">None recorded</span>', unsafe_allow_html=True)

                with b_right:
                    section_label("Profile Maturity")
                    mature = profile.get("profile_mature", False)
                    maturity_pct = 100 if mature else max(5, int(evt_count / 20 * 100))
                    maturity_color = "#4ade80" if mature else "#fbbf24"
                    maturity_label = "MATURE" if mature else f"{min(maturity_pct, 99)}%"
                    st.markdown(
                        f'<div style="margin-bottom:6px">'
                        f'<div style="background:#1e293b;border-radius:4px;height:6px;overflow:hidden">'
                        f'<div style="width:{min(maturity_pct,100)}%;height:6px;background:{maturity_color};'
                        f'border-radius:4px;transition:width 0.6s ease"></div></div>'
                        f'<div style="font-size:0.65rem;color:{maturity_color};margin-top:4px;'
                        f'font-family:monospace">{maturity_label}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    last_seen = fmt_ts(str(profile.get("last_seen", "")))
                    st.markdown(
                        f'<div style="margin-top:12px;font-size:0.75rem;color:#64748b">'
                        f'Last seen: <span style="color:#94a3b8;font-family:monospace">{last_seen}</span></div>',
                        unsafe_allow_html=True,
                    )

            with tab_activity:
                if events:
                    risk_score_timeline(events, title="Risk Score Timeline")
                    download_trend_chart(events, title="Download Volume")
                else:
                    empty_state("No event history available")

            with tab_risk:
                if summary is None:
                    empty_state("No risk summary available")
                else:
                    trend     = summary.get("risk_trend", "stable") or "stable"
                    last_sc   = summary.get("last_risk_score")
                    last_lv   = summary.get("last_risk_level", "—") or "—"
                    hi_cnt    = summary.get("recent_high_alerts", 0) or 0

                    trend_arrow = {"increasing": "↑", "decreasing": "↓", "stable": "→"}.get(trend, "→")
                    trend_color = {"increasing": "#f87171", "decreasing": "#4ade80", "stable": "#fbbf24"}.get(trend, "#64748b")

                    render_kpi_row([
                        {"label": "Recent High Alerts", "value": hi_cnt},
                        {"label": "Last Score",         "value": f"{last_sc:.0f}/100" if last_sc is not None else "—"},
                        {"label": "Trend",              "value": f"{trend_arrow} {trend.capitalize()}"},
                    ])

                    st.markdown('<hr style="border:none;border-top:1px solid #1e293b;margin:16px 0"/>', unsafe_allow_html=True)
                    section_label("Last 10 Events")

                    if events:
                        rows_html = []
                        for e in events[:10]:
                            lvl   = e.get("risk_level", "LOW")
                            sc    = float(e.get("risk_score", 0))
                            ts    = fmt_ts(str(e.get("timestamp", "")))
                            act   = str(e.get("action", "—"))[:30]
                            ip    = str(e.get("ip", "—"))
                            lcolor = {"LOW": "#4ade80", "MEDIUM": "#fbbf24", "HIGH": "#f87171", "CRITICAL": "#c084fc"}.get(lvl, "#64748b")
                            rows_html.append(
                                f'<div style="display:grid;grid-template-columns:120px 1fr 60px 120px;'
                                f'gap:8px;padding:6px 8px;border-bottom:1px solid #0f172a;'
                                f'font-size:0.75rem;font-family:monospace;align-items:center">'
                                f'<span style="color:#475569">{ts}</span>'
                                f'<span style="color:#94a3b8">{act}</span>'
                                f'<span style="color:{lcolor}">{sc:.0f}</span>'
                                f'<span style="color:#475569">{ip}</span>'
                                f'</div>'
                            )
                        st.markdown(
                            '<div style="background:#0f1629;border:1px solid #1e293b;border-radius:8px;overflow:hidden">'
                            + "".join(rows_html)
                            + "</div>",
                            unsafe_allow_html=True,
                        )
                    else:
                        empty_state("No events recorded")
