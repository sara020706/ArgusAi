import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import streamlit as st

_FONT = "JetBrains Mono, ui-monospace, monospace"

DARK_LAYOUT = dict(  # name kept for import stability; now a light theme
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#475569", size=11, family=_FONT),
    xaxis=dict(
        gridcolor="#EDEFF5", linecolor="#E6E9F0",
        tickcolor="#E6E9F0", tickfont=dict(color="#94A3B8", size=10),
    ),
    yaxis=dict(
        gridcolor="#EDEFF5", linecolor="#E6E9F0",
        tickcolor="#E6E9F0", tickfont=dict(color="#94A3B8", size=10),
    ),
    margin=dict(l=0, r=0, t=28, b=0),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#475569", size=10)),
    title=dict(font=dict(color="#475569", size=12), x=0),
)

LEVEL_COLORS = {
    "LOW": "#16A34A",
    "MEDIUM": "#D97706",
    "HIGH": "#DC2626",
    "CRITICAL": "#7C3AED",
}

# Legacy alias used by other modules
RISK_COLORS = LEVEL_COLORS

_CHART_CFG = {"displayModeBar": False}


def _empty_fig(message: str = "No data") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message, x=0.5, y=0.5, xref="paper", yref="paper",
        showarrow=False, font=dict(color="#94A3B8", size=13),
    )
    fig.update_layout(**DARK_LAYOUT)
    return fig


def risk_score_timeline(events: list, title: str = "Risk Score Timeline") -> None:
    """Line chart of risk scores over time with risk-level reference lines."""
    if not events:
        st.plotly_chart(_empty_fig("No events"), use_container_width=True, config=_CHART_CFG)
        return

    df = pd.DataFrame(events)
    if "timestamp" not in df.columns or "risk_score" not in df.columns:
        st.plotly_chart(_empty_fig("Missing columns"), use_container_width=True, config=_CHART_CFG)
        return

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"]).sort_values("timestamp")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["timestamp"], y=df["risk_score"],
        mode="lines",
        line=dict(color="#6366F1", width=2.5),
        fill="tozeroy",
        fillcolor="rgba(99,102,241,0.10)",
        name="risk score",
        hovertemplate="%{y:.0f}/100<extra></extra>",
    ))

    for y, color, label in [(30, "#16A34A", "LOW"), (60, "#D97706", "MED"), (85, "#DC2626", "HIGH")]:
        fig.add_hline(y=y, line=dict(color=color, width=1, dash="dot"),
                      annotation_text=label,
                      annotation_font=dict(color=color, size=9))

    layout = {**DARK_LAYOUT, "title": dict(text=title, font=dict(color="#94a3b8", size=12), x=0)}
    fig.update_layout(**layout)
    st.plotly_chart(fig, use_container_width=True, config=_CHART_CFG)


def risk_distribution_pie(alerts: list, title: str = "Alert Distribution") -> None:
    """Donut chart of alerts by risk level."""
    if not alerts:
        st.plotly_chart(_empty_fig("No alerts"), use_container_width=True, config=_CHART_CFG)
        return

    df = pd.DataFrame(alerts)
    if "risk_level" not in df.columns:
        st.plotly_chart(_empty_fig(), use_container_width=True, config=_CHART_CFG)
        return

    counts = df["risk_level"].value_counts().reset_index()
    counts.columns = ["level", "count"]
    colors = [LEVEL_COLORS.get(l, "#64748b") for l in counts["level"]]
    total  = counts["count"].sum()

    fig = go.Figure(go.Pie(
        labels=counts["level"],
        values=counts["count"],
        hole=0.65,
        marker=dict(colors=colors, line=dict(color="#FFFFFF", width=2)),
        textinfo="label+percent",
        textfont=dict(size=10, color="#475569"),
        hovertemplate="%{label}: %{value}<extra></extra>",
    ))
    fig.add_annotation(
        text=str(total), x=0.5, y=0.5, showarrow=False,
        font=dict(color="#0F172A", size=22, family=_FONT),
    )
    layout = {**DARK_LAYOUT, "title": dict(text=title, font=dict(color="#94a3b8", size=12), x=0),
              "showlegend": False}
    fig.update_layout(**layout)
    st.plotly_chart(fig, use_container_width=True, config=_CHART_CFG)


def top_users_bar(alerts: list, top_n: int = 8, title: str = "Top Users") -> None:
    """Horizontal bar chart — top users by alert count, colored by highest risk level."""
    if not alerts:
        st.plotly_chart(_empty_fig("No alerts"), use_container_width=True, config=_CHART_CFG)
        return

    df = pd.DataFrame(alerts)
    if "user_id" not in df.columns:
        st.plotly_chart(_empty_fig(), use_container_width=True, config=_CHART_CFG)
        return

    risk_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
    agg = df.groupby("user_id").agg(
        count=("user_id", "count"),
        max_level=("risk_level", lambda x: max(x, key=lambda l: risk_order.get(l, 0))),
    ).reset_index().nlargest(top_n, "count")

    colors = [LEVEL_COLORS.get(l, "#64748b") for l in agg["max_level"]]

    fig = go.Figure(go.Bar(
        x=agg["count"], y=agg["user_id"],
        orientation="h",
        marker=dict(color=colors),
        width=0.4,
        hovertemplate="%{y}: %{x} alerts<extra></extra>",
    ))
    layout = {**DARK_LAYOUT, "title": dict(text=title, font=dict(color="#94a3b8", size=12), x=0),
              "xaxis": {**DARK_LAYOUT["xaxis"], "dtick": 1}}
    fig.update_layout(**layout)
    st.plotly_chart(fig, use_container_width=True, config=_CHART_CFG)


def hourly_activity_heatmap(events: list, title: str = "Activity Heatmap") -> None:
    """Heatmap of event frequency by hour and day of week."""
    if not events:
        st.plotly_chart(_empty_fig("No events"), use_container_width=True, config=_CHART_CFG)
        return

    df = pd.DataFrame(events)
    if "timestamp" not in df.columns:
        st.plotly_chart(_empty_fig(), use_container_width=True, config=_CHART_CFG)
        return

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"])
    df["hour"] = df["timestamp"].dt.hour
    df["dow"]  = df["timestamp"].dt.day_name().str[:3]

    days   = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    hours  = list(range(24))
    matrix = pd.DataFrame(0, index=days, columns=hours)

    for _, row in df.iterrows():
        d = row["dow"]
        h = int(row["hour"])
        if d in matrix.index:
            matrix.loc[d, h] += 1

    fig = go.Figure(go.Heatmap(
        z=matrix.values,
        x=[str(h).zfill(2) for h in hours],
        y=days,
        colorscale=[[0, "#F1F3F9"], [0.5, "#C7D2FE"], [1, "#6366F1"]],
        showscale=False,
        xgap=2, ygap=2,
        hovertemplate="Day: %{y}<br>Hour: %{x}:00<br>Events: %{z}<extra></extra>",
    ))
    layout = {**DARK_LAYOUT, "title": dict(text=title, font=dict(color="#94a3b8", size=12), x=0)}
    fig.update_layout(**layout)
    st.plotly_chart(fig, use_container_width=True, config=_CHART_CFG)


def download_trend_chart(events: list, title: str = "Download Volume") -> None:
    """Bar chart of download sizes — green < 1000 MB, red >= 1000 MB."""
    if not events:
        st.plotly_chart(_empty_fig("No events"), use_container_width=True, config=_CHART_CFG)
        return

    df = pd.DataFrame(events)
    if "download_mb" not in df.columns or "timestamp" not in df.columns:
        st.plotly_chart(_empty_fig(), use_container_width=True, config=_CHART_CFG)
        return

    df["timestamp"]   = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"]).sort_values("timestamp")
    df["download_mb"] = pd.to_numeric(df["download_mb"], errors="coerce").fillna(0)
    colors = ["#DC2626" if v >= 1000 else "#16A34A" for v in df["download_mb"]]

    fig = go.Figure(go.Bar(
        x=df["timestamp"], y=df["download_mb"],
        marker=dict(color=colors, line=dict(width=0)),
        hovertemplate="%{y:,.0f} MB<extra></extra>",
    ))
    layout = {**DARK_LAYOUT, "title": dict(text=title, font=dict(color="#94a3b8", size=12), x=0)}
    fig.update_layout(**layout)
    st.plotly_chart(fig, use_container_width=True, config=_CHART_CFG)


def reasons_breakdown_bar(alert: dict, title: str = "Score Breakdown") -> None:
    """Horizontal bar — contributing factors for one alert, sorted by points."""
    # Support both old-style (rule_contributions/stat_contributions) and
    # new-style (reasons list) formats
    reasons = alert.get("reasons", []) or alert.get("contributing_factors", [])

    # Also support the structured contributions dicts from the original API format
    rule_c = alert.get("rule_contributions", {}) or {}
    stat_c = alert.get("stat_contributions", {}) or {}

    parsed = []

    # Try structured contributions first
    if rule_c or stat_c:
        def _extract(contrib: dict):
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

        all_items = _extract(rule_c) + _extract(stat_c)
        for k, pts in all_items:
            label = k.replace("rule_", "").replace("stat_", "").replace("_", " ")
            parsed.append((label[:40], int(pts)))
    elif reasons:
        import re
        for r in reasons[:6]:
            m = re.search(r"\+(\d+)", str(r))
            pts = int(m.group(1)) if m else 5
            label = re.sub(r"\(\+\d+.*?\)", "", str(r)).strip()
            parsed.append((label[:40], pts))

    if not parsed:
        st.plotly_chart(_empty_fig("No breakdown available"), use_container_width=True, config=_CHART_CFG)
        return

    parsed.sort(key=lambda x: x[1], reverse=True)
    labels = [p[0] for p in parsed]
    values = [p[1] for p in parsed]

    fig = go.Figure(go.Bar(
        x=values, y=labels,
        orientation="h",
        marker=dict(color="#6366F1", line=dict(width=0)),
        text=[f"+{v}" for v in values],
        textposition="outside",
        textfont=dict(color="#6366F1", size=10),
        hovertemplate="%{y}: +%{x} pts<extra></extra>",
    ))
    layout = {**DARK_LAYOUT, "title": dict(text=title, font=dict(color="#94a3b8", size=12), x=0)}
    fig.update_layout(**layout)
    st.plotly_chart(fig, use_container_width=True, config=_CHART_CFG)
