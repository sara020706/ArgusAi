"""Threat Map page — global visualization of alert origins.

Plots alert activity on a world map using Plotly scatter_geo. When events
carry a ``location`` field it is used directly; otherwise a lookup table maps
common country codes to approximate coordinates. A placeholder map with
synthetic points is shown when no location data is available.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

import streamlit as st

from argus.dashboard.api_client import get_alerts
from argus.dashboard.components.risk_badge import RISK_COLORS, render_risk_badge, risk_emoji

st.set_page_config(page_title="Threat Map — Argus", page_icon="🌍", layout="wide")
st.title("🌍 Global Threat Map")
st.caption("Geographic distribution of alert origins. Marker size reflects alert volume; colour reflects highest risk level.")

# ── Country-code → (lat, lon, display name) lookup ──────────────────────────

_COUNTRY_COORDS: dict[str, tuple[float, float, str]] = {
    "US": (37.09,  -95.71,  "United States"),
    "GB": (55.38,   -3.44,  "United Kingdom"),
    "DE": (51.17,   10.45,  "Germany"),
    "FR": (46.23,    2.21,  "France"),
    "CN": (35.86,  104.19,  "China"),
    "RU": (61.52,  105.32,  "Russia"),
    "IN": (20.59,   78.96,  "India"),
    "BR": (-14.24,  -51.93, "Brazil"),
    "AU": (-25.27,  133.78, "Australia"),
    "JP": (36.20,  138.25,  "Japan"),
    "KR": (35.91,  127.77,  "South Korea"),
    "CA": (56.13,  -106.35, "Canada"),
    "NL": (52.13,    5.29,  "Netherlands"),
    "SG": (1.35,   103.82,  "Singapore"),
    "ZA": (-30.56,  22.94,  "South Africa"),
}

_PLACEHOLDER_POINTS = [
    {"lat": 37.09,   "lon": -95.71, "location": "United States", "count": 3, "level": "HIGH",     "user": "user_001"},
    {"lat": 55.38,   "lon":  -3.44, "location": "United Kingdom","count": 2, "level": "MEDIUM",   "user": "user_002"},
    {"lat": 35.86,   "lon": 104.19, "location": "China",          "count": 5, "level": "CRITICAL", "user": "user_003"},
    {"lat": 61.52,   "lon": 105.32, "location": "Russia",         "count": 4, "level": "HIGH",     "user": "user_004"},
    {"lat":  1.35,   "lon": 103.82, "location": "Singapore",      "count": 1, "level": "LOW",      "user": "user_005"},
]

_LEVEL_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


def _fmt_ts(ts: str) -> str:
    try:
        return datetime.fromisoformat(ts[:19]).strftime("%b %d, %Y %H:%M")
    except Exception:
        return ts or "—"


def _resolve_location(alert: dict) -> tuple[float, float, str] | None:
    """Try to extract (lat, lon, name) from an alert dict.

    Checks the ``location`` field first (e.g. a country code or free-text
    name), then falls back to None.
    """
    loc = alert.get("location")
    if not loc:
        return None
    up = str(loc).upper().strip()
    if up in _COUNTRY_COORDS:
        return _COUNTRY_COORDS[up]
    # Try case-insensitive name match
    for code, (lat, lon, name) in _COUNTRY_COORDS.items():
        if name.lower() in loc.lower() or loc.lower() in name.lower():
            return lat, lon, name
    return None


def _build_map_points(alerts: list[dict]) -> list[dict]:
    """Aggregate alerts by resolved location into map-ready point dicts."""
    buckets: dict[str, dict] = defaultdict(lambda: {"count": 0, "level": "LOW", "users": set()})

    for alert in alerts:
        resolved = _resolve_location(alert)
        if not resolved:
            continue
        lat, lon, name = resolved
        key = name
        buckets[key]["lat"] = lat
        buckets[key]["lon"] = lon
        buckets[key]["location"] = name
        buckets[key]["count"] += 1
        buckets[key]["users"].add(alert.get("user_id", "unknown"))

        cur = buckets[key]["level"]
        new = alert.get("risk_level", "LOW")
        if _LEVEL_ORDER.get(new, 0) > _LEVEL_ORDER.get(cur, 0):
            buckets[key]["level"] = new

    return [
        {**v, "users": sorted(v["users"]), "user": sorted(v["users"])[0]}
        for v in buckets.values()
    ]


def _render_map(points: list[dict], placeholder: bool = False) -> None:
    import plotly.graph_objects as go

    sizes  = [max(8, min(40, p["count"] * 6)) for p in points]
    colors = [RISK_COLORS.get(p["level"], "#94a3b8") for p in points]
    texts  = [
        f"<b>{p['location']}</b><br>"
        f"Alerts: {p['count']}<br>"
        f"Top user: {p.get('user', '—')}<br>"
        f"Risk: {p['level']}"
        for p in points
    ]

    fig = go.Figure(
        go.Scattergeo(
            lat=[p["lat"] for p in points],
            lon=[p["lon"] for p in points],
            mode="markers",
            marker=dict(
                size=sizes,
                color=colors,
                opacity=0.85,
                line=dict(color="#0f172a", width=1),
            ),
            text=texts,
            hoverinfo="text",
        )
    )

    fig.update_geos(
        projection_type="natural earth",
        showland=True,
        landcolor="#1e293b",
        showocean=True,
        oceancolor="#0f172a",
        showlakes=False,
        showcountries=True,
        countrycolor="#334155",
        showcoastlines=True,
        coastlinecolor="#475569",
        bgcolor="rgba(0,0,0,0)",
    )

    title = "Global Threat Activity"
    if placeholder:
        title += " (sample data — no location info in current alerts)"

    fig.update_layout(
        title=title,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#f1f5f9",
        margin=dict(l=0, r=0, t=40, b=0),
        height=500,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ── Main ──────────────────────────────────────────────────────────────────────

alerts = get_alerts(limit=200, min_risk_level="LOW")

if not alerts:
    st.warning("⚠️ No alert data available. Is the Argus API running?")
    st.stop()

points = _build_map_points(alerts)

if not points:
    st.info(
        "ℹ️ None of the current alerts carry location information. "
        "Showing a placeholder map with sample data. "
        "Populate the ``location`` field on events to see real data here."
    )
    _render_map(_PLACEHOLDER_POINTS, placeholder=True)
else:
    _render_map(points)

    st.divider()
    st.subheader("Alerts with Location Data")

    rows = []
    for alert in alerts:
        resolved = _resolve_location(alert)
        if not resolved:
            continue
        _, _, name = resolved
        level = alert.get("risk_level", "LOW")
        rows.append({
            "User":     alert.get("user_id", "—"),
            "Location": name,
            "Risk":     f"{risk_emoji(level)} {level}",
            "Score":    f"{alert.get('risk_score', 0):.0f}",
            "Time":     _fmt_ts(alert.get("timestamp", "")),
        })

    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("No located alerts to display in table.")
