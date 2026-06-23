"""Scoring engine for Argus.

This module ties together the feature, rule and statistical layers to produce
a single :class:`~argus.schema.ScoreResult` for an event. It defines the risk
banding, helpers to clamp and label scores, and the main :func:`compute_score`
entry point.
"""

from __future__ import annotations

from argus.features import build_feature_vector
from argus.rules import evaluate_all_rules
from argus.schema import Event, ScoreResult
from argus.statistics import evaluate_all_stats

# Risk bands as (low_inclusive, high_inclusive, label) tuples covering 0-100.
RISK_BANDS = [
    (0, 30, "LOW"),
    (31, 60, "MEDIUM"),
    (61, 85, "HIGH"),
    (86, 100, "CRITICAL"),
]


def get_risk_level(score: float) -> str:
    """Map a numeric risk score to its categorical risk level.

    Args:
        score: A risk score, expected in the range 0-100.

    Returns:
        One of ``"LOW"``, ``"MEDIUM"``, ``"HIGH"`` or ``"CRITICAL"``. Scores
        are matched against :data:`RISK_BANDS`; anything at or above the top
        band's lower bound is treated as ``"CRITICAL"``.
    """
    for low, high, label in RISK_BANDS:
        if low <= score <= high:
            return label
    # Defensive fallback: scores above the defined bands are CRITICAL.
    return RISK_BANDS[-1][2]


def cap_score(score: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    """Clamp a score to a valid range.

    Args:
        score: The raw, uncapped score.
        minimum: Lower bound of the valid range. Defaults to 0.
        maximum: Upper bound of the valid range. Defaults to 100.

    Returns:
        ``score`` clamped to ``[minimum, maximum]``.
    """
    return max(minimum, min(score, maximum))


def compute_score(
    event: Event,
    user_profile: dict,
    rule_weight: float = 1.0,
    stat_weight: float = 1.0,
) -> ScoreResult:
    """Score a single event against a user profile.

    Steps:
        1. Build the feature vector from the event and profile.
        2. Evaluate all heuristic rules.
        3. Evaluate all statistical signals.
        4. Sum the (weighted) points from rules and stats.
        5. Cap the total at 100.
        6. Resolve the risk level.
        7. Assemble a :class:`~argus.schema.ScoreResult` with all
           contributions and human-readable reasons.

    Args:
        event: The :class:`~argus.schema.Event` to score.
        user_profile: The user's historical profile dict (see
            ``build_feature_vector`` for required keys).
        rule_weight: Multiplier applied to all rule points. Defaults to 1.0.
        stat_weight: Multiplier applied to all stat points. Defaults to 1.0.

    Returns:
        A fully populated :class:`~argus.schema.ScoreResult`.
    """
    feature_vector = build_feature_vector(event, user_profile)
    rule_results = evaluate_all_rules(feature_vector)
    stat_results = evaluate_all_stats(feature_vector)

    rule_contributions: dict[str, float] = {}
    stat_contributions: dict[str, float] = {}
    # Collect reasons with their points so they can be ranked highest-first.
    scored_reasons: list[tuple[float, str]] = []

    total = 0.0

    for name, (points, reason) in rule_results.items():
        weighted = points * rule_weight
        rule_contributions[name] = weighted
        total += weighted
        if reason:
            scored_reasons.append((weighted, reason))

    for name, (points, reason) in stat_results.items():
        weighted = points * stat_weight
        stat_contributions[name] = weighted
        total += weighted
        if reason:
            scored_reasons.append((weighted, reason))

    risk_score = cap_score(total)
    risk_level = get_risk_level(risk_score)

    # Rank reasons by descending points for the explanation.
    scored_reasons.sort(key=lambda item: item[0], reverse=True)
    reasons = [reason for _, reason in scored_reasons]

    return ScoreResult(
        user_id=event.user_id,
        timestamp=event.timestamp,
        risk_score=risk_score,
        risk_level=risk_level,
        rule_contributions=rule_contributions,
        stat_contributions=stat_contributions,
        reasons=reasons,
        raw_features=feature_vector,
    )
