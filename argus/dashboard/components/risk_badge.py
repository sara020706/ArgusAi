"""Risk-level badge and colour helpers for the Argus dashboard.

Pure functions — no Streamlit calls, no side effects. Import freely from any
chart or page module.
"""

from __future__ import annotations

RISK_COLORS = {
    "LOW":      "#22c55e",
    "MEDIUM":   "#f59e0b",
    "HIGH":     "#ef4444",
    "CRITICAL": "#7c3aed",
}

RISK_EMOJI = {
    "LOW":      "🟢",
    "MEDIUM":   "🟡",
    "HIGH":     "🔴",
    "CRITICAL": "🟣",
}

_DEFAULT_COLOR = "#94a3b8"


def risk_color(level: str) -> str:
    """Return the hex colour for a risk level.

    Args:
        level: One of ``"LOW"``, ``"MEDIUM"``, ``"HIGH"``, ``"CRITICAL"``.

    Returns:
        Hex colour string. Falls back to slate-grey for unknown levels.
    """
    return RISK_COLORS.get(level.upper() if level else "", _DEFAULT_COLOR)


def risk_emoji(level: str) -> str:
    """Return the emoji indicator for a risk level.

    Args:
        level: Risk level string.

    Returns:
        A single emoji character. Falls back to ``"⚪"`` for unknown levels.
    """
    return RISK_EMOJI.get(level.upper() if level else "", "⚪")


def render_risk_badge(level: str) -> str:
    """Render a coloured HTML pill badge for a risk level.

    Intended to be used with ``st.markdown(..., unsafe_allow_html=True)`` or
    inside an HTML string that Streamlit will render.

    Args:
        level: Risk level string.

    Returns:
        An HTML ``<span>`` styled as a rounded pill with the appropriate
        background colour. Example output::

            <span style="background:#ef4444; color:white; padding:2px 10px;
                border-radius:12px; font-weight:bold; font-size:0.85em">
                HIGH
            </span>
    """
    colour = risk_color(level)
    label = level.upper() if level else "UNKNOWN"
    return (
        f'<span style="background:{colour}; color:white; padding:2px 10px; '
        f'border-radius:12px; font-weight:bold; font-size:0.85em">'
        f"{label}</span>"
    )


def score_to_color(score: float) -> str:
    """Interpolate a hex colour across the green → amber → red gradient.

    Maps ``0 → #22c55e`` (green), ``50 → #f59e0b`` (amber), ``100 → #ef4444``
    (red) with linear interpolation between the two halves.

    Args:
        score: Risk score in the range 0–100.

    Returns:
        A hex colour string representing the score position on the gradient.
    """
    score = max(0.0, min(100.0, score))

    def _hex(r: int, g: int, b: int) -> str:
        return f"#{r:02x}{g:02x}{b:02x}"

    def _lerp(a: int, b: int, t: float) -> int:
        return int(a + (b - a) * t)

    # Green  #22c55e → (34, 197, 94)
    # Amber  #f59e0b → (245, 158, 11)
    # Red    #ef4444 → (239, 68, 68)
    green = (34, 197, 94)
    amber = (245, 158, 11)
    red   = (239, 68, 68)

    if score <= 50:
        t = score / 50.0
        r = _lerp(green[0], amber[0], t)
        g = _lerp(green[1], amber[1], t)
        b = _lerp(green[2], amber[2], t)
    else:
        t = (score - 50) / 50.0
        r = _lerp(amber[0], red[0], t)
        g = _lerp(amber[1], red[1], t)
        b = _lerp(amber[2], red[2], t)

    return _hex(r, g, b)
