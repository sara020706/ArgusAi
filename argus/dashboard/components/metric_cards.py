import streamlit as st


def render_kpi_row(stats: list) -> None:
    if not stats:
        return
    cols = st.columns(len(stats))
    for col, s in zip(cols, stats):
        with col:
            st.metric(
                label=s.get("label", ""),
                value=s.get("value", "—"),
                delta=s.get("sublabel"),
            )


def render_system_status(health: dict) -> None:
    items = [
        ("API",   health.get("status") == "healthy"),
        ("DB",    health.get("db_connected", False)),
        ("ML",    health.get("ml_enabled", False)),
        ("Intel", health.get("threat_intel_enabled", False)),
    ]
    rows = []
    for name, ok in items:
        color = "#16A34A" if ok else "#CBD5E1"
        label = "Connected" if ok else "Off"
        rows.append(
            f'<div style="display:flex;align-items:center;justify-content:space-between;'
            f'padding:5px 0;font-size:0.78rem">'
            f'<span style="color:#475569;font-weight:500">'
            f'<span style="display:inline-block;width:7px;height:7px;border-radius:50%;'
            f'background:{color};margin-right:8px;vertical-align:middle"></span>{name}</span>'
            f'<span style="color:#94A3B8;font-size:0.72rem">{label}</span>'
            f'</div>'
        )
    st.markdown(
        '<div style="margin:6px 0 14px">' + "".join(rows) + "</div>",
        unsafe_allow_html=True,
    )


def render_page_header(title: str, subtitle: str) -> None:
    st.markdown(
        f'<div class="page-title">{title}</div>'
        f'<div class="page-subtitle">{subtitle}</div>',
        unsafe_allow_html=True,
    )


def render_metric_row(metrics: list) -> None:
    if not metrics:
        return
    cols = st.columns(len(metrics))
    for col, m in zip(cols, metrics):
        with col:
            st.metric(
                label=m.get("label", ""),
                value=m.get("value", "—"),
                delta=m.get("delta"),
            )


def render_stat_card(title: str, value: str, color: str) -> None:
    st.markdown(
        f"""
        <div style="
            background: #FFFFFF;
            border-left: 3px solid {color};
            border: 1px solid #E6E9F0;
            border-radius: 12px;
            padding: 16px 20px;
            margin-bottom: 8px;
            box-shadow: 0 1px 2px rgba(16,24,40,.05);
        ">
            <div style="color:#94A3B8; font-size:0.7rem; text-transform:uppercase;
                        letter-spacing:0.06em; margin-bottom:5px; font-weight:600">{title}</div>
            <div style="color:#0F172A; font-size:1.6em; font-weight:700;
                        line-height:1; font-family:'JetBrains Mono',ui-monospace,monospace">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
