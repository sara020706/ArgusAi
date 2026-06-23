import streamlit as st

RISK_COLORS = {
    "LOW":      "#4ade80",
    "MEDIUM":   "#fbbf24",
    "HIGH":     "#f87171",
    "CRITICAL": "#c084fc",
}

_DEFAULT_COLOR = "#64748b"


def render_risk_badge(level: str) -> str:
    cls = f"badge-{level.lower()}"
    return f'<span class="badge {cls}">&#9642; {level}</span>'


def render_score_bar(score: float, level: str) -> str:
    color = RISK_COLORS.get(level, _DEFAULT_COLOR)
    return (
        f'<div class="stat-bar-bg">'
        f'<div class="stat-bar-fill" style="width:{min(score,100)}%;background:{color}"></div>'
        f'</div>'
    )


def level_color(level: str) -> str:
    return RISK_COLORS.get(level, _DEFAULT_COLOR)


def level_border_style(level: str) -> str:
    color = RISK_COLORS.get(level)
    if color:
        return f"border-left: 2px solid {color}; padding-left: 10px;"
    return ""


def risk_color(level: str) -> str:
    return RISK_COLORS.get(level.upper() if level else "", _DEFAULT_COLOR)


def score_to_color(score: float) -> str:
    score = max(0.0, min(100.0, score))

    def _lerp(a: int, b: int, t: float) -> int:
        return int(a + (b - a) * t)

    green = (74, 222, 128)
    amber = (251, 191, 36)
    red   = (248, 113, 113)

    if score <= 50:
        t = score / 50.0
        r, g, b = _lerp(green[0], amber[0], t), _lerp(green[1], amber[1], t), _lerp(green[2], amber[2], t)
    else:
        t = (score - 50) / 50.0
        r, g, b = _lerp(amber[0], red[0], t), _lerp(amber[1], red[1], t), _lerp(amber[2], red[2], t)

    return f"#{r:02x}{g:02x}{b:02x}"
