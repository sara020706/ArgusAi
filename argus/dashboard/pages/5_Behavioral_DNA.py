"""Behavioral DNA page — per-user behavioral fingerprints and drift detection.

The core of the page is the side-by-side heatmap comparison: an analyst can
instantly see whether this week's activity pattern matches the user's
historical fingerprint, or whether they've stopped being themselves.
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from argus.dashboard.api_client import (
    get_dna_alerts,
    get_dna_summary,
    get_user_dna,
)
from argus.dashboard.styles import (
    empty_state,
    fmt_ts,
    inject_global_css,
    render_page_header,
    section_label,
)

st.set_page_config(page_title="Behavioral DNA — Argus AI", page_icon="⬡", layout="wide")
inject_global_css()

render_page_header("Behavioral DNA", "behavioral fingerprinting · drift detection")

# ── Palette ───────────────────────────────────────────────────────────────────

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
HEATMAP_SCALE = [[0.0, "#0a0f1e"], [0.5, "#1e1b4b"], [1.0, "#7c3aed"]]

_SEV_COLOR = {
    "none":     "#4ade80",
    "low":      "#fbbf24",
    "medium":   "#fb923c",
    "high":     "#f87171",
    "critical": "#c084fc",
}
_SEV_BADGE = {
    "none":     "badge-low",
    "low":      "badge-medium",
    "medium":   "badge-medium",
    "high":     "badge-high",
    "critical": "badge-critical",
}


def _sim_badge(score: float) -> tuple[str, str, str]:
    """Return (label, css_class, color) for a similarity score."""
    if score >= 0.85:
        return "NORMAL", "badge-low", "#4ade80"
    if score >= 0.70:
        return "DRIFT", "badge-medium", "#fbbf24"
    return "ANOMALY", "badge-high", "#f87171"


def _heatmap(matrix: list[list[float]], title: str) -> None:
    """Render a 7×24 activity heatmap with the shared purple colour scale."""
    fig = go.Figure(
        data=go.Heatmap(
            z=matrix,
            x=list(range(24)),
            y=DAY_NAMES,
            colorscale=HEATMAP_SCALE,
            zmin=0.0,
            zmax=1.0,
            showscale=False,
            hovertemplate="%{y} · %{x}:00<br>density %{z:.2f}<extra></extra>",
            xgap=1,
            ygap=1,
        )
    )
    fig.update_layout(
        title=dict(text=title, font=dict(color="#64748b", size=11), x=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#64748b", family="monospace", size=10),
        margin=dict(l=0, r=0, t=28, b=0),
        height=200,
        xaxis=dict(
            tickmode="array",
            tickvals=[0, 3, 6, 9, 12, 15, 18, 21],
            showgrid=False,
            zeroline=False,
        ),
        yaxis=dict(showgrid=False, zeroline=False, autorange="reversed"),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _sparkline(scores: list[float]) -> None:
    """Render a small weekly-trend sparkline (no axes, no toolbar)."""
    if not scores:
        empty_state("Not enough weekly history yet")
        return
    x = list(range(len(scores)))
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x,
            y=scores,
            mode="lines",
            line=dict(color="#a78bfa", width=2),
            fill="tozeroy",
            fillcolor="rgba(124,58,237,0.15)",
            hovertemplate="week %{x}<br>%{y:.2f}<extra></extra>",
        )
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=4, b=0),
        height=80,
        showlegend=False,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False, range=[0, 1.05]),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ── Fetch summary + alerts ──────────────────────────────────────────────────────

try:
    summary = get_dna_summary()
except Exception:
    summary = []
try:
    alerts = get_dna_alerts()
except Exception:
    alerts = []

# ── Top: anomaly strip ──────────────────────────────────────────────────────────

if alerts:
    st.markdown(
        f'<div style="background:#1a0a2e;border:1px solid #92400e;border-radius:8px;'
        f'padding:12px 16px;color:#fbbf24;font-size:0.85rem;margin-bottom:16px;'
        f'display:flex;align-items:center;gap:10px">'
        f'<span style="font-size:1.1rem">&#9888;</span>'
        f'<span><strong>{len(alerts)}</strong> '
        f'user{"s" if len(alerts) != 1 else ""} showing behavioral anomalies</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

st.markdown('<hr style="border:none;border-top:1px solid #1e293b;margin:16px 0"/>', unsafe_allow_html=True)

# ── Row 1: user list (35) + detail (65) ─────────────────────────────────────────

col_users, col_detail = st.columns([35, 65])

with col_users:
    section_label("Users")

    if not summary:
        st.markdown(
            '<div style="font-size:0.72rem;color:#334155;padding:8px 0">'
            'No behavioral DNA data yet. Score some events first.</div>',
            unsafe_allow_html=True,
        )
    else:
        for row in summary:
            uid = row.get("user_id", "—")
            sim = float(row.get("similarity_score", 1.0))
            conf = float(row.get("confidence", 0.0))
            label, badge_cls, _ = _sim_badge(sim)

            # Row: username + similarity badge + confidence bar
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:2px">'
                f'<span style="font-family:monospace;font-size:0.82rem;color:#e2e8f0;'
                f'flex:1;overflow:hidden;text-overflow:ellipsis">{uid}</span>'
                f'<span class="badge {badge_cls}">{label}</span>'
                f'</div>'
                f'<div class="stat-bar-bg" style="margin-bottom:4px">'
                f'<div class="stat-bar-fill" style="width:{conf * 100:.0f}%;'
                f'background:#7c3aed"></div></div>',
                unsafe_allow_html=True,
            )
            if st.button(f"View {uid}", key=f"dna_btn_{uid}", use_container_width=True):
                st.session_state["dna_selected_user"] = uid
                st.rerun()

with col_detail:
    selected: str | None = st.session_state.get("dna_selected_user")

    if not selected:
        empty_state("Select a user to view their behavioral DNA")
    else:
        try:
            dna = get_user_dna(selected)
        except Exception:
            dna = None

        if dna is None:
            st.markdown(
                f'<div style="background:#1c0a0a;border:1px solid #991b1b;border-radius:8px;'
                f'padding:12px 16px;color:#f87171;font-size:0.82rem">'
                f'No behavioral DNA found for <code>{selected}</code>.</div>',
                unsafe_allow_html=True,
            )
        else:
            sim = float(dna.get("similarity_score", 1.0))
            conf = float(dna.get("confidence", 0.0))
            total = int(dna.get("total_events", 0))
            drift = dna.get("drift", {}) or {}
            sig = dna.get("signature", {}) or {}
            label, badge_cls, sim_color = _sim_badge(sim)

            # Header
            st.markdown(
                f'<div style="margin-bottom:14px">'
                f'<span style="font-size:1rem;font-weight:700;color:#f1f5f9;'
                f'font-family:monospace">{selected}</span>'
                f'&nbsp;&nbsp;<span class="badge {badge_cls}">{label}</span>'
                f'&nbsp;&nbsp;<span style="font-size:0.72rem;color:#475569">'
                f'Profile confidence: {conf * 100:.0f}% · {total} events</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # Big similarity number + color bar
            st.markdown(
                f'<div style="margin-bottom:6px">'
                f'<span style="font-size:2.6rem;font-weight:800;color:#f1f5f9;'
                f'font-family:monospace;line-height:1">{sim * 100:.0f}%</span>'
                f'<span style="font-size:0.78rem;color:#475569;margin-left:10px">'
                f'self-similarity this week</span>'
                f'</div>'
                f'<div class="stat-bar-bg" style="height:6px;margin-bottom:18px">'
                f'<div class="stat-bar-fill" style="height:6px;width:{sim * 100:.0f}%;'
                f'background:{sim_color}"></div></div>',
                unsafe_allow_html=True,
            )

            # Weekly trend sparkline
            section_label("Weekly Trend (last 8 weeks)")
            _sparkline([float(s) for s in dna.get("weekly_scores", [])])

            st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)

            # Dual heatmaps
            hm_left, hm_right = st.columns(2)
            with hm_left:
                _heatmap(dna.get("matrix", [[0.0] * 24 for _ in range(7)]), "HISTORICAL PATTERN")
            with hm_right:
                _heatmap(
                    dna.get("current_week_matrix", [[0.0] * 24 for _ in range(7)]),
                    "THIS WEEK",
                )

            st.markdown('<hr style="border:none;border-top:1px solid #1e293b;margin:16px 0"/>', unsafe_allow_html=True)

            # Signature
            section_label("Behavioral Signature")
            sig_left, sig_right = st.columns(2)

            with sig_left:
                peak_hours = sig.get("peak_hours", []) or []
                pills = "".join(
                    f'<code style="display:inline-block;background:#0a0f1e;'
                    f'border:1px solid #1e293b;border-radius:4px;padding:2px 7px;'
                    f'font-size:0.72rem;color:#a78bfa;margin:2px 3px 2px 0">{h:02d}</code>'
                    for h in peak_hours
                ) or '<span style="font-size:0.72rem;color:#334155">none</span>'
                st.markdown(
                    f'<div style="font-size:0.7rem;color:#64748b;margin-bottom:4px">Peak hours</div>'
                    f'<div style="margin-bottom:12px">{pills}</div>',
                    unsafe_allow_html=True,
                )

                active = set(sig.get("active_days", []) or [])
                dots = "".join(
                    f'<span title="{d}" style="display:inline-block;width:14px;height:14px;'
                    f'border-radius:50%;margin-right:5px;'
                    f'background:{"#7c3aed" if d in active else "transparent"};'
                    f'border:1px solid {"#7c3aed" if d in active else "#1e293b"}"></span>'
                    for d in DAY_NAMES
                )
                st.markdown(
                    f'<div style="font-size:0.7rem;color:#64748b;margin-bottom:6px">Active days</div>'
                    f'<div>{dots}</div>',
                    unsafe_allow_html=True,
                )

            with sig_right:
                mah = sig.get("most_active_hour", 0)
                mad = sig.get("most_active_day", "—")
                spread = sig.get("activity_spread", 0.0)
                st.markdown(
                    f'<div style="font-size:0.78rem;color:#94a3b8;line-height:1.9">'
                    f'Most active hour: <span style="color:#f1f5f9;font-family:monospace">{mah:02d}:00</span><br>'
                    f'Most active day: <span style="color:#f1f5f9;font-family:monospace">{mad}</span><br>'
                    f'Activity spread: <span style="color:#f1f5f9;font-family:monospace">{spread:.2f}</span>'
                    f'<span style="color:#475569"> (lower = more predictable)</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            # Drift detail
            if drift.get("drift_detected"):
                dtype = (drift.get("drift_type") or "unknown").upper()
                reason = drift.get("reason") or "Behavioral drift detected"
                sev = drift.get("severity", "medium")
                bg = "#1a0a2e" if sev == "critical" else "#1c0a0a" if sev == "high" else "#1c1400"
                border = "#6b21a8" if sev == "critical" else "#991b1b" if sev == "high" else "#92400e"
                fg = _SEV_COLOR.get(sev, "#fbbf24")

                prev_txt = ""
                weekly = dna.get("weekly_scores", []) or []
                if weekly:
                    prev_txt = (
                        f'<div style="font-size:0.75rem;color:#94a3b8;margin-top:4px">'
                        f'Similarity dropped from {float(weekly[-1]) * 100:.0f}% '
                        f'to {sim * 100:.0f}%</div>'
                    )

                st.markdown(
                    f'<div style="background:{bg};border:1px solid {border};border-radius:8px;'
                    f'padding:12px 16px;margin-top:16px">'
                    f'<div style="font-size:0.85rem;font-weight:700;color:{fg}">'
                    f'&#9888; {dtype} DRIFT DETECTED</div>'
                    f'<div style="font-size:0.8rem;color:#cbd5e1;margin-top:4px">{reason}</div>'
                    f'{prev_txt}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

# ── Bottom: anomalies table ─────────────────────────────────────────────────────

st.markdown('<hr style="border:none;border-top:1px solid #1e293b;margin:24px 0"/>', unsafe_allow_html=True)
section_label("Behavioral Anomalies")

if not alerts:
    empty_state("No behavioral anomalies detected")
else:
    header = (
        '<div style="display:grid;grid-template-columns:110px 90px 90px 90px 1fr 120px;'
        'gap:8px;padding:8px;border-bottom:1px solid #1e293b;font-size:0.62rem;'
        'text-transform:uppercase;letter-spacing:0.08em;color:#475569;font-weight:700">'
        '<span>User</span><span>Similarity</span><span>Drift Type</span>'
        '<span>Severity</span><span>Reason</span><span>Last Seen</span>'
        '</div>'
    )
    rows_html = [header]
    for a in alerts:
        sev = a.get("drift_severity", "medium")
        sev_color = _SEV_COLOR.get(sev, "#fbbf24")
        sim_pct = f'{float(a.get("similarity_score", 0)) * 100:.0f}%'
        dtype = (a.get("drift_type") or "—")
        reason = a.get("reason") or "—"
        last = fmt_ts(str(a.get("last_updated", "")))
        rows_html.append(
            f'<div style="display:grid;grid-template-columns:110px 90px 90px 90px 1fr 120px;'
            f'gap:8px;padding:7px 8px;border-bottom:1px solid #0f172a;font-size:0.75rem;'
            f'font-family:monospace;align-items:center">'
            f'<span style="color:#e2e8f0">{a.get("user_id", "—")}</span>'
            f'<span style="color:#f1f5f9">{sim_pct}</span>'
            f'<span style="color:#94a3b8">{dtype}</span>'
            f'<span style="color:{sev_color};font-weight:700;text-transform:uppercase">{sev}</span>'
            f'<span style="color:#64748b;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{reason}</span>'
            f'<span style="color:#475569">{last}</span>'
            f'</div>'
        )
    st.markdown(
        '<div style="background:#0f1629;border:1px solid #1e293b;border-radius:8px;overflow:hidden">'
        + "".join(rows_html)
        + "</div>",
        unsafe_allow_html=True,
    )
