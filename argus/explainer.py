"""Human-readable explanation rendering for Argus.

These pure functions take a :class:`~argus.schema.ScoreResult` and produce
either a formatted multi-line report or a clean JSON-serializable summary dict.
"""

from __future__ import annotations

from argus.scorer import RISK_BANDS  # noqa: F401  (kept for API discoverability)
from argus.schema import ScoreResult

# Recommended action text keyed by risk level.
RECOMMENDED_ACTIONS = {
    "LOW": "Monitor - no immediate action required",
    "MEDIUM": "Review user activity for the past 24 hours",
    "HIGH": "Investigate immediately and consider session termination",
    "CRITICAL": "Escalate to security team - possible active threat",
}


def format_reason_line(rank: int, reason: str, points: float) -> str:
    """Format a single contributing-factor line for the explanation report.

    Args:
        rank: 1-based rank of this reason (highest contribution first).
        reason: The human-readable reason text.
        points: Points this factor contributed to the score.

    Returns:
        A formatted line, e.g. ``"  #1 (+35 pts) Login during night hours"``.
    """
    return f"  #{rank} (+{points:.0f} pts) {reason}"


def _contribution_points(value) -> float:
    """Extract the numeric point value from a contribution entry.

    Most contributions store a plain number, but some layers (threat intel,
    correlation) store a ``(points, reason)`` tuple. Normalize both shapes to a
    single float so values can be ranked together.

    Args:
        value: A contribution value — either a number or a ``(points, reason)``
            tuple/list.

    Returns:
        The numeric points as a float (``0.0`` if it can't be interpreted).
    """
    if isinstance(value, (tuple, list)):
        value = value[0] if value else 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _ranked_contributions(result: ScoreResult) -> list[tuple[str, float]]:
    """Pair each reason with its point value, ranked highest-first.

    The scorer already stores ``reasons`` in descending point order and stores
    every contribution value in ``rule_contributions`` / ``stat_contributions``.
    This helper re-associates each reason with its points by drawing from a
    sorted pool of contribution values. Contribution values may be plain
    numbers or ``(points, reason)`` tuples; both are handled.

    Args:
        result: The score result to read contributions and reasons from.

    Returns:
        A list of ``(reason, points)`` tuples in descending point order.
    """
    point_pool = sorted(
        (
            _contribution_points(v)
            for v in list(result.rule_contributions.values())
            + list(result.stat_contributions.values())
        ),
        reverse=True,
    )
    paired: list[tuple[str, float]] = []
    for reason, points in zip(result.reasons, point_pool):
        paired.append((reason, points))
    return paired


def build_explanation(result: ScoreResult) -> str:
    """Build a full multi-line, human-readable explanation of a score.

    Args:
        result: The :class:`~argus.schema.ScoreResult` to render.

    Returns:
        A multi-line string containing a header box, the ranked contributing
        factors, and a recommended action for the risk level.
    """
    header_lines = [
        "+-------------------------------------+",
        "|  ARGUS THREAT ASSESSMENT            |",
        f"|  User: {result.user_id}",
        f"|  Time: {result.timestamp}",
        f"|  Risk Score: {result.risk_score:.0f}/100 [{result.risk_level}]",
        "+-------------------------------------+",
    ]

    body_lines = ["", "Contributing Factors:"]
    ranked = _ranked_contributions(result)
    if ranked:
        for rank, (reason, points) in enumerate(ranked, start=1):
            body_lines.append(format_reason_line(rank, reason, points))
    else:
        body_lines.append("  (none - behaviour within normal parameters)")

    action = RECOMMENDED_ACTIONS.get(result.risk_level, "Review user activity")
    footer_lines = ["", f"Recommended Action: {action}"]

    return "\n".join(header_lines + body_lines + footer_lines)


def summarize_result(result: ScoreResult) -> dict:
    """Produce a clean, JSON-serializable summary of a score result.

    All ``datetime`` values are converted to ISO 8601 strings so the dict can
    be passed directly to ``json.dumps``.

    Args:
        result: The :class:`~argus.schema.ScoreResult` to summarize.

    Returns:
        A JSON-serializable dict containing the user, timestamp, score, level,
        contributions, reasons and raw feature vector.
    """
    return {
        "user_id": result.user_id,
        "timestamp": result.timestamp.isoformat(),
        "risk_score": result.risk_score,
        "risk_level": result.risk_level,
        "rule_contributions": dict(result.rule_contributions),
        "stat_contributions": dict(result.stat_contributions),
        "reasons": list(result.reasons),
        "raw_features": dict(result.raw_features),
    }
