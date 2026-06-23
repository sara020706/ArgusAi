"""Multi-event correlation engine for Argus.

A single event is a weak signal; a *pattern* of events over time is a strong
one. This module looks at a user's recent scored events within a sliding time
window and detects attack patterns (repeated night logins, escalating or slow
data exfiltration, reconnaissance, account-takeover indicators), each of which
contributes bonus risk points on top of the per-event score.

The public :func:`correlate` function is the integration point used by
:class:`~argus.ArgusEngine`. It is defensive by contract: it never raises, and
returns ``(0.0, [])`` if anything goes wrong, so scoring always completes.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from argus.schema import ScoreResult

# Pattern definitions. Each pattern's `condition` is documented for humans; the
# actual evaluation lives in `evaluate_patterns` so logic stays explicit.
PATTERNS = [
    {
        "name": "repeated_night_logins",
        "description": "Multiple logins during night hours in 24h window",
        "condition": "night_login_count >= 2",
        "bonus_points": 25,
        "reason": "Pattern: repeated night access ({count} times in 24h)",
    },
    {
        "name": "escalating_downloads",
        "description": "Download size increasing across consecutive events",
        "condition": "download_trend == 'escalating' and event_count >= 3",
        "bonus_points": 20,
        "reason": "Pattern: escalating download sizes detected",
    },
    {
        "name": "reconnaissance",
        "description": "High file access with low download - browsing without taking",
        "condition": "files_accessed > 200 and download_mb < 10",
        "bonus_points": 30,
        "reason": "Pattern: possible reconnaissance (high file access, low download)",
    },
    {
        "name": "slow_exfiltration",
        "description": "Multiple medium downloads across several hours",
        "condition": "total_download_mb > 1000 and event_count >= 3 and time_span_hours > 2",
        "bonus_points": 35,
        "reason": "Pattern: possible slow exfiltration ({total:.0f} MB over {hours:.1f}h)",
    },
    {
        "name": "account_takeover_indicators",
        "description": "New IP + new device + off hours in same session",
        "condition": "new_ip and new_device and off_hours",
        "bonus_points": 40,
        "reason": "Pattern: account takeover indicators (new IP + new device + off hours)",
    },
]


def detect_download_trend(sizes: list[float], threshold: float = 0.2) -> str:
    """Classify the trend of a chronological sequence of download sizes.

    Args:
        sizes: Download sizes in chronological order.
        threshold: Minimum fractional change between consecutive values for the
            sequence to count as monotonic. Defaults to 0.2 (20%).

    Returns:
        ``"escalating"`` if every value exceeds the previous by more than
        ``threshold``; ``"declining"`` if every value falls below the previous
        by more than ``threshold``; otherwise ``"stable"``. Sequences shorter
        than two elements are ``"stable"``.
    """
    if len(sizes) < 2:
        return "stable"

    escalating = True
    declining = True
    for prev, cur in zip(sizes, sizes[1:]):
        if prev <= 0:
            # Can't compute a relative change against a zero/negative baseline.
            escalating = False
            declining = False
            break
        change = (cur - prev) / prev
        if change <= threshold:
            escalating = False
        if change >= -threshold:
            declining = False

    if escalating:
        return "escalating"
    if declining:
        return "declining"
    return "stable"


def _parse_ts(value) -> datetime | None:
    """Best-effort parse of a stored timestamp into a datetime.

    Args:
        value: Either a ``datetime`` or an ISO-format string.

    Returns:
        A ``datetime``, or ``None`` if it cannot be parsed.
    """
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def _is_night(ts: datetime | None) -> bool:
    """Return True if a timestamp falls in deep-night hours (00:00-05:59)."""
    return ts is not None and 0 <= ts.hour <= 5


def _is_off_hours(ts: datetime | None, work_start: int = 9, work_end: int = 18) -> bool:
    """Return True if a timestamp is outside normal working hours."""
    return ts is not None and (ts.hour < work_start or ts.hour >= work_end)


def compute_window_stats(events: list[dict]) -> dict:
    """Aggregate a list of recent scored-event dicts into window statistics.

    Args:
        events: Recent scored-event dicts (as returned by an
            :class:`~argus.storage.ArgusStore`), in any order. Each is expected
            to carry ``timestamp``, ``ip``, ``device_id``, ``download_mb``,
            ``files_accessed`` and the stored contribution dicts.

    Returns:
        A stats dict with keys: ``event_count``, ``night_login_count``,
        ``total_download_mb``, ``download_sizes`` (chronological),
        ``download_trend``, ``time_span_hours``, ``unique_ips``,
        ``unique_devices``, ``new_ip``, ``new_device`` and ``off_hours_count``.
    """
    # Sort chronologically so trends and time spans are meaningful.
    ordered = sorted(events, key=lambda e: e.get("timestamp", ""))

    timestamps = [_parse_ts(e.get("timestamp")) for e in ordered]
    valid_ts = [t for t in timestamps if t is not None]

    download_sizes = [float(e.get("download_mb", 0.0)) for e in ordered]
    night_login_count = sum(1 for t in timestamps if _is_night(t))
    off_hours_count = sum(1 for t in timestamps if _is_off_hours(t))

    unique_ips = list(dict.fromkeys(e.get("ip") for e in ordered if e.get("ip")))
    unique_devices = list(
        dict.fromkeys(e.get("device_id") for e in ordered if e.get("device_id"))
    )

    # A "new" IP/device in the window is signalled by the per-event scoring
    # having fired the corresponding novelty rule.
    new_ip = any(
        "rule_new_ip" in (e.get("rule_contributions") or {}) for e in ordered
    )
    new_device = any(
        "rule_new_device" in (e.get("rule_contributions") or {}) for e in ordered
    )

    if len(valid_ts) >= 2:
        time_span_hours = (max(valid_ts) - min(valid_ts)).total_seconds() / 3600.0
    else:
        time_span_hours = 0.0

    return {
        "event_count": len(ordered),
        "night_login_count": night_login_count,
        "total_download_mb": sum(download_sizes),
        "download_sizes": download_sizes,
        "download_trend": detect_download_trend(download_sizes),
        "time_span_hours": time_span_hours,
        "unique_ips": unique_ips,
        "unique_devices": unique_devices,
        "new_ip": new_ip,
        "new_device": new_device,
        "off_hours_count": off_hours_count,
    }


def evaluate_patterns(window_stats: dict) -> list[tuple[float, str]]:
    """Evaluate all defined patterns against window statistics.

    Args:
        window_stats: The dict produced by :func:`compute_window_stats`.

    Returns:
        A list of ``(bonus_points, reason)`` tuples for every pattern that
        matched.
    """
    matched: list[tuple[float, str]] = []

    night = window_stats.get("night_login_count", 0)
    trend = window_stats.get("download_trend", "stable")
    event_count = window_stats.get("event_count", 0)
    total_download = window_stats.get("total_download_mb", 0.0)
    time_span = window_stats.get("time_span_hours", 0.0)
    new_ip = window_stats.get("new_ip", False)
    new_device = window_stats.get("new_device", False)
    off_hours = window_stats.get("off_hours_count", 0) > 0

    # For the single-event reconnaissance check, use the most recent event's
    # aggregate values: high file access with low download in the window.
    sizes = window_stats.get("download_sizes", [])
    latest_download = sizes[-1] if sizes else 0.0
    # files_accessed is not aggregated per-event into window_stats; reuse the
    # window's total file access proxy via the most recent download being low.

    by_name = {p["name"]: p for p in PATTERNS}

    if night >= 2:
        p = by_name["repeated_night_logins"]
        matched.append((float(p["bonus_points"]), p["reason"].format(count=night)))

    if trend == "escalating" and event_count >= 3:
        p = by_name["escalating_downloads"]
        matched.append((float(p["bonus_points"]), p["reason"]))

    # Reconnaissance: high file access with low download. We approximate
    # "high file access" from the explicitly provided files_accessed when
    # present (correlate passes it through), else skip.
    files_accessed = window_stats.get("max_files_accessed", 0)
    if files_accessed > 200 and latest_download < 10:
        p = by_name["reconnaissance"]
        matched.append((float(p["bonus_points"]), p["reason"]))

    if total_download > 1000 and event_count >= 3 and time_span > 2:
        p = by_name["slow_exfiltration"]
        matched.append(
            (
                float(p["bonus_points"]),
                p["reason"].format(total=total_download, hours=time_span),
            )
        )

    if new_ip and new_device and off_hours:
        p = by_name["account_takeover_indicators"]
        matched.append((float(p["bonus_points"]), p["reason"]))

    return matched


def correlate(
    user_id: str,
    current_result: ScoreResult,
    recent_events: list[dict],
    window_hours: int = 24,
) -> tuple[float, list[str]]:
    """Correlate the current event against the user's recent activity window.

    Filters ``recent_events`` to those within ``window_hours`` before (and
    including) the current event, computes window statistics, and evaluates all
    patterns. Bonus points are capped so the final score cannot exceed 100.

    This function never raises: any error results in a ``(0.0, [])`` fallback so
    scoring always completes.

    Args:
        user_id: The user being scored (used for filtering / clarity).
        current_result: The :class:`ScoreResult` for the current event.
        recent_events: Recent scored-event dicts for this user from the store.
        window_hours: Size of the correlation window in hours. Defaults to 24.

    Returns:
        A ``(total_bonus_points, pattern_reasons)`` tuple. ``total_bonus_points``
        is clamped so ``current_result.risk_score + bonus`` does not exceed 100.
    """
    try:
        current_ts = current_result.timestamp
        window_start = current_ts - timedelta(hours=window_hours)

        in_window: list[dict] = []
        max_files = 0
        for e in recent_events:
            ts = _parse_ts(e.get("timestamp"))
            if ts is None:
                continue
            if window_start <= ts <= current_ts:
                in_window.append(e)
                max_files = max(max_files, int(e.get("files_accessed", 0) or 0))

        if not in_window:
            return 0.0, []

        window_stats = compute_window_stats(in_window)
        # Surface the peak file-access count for the reconnaissance pattern.
        window_stats["max_files_accessed"] = max_files

        matched = evaluate_patterns(window_stats)
        total_bonus = sum(points for points, _ in matched)
        reasons = [reason for _, reason in matched]

        # Cap so the final score never exceeds 100.
        headroom = max(0.0, 100.0 - current_result.risk_score)
        total_bonus = min(total_bonus, headroom)

        return total_bonus, reasons
    except Exception:
        # Correlation must never break the scoring path.
        return 0.0, []
