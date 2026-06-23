"""Threat Map page — global visualization of alert origins."""

from __future__ import annotations

from collections import defaultdict

import plotly.graph_objects as go
import streamlit as st

from argus.dashboard.api_client import get_alerts
from argus.dashboard.components.risk_badge import (
    RISK_COLORS,
    render_risk_badge,
    level_color,
)
from argus.dashboard.styles import empty_state, fmt_ts, inject_global_css, render_page_header, section_label

st.set_page_config(page_title="Threat Map — Argus AI", page_icon="⬡", layout="wide")
inject_global_css()

render_page_header("Threat Map", "global threat activity")

# ── Country-code → (lat, lon, display name) lookup ──────────────────────────

_COUNTRY_COORDS: dict[str, tuple[float, float, str]] = {
    "US": (37.09,  -95.71,  "United States"),
    "GB": (55.38,   -3.44,  "United Kingdom"),
    "DE": (51.17,   10.45,  "Germany"),
    "FR": (46.23,    2.21,  "France"),
    "CN": (35.86,  104.19,  "China"),
    "RU": (61.52,  105.32,  "Russia"),
    "IN": (20.59,   78.96,  "India"),
    "BR": (-14.24, -51.93,  "Brazil"),
    "AU": (-25.27,  133.78, "Australia"),
    "JP": (36.20,  138.25,  "Japan"),
    "KR": (35.91,  127.77,  "South Korea"),
    "CA": (56.13, -106.35,  "Canada"),
    "NL": (52.13,    5.29,  "Netherlands"),
    "SG": (1.35,   103.82,  "Singapore"),
    "ZA": (-30.56,  22.94,  "South Africa"),
}

_PLACEHOLDER_POINTS = [
    {"lat": 37.09,  "lon": -95.71, "location": "United States", "count": 3,  "level": "HIGH",     "user": "user_001", "score": 72},
    {"lat": 55.38,  "lon":  -3.44, "location": "United Kingdom","count": 2,  "level": "MEDIUM",   "user": "user_002", "score": 55},
    {"lat": 35.86,  "lon": 104.19, "location": "China",          "count": 5,  "level": "CRITICAL", "user": "user_003", "score": 91},
    {"lat": 61.52,  "lon": 105.32, "location": "Russia",         "count": 4,  "level": "HIGH",     "user": "user_004", "score": 78},
    {"lat":  1.35,  "lon": 103.82, "location": "Singapore",      "count": 1,  "level": "LOW",      "user": "user_005", "score": 22},
]

_LEVEL_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


def _resolve_location(alert: dict):
    loc = alert.get("location")
    if not loc:
        return None
    up = str(loc).upper().strip()
    if up in _COUNTRY_COORDS:
        return _COUNTRY_COORDS[up]
    for code, (lat, lon, name) in _COUNTRY_COORDS.items():
        if name.lower() in loc.lower() or loc.lower() in name.lower():
            return lat, lon, name
    return None


def _build_map_points(alerts: list) -> list:
    buckets: dict = defaultdict(lambda: {"count": 0, "level": "LOW", "users": set(), "score": 0})
    for alert in alerts:
        resolved = _resolve_location(alert)
        if not resolved:
            continue
        lat, lon, name = resolved
        buckets[name]["lat"] = lat
        buckets[name]["lon"] = lon
        buckets[name]["location"] = name
        buckets[name]["count"] += 1
        buckets[name]["users"].add(alert.get("user_id", "unknown"))
        cur = buckets[name]["level"]
        new = alert.get("risk_level", "LOW")
        if _LEVEL_ORDER.get(new, 0) > _LEVEL_ORDER.get(cur, 0):
            buckets[name]["level"] = new
        sc = float(alert.get("risk_score", 0) or 0)
        if sc > buckets[name]["score"]:
            buckets[name]["score"] = sc
    return [
        {**v, "users": sorted(v["users"]), "user": sorted(v["users"])[0] if v["users"] else "—"}
        for v in buckets.values()
    ]


def _render_map(points: list, placeholder: bool = False) -> None:
    lats    = [p["lat"] for p in points]
    lons    = [p["lon"] for p in points]
    scores  = [float(p.get("score", p.get("count", 1) * 10)) for p in points]
    colors  = [RISK_COLORS.get(p["level"], "#64748b") for p in points]
    sizes   = [max(6, min(30, s / 10)) for s in scores]
    hovers  = [
        f"<b>{p['location']}</b><br>"
        f"User: {p.get('user', '—')}<br>"
        f"Score: {p.get('score', p.get('count', 0)):.0f}/100<br>"
        f"Level: {p['level']}<br>"
        f"Alerts: {p.get('count', 1)}"
        for p in points
    ]

    fig = go.Figure()

    # Glow trace (same coords, larger, low opacity)
    fig.add_trace(go.Scattergeo(
        lat=lats, lon=lons,
        mode="markers",
        marker=dict(size=[s * 3 for s in sizes], color=colors, opacity=0.12, line=dict(width=0)),
        hoverinfo="skip",
        showlegend=False,
    ))

    # Main markers
    fig.add_trace(go.Scattergeo(
        lat=lats, lon=lons,
        mode="markers",
        marker=dict(
            size=sizes,
            color=colors,
            opacity=0.9,
            line=dict(color="#0f172a", width=1),
        ),
        text=hovers,
        hoverinfo="text",
        showlegend=False,
    ))

    fig.update_geos(
        projection_type="natural earth",
        showframe=False,
        showland=True,
        landcolor="#0a0f1e",
        showocean=True,
        oceancolor="#070d1a",
        showlakes=False,
        showcountries=True,
        countrycolor="#1e293b",
        showcoastlines=True,
        coastlinecolor="#1e293b",
        bgcolor="rgba(0,0,0,0)",
    )

    title_text = "Global Threat Activity"
    if placeholder:
        title_text += " (sample data)"

    fig.update_layout(
        title=dict(text=title_text, font=dict(color="#94a3b8", size=12), x=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#64748b", family="monospace"),
        margin=dict(l=0, r=0, t=32, b=0),
        height=480,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ── Main ──────────────────────────────────────────────────────────────────────

try:
    alerts = get_alerts(limit=200, min_risk_level="LOW")
except Exception:
    alerts = []

points = _build_map_points(alerts) if alerts else []

if not alerts:
    st.markdown(
        '<div style="background:#1c0a0a;border:1px solid #991b1b;border-radius:8px;'
        'padding:12px 16px;color:#f87171;font-size:0.82rem;margin-bottom:16px">'
        'No alert data available. Is the Argus API running?</div>',
        unsafe_allow_html=True,
    )
    _render_map(_PLACEHOLDER_POINTS, placeholder=True)
elif not points:
    st.markdown(
        '<div style="background:#1c1400;border:1px solid #92400e;border-radius:8px;'
        'padding:12px 16px;color:#fbbf24;font-size:0.82rem;margin-bottom:16px">'
        'None of the current alerts carry location information. '
        'Showing sample data. Populate the <code>location</code> field on events to see real data.</div>',
        unsafe_allow_html=True,
    )
    _render_map(_PLACEHOLDER_POINTS, placeholder=True)
else:
    _render_map(points)

# ── Below-map stats ────────────────────────────────────────────────────────────

st.markdown('<hr style="border:none;border-top:1px solid #1e293b;margin:20px 0"/>', unsafe_allow_html=True)

active_points = points if points else _PLACEHOLDER_POINTS
total_threats = sum(p.get("count", 1) for p in active_points)
unique_ips    = len({a.get("ip") for a in alerts if a.get("ip")}) if alerts else 0
countries     = len(active_points)

col_metrics, col_table = st.columns([1, 2])

with col_metrics:
    section_label("Summary")
    st.metric("Total Threats",  total_threats)
    st.metric("Unique IPs",     unique_ips)
    st.metric("Countries",      countries)

with col_table:
    section_label("Threat Locations")
    located_alerts = []
    for alert in alerts:
        resolved = _resolve_location(alert)
        if not resolved:
            continue
        _, _, name = resolved
        level = alert.get("risk_level", "LOW")
        located_alerts.append({
            "User":     alert.get("user_id", "—"),
            "Location": name,
            "Level":    level,
            "Score":    f"{alert.get('risk_score', 0):.0f}/100",
            "Time":     fmt_ts(str(alert.get("timestamp", ""))),
        })

    if located_alerts:
        # Render compact table
        rows_html = []
        for row in located_alerts[:15]:
            lc = RISK_COLORS.get(row["Level"], "#64748b")
            rows_html.append(
                f'<div style="display:grid;grid-template-columns:120px 140px 80px 70px 120px;'
                f'gap:8px;padding:6px 8px;border-bottom:1px solid #0f172a;font-size:0.75rem;'
                f'font-family:monospace;align-items:center">'
                f'<span style="color:#94a3b8">{row["User"]}</span>'
                f'<span style="color:#64748b">{row["Location"]}</span>'
                f'<span style="color:{lc}">{row["Level"]}</span>'
                f'<span style="color:#f1f5f9">{row["Score"]}</span>'
                f'<span style="color:#475569">{row["Time"]}</span>'
                f'</div>'
            )
        st.markdown(
            '<div style="background:#0f1629;border:1px solid #1e293b;border-radius:8px;overflow:hidden">'
            + "".join(rows_html)
            + "</div>",
            unsafe_allow_html=True,
        )
    else:
        empty_state("No located alerts to display")
