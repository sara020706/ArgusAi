"""Plotly chart components for the Argus dashboard.

Every function accepts a list of event/alert dicts as returned by the API
client and renders directly into the Streamlit app via ``st.plotly_chart``.
All charts use transparent backgrounds to integrate cleanly with the dark
theme. Empty-list inputs are handled gracefully with ``st.info``.
"""

from __future__ import annotations

from collections import Counter, defaultdict

import streamlit as st

from argus.dashboard.components.risk_badge import RISK_COLORS, risk_color

_TRANSPARENT = "rgba(0,0,0,0)"
_CHART_OPTS = dict(use_container_width=True, config={"displayModeBar": False})

_RISK_ORDER = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


def _apply_dark_layout(fig) -> None:
    """Apply transparent, dark-friendly layout settings to a Plotly figure."""
    fig.update_layout(
        plot_bgcolor=_TRANSPARENT,
        paper_bgcolor=_TRANSPARENT,
        font_color="#f1f5f9",
        legend=dict(bgcolor=_TRANSPARENT),
        margin=dict(l=10, r=10, t=40, b=10),
    )
    fig.update_xaxes(gridcolor="#334155", zerolinecolor="#334155")
    fig.update_yaxes(gridcolor="#334155", zerolinecolor="#334155")


def _parse_ts(ts_str: str):
    """Parse a timestamp string to datetime, returning None on failure."""
    from datetime import datetime
    if not ts_str:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(ts_str[:19], fmt)
        except ValueError:
            continue
    return None


def risk_score_timeline(events: list[dict]) -> None:
    """Line chart of risk score over time for a single user.

    Plots ``risk_score`` (Y) vs ``timestamp`` (X). Adds horizontal reference
    lines at the risk-band boundaries (30, 60, 85) and colours the markers by
    ``risk_level``.

    Args:
        events: List of scored-event dicts from the API (newest-first ordering
            is handled internally).
    """
    import plotly.graph_objects as go

    if not events:
        st.info("No event data available for timeline.")
        return

    ordered = sorted(
        [e for e in events if e.get("timestamp")],
        key=lambda e: e["timestamp"],
    )
    xs = [_parse_ts(e["timestamp"]) for e in ordered]
    ys = [float(e.get("risk_score", 0)) for e in ordered]
    colors = [risk_color(e.get("risk_level", "LOW")) for e in ordered]

    fig = go.Figure()

    # Band reference lines
    for y, label, color in [
        (85, "CRITICAL", RISK_COLORS["CRITICAL"]),
        (60, "HIGH",     RISK_COLORS["HIGH"]),
        (30, "MEDIUM",   RISK_COLORS["MEDIUM"]),
    ]:
        fig.add_hline(
            y=y,
            line_dash="dot",
            line_color=color,
            opacity=0.5,
            annotation_text=label,
            annotation_position="right",
        )

    fig.add_trace(
        go.Scatter(
            x=xs,
            y=ys,
            mode="lines+markers",
            line=dict(color="#7c3aed", width=2),
            marker=dict(color=colors, size=9, line=dict(color="#0f172a", width=1)),
            hovertemplate="<b>%{y:.0f}</b> pts<br>%{x}<extra></extra>",
        )
    )

    fig.update_layout(
        title="Risk Score Over Time",
        xaxis_title="Time",
        yaxis_title="Risk Score",
        yaxis_range=[0, 105],
    )
    _apply_dark_layout(fig)
    st.plotly_chart(fig, **_CHART_OPTS)


def risk_distribution_pie(alerts: list[dict]) -> None:
    """Pie chart of alert counts by risk level.

    Args:
        alerts: List of alert dicts, each with a ``risk_level`` key.
    """
    import plotly.graph_objects as go

    if not alerts:
        st.info("No alert data available for distribution chart.")
        return

    counts = Counter(a.get("risk_level", "UNKNOWN") for a in alerts)
    labels = [l for l in _RISK_ORDER if l in counts]
    values = [counts[l] for l in labels]
    colors = [RISK_COLORS.get(l, "#94a3b8") for l in labels]

    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            marker=dict(colors=colors, line=dict(color="#0f172a", width=2)),
            hovertemplate="<b>%{label}</b><br>%{value} alerts (%{percent})<extra></extra>",
            textfont_color="#f1f5f9",
        )
    )
    fig.update_layout(title="Alert Distribution by Risk Level")
    _apply_dark_layout(fig)
    st.plotly_chart(fig, **_CHART_OPTS)


def top_users_bar(alerts: list[dict], top_n: int = 10) -> None:
    """Horizontal bar chart of users ranked by alert count.

    Each bar is coloured by the user's highest observed risk level.

    Args:
        alerts: List of alert dicts with ``user_id`` and ``risk_level`` keys.
        top_n: Maximum number of users to display.
    """
    import plotly.graph_objects as go

    if not alerts:
        st.info("No alert data to rank users.")
        return

    user_counts: Counter = Counter()
    user_top_level: dict[str, str] = {}
    level_rank = {l: i for i, l in enumerate(_RISK_ORDER)}

    for a in alerts:
        uid = a.get("user_id", "unknown")
        level = a.get("risk_level", "LOW")
        user_counts[uid] += 1
        existing = user_top_level.get(uid, "LOW")
        if level_rank.get(level, 0) > level_rank.get(existing, 0):
            user_top_level[uid] = level

    top = user_counts.most_common(top_n)
    users = [u for u, _ in reversed(top)]
    counts = [user_counts[u] for u in users]
    colors = [RISK_COLORS.get(user_top_level.get(u, "LOW"), "#94a3b8") for u in users]

    fig = go.Figure(
        go.Bar(
            x=counts,
            y=users,
            orientation="h",
            marker=dict(color=colors),
            hovertemplate="<b>%{y}</b><br>%{x} alerts<extra></extra>",
        )
    )
    fig.update_layout(title=f"Top {top_n} Users by Alert Count", xaxis_title="Alerts")
    _apply_dark_layout(fig)
    st.plotly_chart(fig, **_CHART_OPTS)


def hourly_activity_heatmap(events: list[dict]) -> None:
    """Heatmap of event count by hour of day vs day of week.

    Rows represent days (Monday–Sunday), columns represent hours (0–23).
    More activity → darker red.

    Args:
        events: List of event dicts with a ``timestamp`` key.
    """
    import plotly.graph_objects as go

    if not events:
        st.info("No event data available for heatmap.")
        return

    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    grid: dict[tuple[int, int], int] = defaultdict(int)

    for e in events:
        ts = _parse_ts(e.get("timestamp", ""))
        if ts:
            grid[(ts.weekday(), ts.hour)] += 1

    z = [[grid[(d, h)] for h in range(24)] for d in range(7)]

    fig = go.Figure(
        go.Heatmap(
            z=z,
            x=list(range(24)),
            y=day_names,
            colorscale=[[0, _TRANSPARENT], [0.01, "#1e293b"], [1, "#ef4444"]],
            hovertemplate="Day: <b>%{y}</b><br>Hour: <b>%{x}:00</b><br>Events: <b>%{z}</b><extra></extra>",
            showscale=True,
        )
    )
    fig.update_layout(
        title="Activity Heatmap — Hour × Day of Week",
        xaxis_title="Hour of Day (UTC)",
        yaxis_title="Day",
    )
    _apply_dark_layout(fig)
    st.plotly_chart(fig, **_CHART_OPTS)


def download_trend_chart(events: list[dict]) -> None:
    """Bar chart of download_mb per event over time.

    Bars above 1000 MB are coloured red; others green.

    Args:
        events: List of scored-event dicts with ``download_mb`` and
            ``timestamp`` keys.
    """
    import plotly.graph_objects as go

    if not events:
        st.info("No download data available.")
        return

    ordered = sorted(
        [e for e in events if e.get("timestamp")],
        key=lambda e: e["timestamp"],
    )
    xs = [_parse_ts(e["timestamp"]) for e in ordered]
    ys = [float(e.get("download_mb", 0)) for e in ordered]
    colors = [RISK_COLORS["HIGH"] if y > 1000 else RISK_COLORS["LOW"] for y in ys]

    fig = go.Figure(
        go.Bar(
            x=xs,
            y=ys,
            marker_color=colors,
            hovertemplate="<b>%{y:.1f} MB</b><br>%{x}<extra></extra>",
        )
    )
    fig.add_hline(
        y=1000,
        line_dash="dot",
        line_color=RISK_COLORS["HIGH"],
        opacity=0.6,
        annotation_text="1 GB threshold",
        annotation_position="right",
    )
    fig.update_layout(title="Download Volume Over Time", yaxis_title="MB")
    _apply_dark_layout(fig)
    st.plotly_chart(fig, **_CHART_OPTS)


def reasons_breakdown_bar(alert: dict) -> None:
    """Horizontal bar chart of scoring contributions for a single alert.

    Combines ``rule_contributions`` and ``stat_contributions`` from the alert
    dict and renders them as labelled bars.

    Args:
        alert: A single scored-event dict with ``rule_contributions`` and
            ``stat_contributions`` keys (dicts of name → points or
            name → [points, reason]).
    """
    import plotly.graph_objects as go

    def _extract(contrib: dict) -> list[tuple[str, float]]:
        items = []
        for k, v in (contrib or {}).items():
            if isinstance(v, (int, float)):
                items.append((k, float(v)))
            elif isinstance(v, (list, tuple)) and len(v) >= 1:
                try:
                    items.append((k, float(v[0])))
                except (TypeError, ValueError):
                    pass
        return items

    rule_items = _extract(alert.get("rule_contributions", {}))
    stat_items = _extract(alert.get("stat_contributions", {}))
    all_items = sorted(rule_items + stat_items, key=lambda x: x[1])

    if not all_items:
        st.info("No contribution breakdown available.")
        return

    names = [i[0].replace("rule_", "").replace("stat_", "").replace("_", " ") for i, _ in
             [(x, None) for x in all_items]]
    values = [i[1] for i in all_items]
    colors = [
        RISK_COLORS["CRITICAL"] if v >= 30 else
        RISK_COLORS["HIGH"] if v >= 20 else
        RISK_COLORS["MEDIUM"] if v >= 10 else
        RISK_COLORS["LOW"]
        for v in values
    ]
    names = [n for n, _ in [(x[0].replace("rule_", "").replace("stat_", "").replace("_", " "), None)
                             for x in all_items]]

    fig = go.Figure(
        go.Bar(
            x=values,
            y=names,
            orientation="h",
            marker_color=colors,
            text=[f"+{v:.0f} pts" for v in values],
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>+%{x:.0f} pts<extra></extra>",
        )
    )
    fig.update_layout(title="Score Contributions", xaxis_title="Points")
    _apply_dark_layout(fig)
    st.plotly_chart(fig, **_CHART_OPTS)
