"""Heuristic rule engine for Argus.

Each rule is a pure function that inspects a feature vector and returns a
``(points, reason)`` tuple. ``points`` is the number of risk points the rule
contributes and ``reason`` is a human-readable string explaining why the rule
fired (or ``None`` if it did not fire). Thresholds are exposed as parameters
with sensible defaults so there are no hidden magic numbers.
"""

from __future__ import annotations


def rule_night_access(fv: dict, points: float = 35.0) -> tuple[float, str | None]:
    """Flag access during deep-night hours (00:00-05:00).

    Args:
        fv: The feature vector produced by ``build_feature_vector``.
        points: Points to award when the rule fires. Defaults to 35.

    Returns:
        ``(points, reason)`` if ``is_night_access`` is True, else ``(0.0, None)``.
    """
    if fv.get("is_night_access"):
        return points, "Login during night hours (00:00-05:00)"
    return 0.0, None


def rule_off_hours(fv: dict, points: float = 20.0) -> tuple[float, str | None]:
    """Flag access outside normal working hours.

    To avoid double counting with :func:`rule_night_access`, this rule does not
    fire if the event already qualifies as night access.

    Args:
        fv: The feature vector produced by ``build_feature_vector``.
        points: Points to award when the rule fires. Defaults to 20.

    Returns:
        ``(points, reason)`` if the event is off-hours but not night access,
        else ``(0.0, None)``.
    """
    if fv.get("is_off_hours") and not fv.get("is_night_access"):
        return points, "Login outside normal working hours"
    return 0.0, None


def rule_weekend_access(fv: dict, points: float = 10.0) -> tuple[float, str | None]:
    """Flag activity occurring on a weekend.

    Args:
        fv: The feature vector produced by ``build_feature_vector``.
        points: Points to award when the rule fires. Defaults to 10.

    Returns:
        ``(points, reason)`` if ``is_weekend`` is True, else ``(0.0, None)``.
    """
    if fv.get("is_weekend"):
        return points, "Activity on weekend"
    return 0.0, None


def rule_large_download(
    fv: dict,
    threshold_mb: float = 1000.0,
    base_points: float = 30.0,
    max_points: float = 50.0,
    scale_multiple: float = 5.0,
) -> tuple[float, str | None]:
    """Flag unusually large downloads.

    Awards ``base_points`` once the download exceeds ``threshold_mb`` and
    scales linearly up to ``max_points`` as the download approaches
    ``scale_multiple`` times the threshold.

    Args:
        fv: The feature vector produced by ``build_feature_vector``.
        threshold_mb: Download size in MB above which the rule fires. Defaults
            to 1000.
        base_points: Points awarded at exactly the threshold. Defaults to 30.
        max_points: Maximum points awarded for very large downloads. Defaults
            to 50.
        scale_multiple: Multiple of the threshold at which ``max_points`` is
            reached. Defaults to 5 (i.e. 5x the threshold).

    Returns:
        ``(points, reason)`` if the download exceeds the threshold, where
        points are scaled between ``base_points`` and ``max_points``. Otherwise
        ``(0.0, None)``.
    """
    download_mb = fv.get("download_mb", 0.0)
    if download_mb <= threshold_mb:
        return 0.0, None

    # Fraction of the way from the threshold to scale_multiple * threshold.
    span = threshold_mb * (scale_multiple - 1.0)
    if span <= 0:
        fraction = 1.0
    else:
        fraction = min((download_mb - threshold_mb) / span, 1.0)
    points = base_points + (max_points - base_points) * fraction

    reason = (
        f"Large download: {download_mb:.0f} MB "
        f"(threshold: {threshold_mb:.0f} MB)"
    )
    return points, reason


def rule_excessive_files(
    fv: dict, threshold: int = 100, points: float = 25.0
) -> tuple[float, str | None]:
    """Flag access to an excessive number of files.

    Args:
        fv: The feature vector produced by ``build_feature_vector``.
        threshold: File count above which the rule fires. Defaults to 100.
        points: Points to award when the rule fires. Defaults to 25.

    Returns:
        ``(points, reason)`` if files accessed exceeds the threshold, else
        ``(0.0, None)``.
    """
    files_accessed = fv.get("files_accessed", 0.0)
    if files_accessed > threshold:
        return points, f"Excessive file access: {int(files_accessed)} files"
    return 0.0, None


def rule_new_ip(fv: dict, points: float = 20.0) -> tuple[float, str | None]:
    """Flag a login from an unrecognized IP address.

    Args:
        fv: The feature vector produced by ``build_feature_vector``.
        points: Points to award when the rule fires. Defaults to 20.

    Returns:
        ``(points, reason)`` if ``is_new_ip`` is True, else ``(0.0, None)``.
    """
    if fv.get("is_new_ip"):
        return points, "Login from unrecognized IP address"
    return 0.0, None


def rule_new_device(fv: dict, points: float = 20.0) -> tuple[float, str | None]:
    """Flag a login from an unrecognized device.

    Args:
        fv: The feature vector produced by ``build_feature_vector``.
        points: Points to award when the rule fires. Defaults to 20.

    Returns:
        ``(points, reason)`` if ``is_new_device`` is True, else ``(0.0, None)``.
    """
    if fv.get("is_new_device"):
        return points, "Login from unrecognized device"
    return 0.0, None


def evaluate_all_rules(feature_vector: dict) -> dict[str, tuple[float, str | None]]:
    """Run every rule against a feature vector and collect those that fired.

    Args:
        feature_vector: The feature vector produced by ``build_feature_vector``.

    Returns:
        A dict mapping rule name to its ``(points, reason)`` tuple. Only rules
        that fired (``points > 0``) are included.
    """
    all_rules = {
        "rule_night_access": rule_night_access,
        "rule_off_hours": rule_off_hours,
        "rule_weekend_access": rule_weekend_access,
        "rule_large_download": rule_large_download,
        "rule_excessive_files": rule_excessive_files,
        "rule_new_ip": rule_new_ip,
        "rule_new_device": rule_new_device,
    }

    fired: dict[str, tuple[float, str | None]] = {}
    for name, rule_fn in all_rules.items():
        points, reason = rule_fn(feature_vector)
        if points > 0:
            fired[name] = (points, reason)
    return fired
