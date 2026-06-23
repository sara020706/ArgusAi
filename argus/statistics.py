"""Statistical anomaly scoring for Argus.

These pure functions convert per-user statistical deviations (z-scores stored
in the feature vector) into risk points. Unlike the binary heuristic rules,
these signals scale with how far a value deviates from the user's personal
baseline. All thresholds and weights are parameters with sensible defaults.
"""

from __future__ import annotations


def zscore_contribution(z: float, weight: float = 10.0) -> float:
    """Convert a z-score into risk points using graduated bands.

    The magnitude of the z-score is used, so deviations in either direction are
    treated symmetrically. The banding is:

    * ``|z| < 1.5``  -> ``0`` points (within normal variation).
    * ``1.5 <= |z| < 2``  -> ``weight * 0.5``.
    * ``2 <= |z| < 3``  -> ``weight * 1.0``.
    * ``|z| >= 3``  -> ``weight * 2.0``.

    Args:
        z: The z-score to convert.
        weight: The base weight that scales each band. Defaults to 10.

    Returns:
        Risk points as a float.
    """
    magnitude = abs(z)
    if magnitude < 1.5:
        return 0.0
    if magnitude < 2.0:
        return weight * 0.5
    if magnitude < 3.0:
        return weight * 1.0
    return weight * 2.0


def stat_download_deviation(fv: dict, weight: float = 15.0) -> tuple[float, str | None]:
    """Score how far the download size deviates from the user's average.

    Args:
        fv: The feature vector; uses the ``download_zscore`` key.
        weight: Base weight passed to :func:`zscore_contribution`. Defaults to 15.

    Returns:
        ``(points, reason)`` if the deviation is significant, else
        ``(0.0, None)``.
    """
    z = fv.get("download_zscore", 0.0)
    points = zscore_contribution(z, weight=weight)
    if points > 0:
        return points, f"Download size {z:.1f}x above personal average"
    return 0.0, None


def stat_file_access_deviation(fv: dict, weight: float = 10.0) -> tuple[float, str | None]:
    """Score how far the file-access count deviates from the user's average.

    Args:
        fv: The feature vector; uses the ``files_zscore`` key.
        weight: Base weight passed to :func:`zscore_contribution`. Defaults to 10.

    Returns:
        ``(points, reason)`` if the deviation is significant, else
        ``(0.0, None)``.
    """
    z = fv.get("files_zscore", 0.0)
    points = zscore_contribution(z, weight=weight)
    if points > 0:
        return points, f"File access count {z:.1f}x above personal average"
    return 0.0, None


def evaluate_all_stats(feature_vector: dict) -> dict[str, tuple[float, str | None]]:
    """Run every statistical signal and collect those that fired.

    Args:
        feature_vector: The feature vector produced by ``build_feature_vector``.

    Returns:
        A dict mapping stat name to its ``(points, reason)`` tuple. Only stats
        that fired (``points > 0``) are included.
    """
    all_stats = {
        "stat_download_deviation": stat_download_deviation,
        "stat_file_access_deviation": stat_file_access_deviation,
    }

    fired: dict[str, tuple[float, str | None]] = {}
    for name, stat_fn in all_stats.items():
        points, reason = stat_fn(feature_vector)
        if points > 0:
            fired[name] = (points, reason)
    return fired
