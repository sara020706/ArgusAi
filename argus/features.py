"""Feature extraction functions for Argus.

This module contains only pure functions. Given an :class:`~argus.schema.Event`
and a user profile, the functions here derive the numeric and boolean features
that the rule and statistical engines consume. No classes and no global state
are used, so every function is independently importable and testable.
"""

from __future__ import annotations

import math
from datetime import datetime

from argus.schema import Event


def extract_hour(timestamp: datetime) -> float:
    """Extract the hour of day from a timestamp.

    Args:
        timestamp: The datetime to read the hour from.

    Returns:
        The hour as a float in the range 0.0-23.0. Minutes and seconds are
        included as a fractional part (e.g. ``02:30`` returns ``2.5``).
    """
    return timestamp.hour + timestamp.minute / 60.0 + timestamp.second / 3600.0


def extract_day_of_week(timestamp: datetime) -> int:
    """Extract the day of week from a timestamp.

    Args:
        timestamp: The datetime to read the weekday from.

    Returns:
        The day of week as an integer where 0=Monday and 6=Sunday.
    """
    return timestamp.weekday()


def is_weekend(timestamp: datetime) -> bool:
    """Determine whether a timestamp falls on a weekend.

    Args:
        timestamp: The datetime to check.

    Returns:
        ``True`` if the timestamp is on Saturday or Sunday, else ``False``.
    """
    return timestamp.weekday() >= 5


def is_off_hours(timestamp: datetime, work_start: int = 9, work_end: int = 18) -> bool:
    """Determine whether a timestamp is outside normal working hours.

    Args:
        timestamp: The datetime to check.
        work_start: First hour (inclusive) considered working hours. Defaults
            to 9 (9 AM).
        work_end: Last hour (exclusive) considered working hours. Defaults to
            18 (6 PM).

    Returns:
        ``True`` if the hour is before ``work_start`` or at/after ``work_end``,
        else ``False``.
    """
    hour = timestamp.hour
    return hour < work_start or hour >= work_end


def is_night_access(timestamp: datetime) -> bool:
    """Determine whether a timestamp falls in the deep-night window.

    Args:
        timestamp: The datetime to check.

    Returns:
        ``True`` if the hour is between 0 and 5 inclusive (00:00-05:59),
        else ``False``.
    """
    return 0 <= timestamp.hour <= 5


def cyclic_encode_hour(hour: float) -> tuple[float, float]:
    """Encode an hour cyclically so that 23:00 and 00:00 are close together.

    Using a raw hour value treats 23 and 0 as far apart even though they are
    adjacent in time. Mapping the hour onto a circle via sine and cosine
    preserves this adjacency, which is useful for downstream models.

    Args:
        hour: Hour of day as a float in the range 0.0-23.0.

    Returns:
        A ``(sin_val, cos_val)`` tuple of the hour projected onto the unit
        circle.
    """
    radians = 2.0 * math.pi * hour / 24.0
    return math.sin(radians), math.cos(radians)


def normalize_download(download_mb: float, user_avg_mb: float, user_std_mb: float) -> float:
    """Compute the z-score of a download size against the user's history.

    Args:
        download_mb: The download size for the current event, in megabytes.
        user_avg_mb: The user's historical average download size, in megabytes.
        user_std_mb: The user's historical standard deviation of download size.

    Returns:
        The z-score ``(download_mb - user_avg_mb) / user_std_mb``. If
        ``user_std_mb`` is zero (no variation in history), returns ``0.0`` to
        avoid division by zero.
    """
    if user_std_mb == 0:
        return 0.0
    return (download_mb - user_avg_mb) / user_std_mb


def normalize_file_count(files: int, user_avg_files: float, user_std_files: float) -> float:
    """Compute the z-score of a file-access count against the user's history.

    Args:
        files: Number of files accessed in the current event.
        user_avg_files: The user's historical average file-access count.
        user_std_files: The user's historical standard deviation of file count.

    Returns:
        The z-score ``(files - user_avg_files) / user_std_files``. If
        ``user_std_files`` is zero, returns ``0.0`` to avoid division by zero.
    """
    if user_std_files == 0:
        return 0.0
    return (files - user_avg_files) / user_std_files


def is_new_ip(ip: str, known_ips: list[str]) -> bool:
    """Determine whether an IP address is unrecognized for the user.

    Args:
        ip: The IP address of the current event.
        known_ips: List of IP addresses previously seen for the user.

    Returns:
        ``True`` if ``ip`` is not in ``known_ips``, else ``False``.
    """
    return ip not in known_ips


def is_new_device(device_id: str, known_devices: list[str]) -> bool:
    """Determine whether a device is unrecognized for the user.

    Args:
        device_id: The device identifier of the current event.
        known_devices: List of device identifiers previously seen for the user.

    Returns:
        ``True`` if ``device_id`` is not in ``known_devices``, else ``False``.
    """
    return device_id not in known_devices


def build_feature_vector(event: Event, user_profile: dict) -> dict:
    """Build a flat feature vector from an event and the user's profile.

    This combines every individual feature function in this module into a
    single dictionary suitable for the rule and statistical engines.

    Args:
        event: The :class:`~argus.schema.Event` to extract features from.
        user_profile: A dict describing the user's historical behaviour with
            the keys:

            * ``avg_download_mb`` (float): mean download size.
            * ``std_download_mb`` (float): std dev of download size.
            * ``avg_files_accessed`` (float): mean file-access count.
            * ``std_files_accessed`` (float): std dev of file-access count.
            * ``known_ips`` (list[str]): previously seen IP addresses.
            * ``known_devices`` (list[str]): previously seen device IDs.

    Returns:
        A flat dictionary where every key is a descriptive string and every
        value is a ``float`` or ``bool``. Raw event values needed by rule
        reasons (download size, file count) are passed through as well.
    """
    hour = extract_hour(event.timestamp)
    sin_hour, cos_hour = cyclic_encode_hour(hour)

    download_z = normalize_download(
        event.download_mb,
        user_profile["avg_download_mb"],
        user_profile["std_download_mb"],
    )
    files_z = normalize_file_count(
        event.files_accessed,
        user_profile["avg_files_accessed"],
        user_profile["std_files_accessed"],
    )

    return {
        # Temporal features.
        "hour": hour,
        "day_of_week": float(extract_day_of_week(event.timestamp)),
        "is_weekend": is_weekend(event.timestamp),
        "is_off_hours": is_off_hours(event.timestamp),
        "is_night_access": is_night_access(event.timestamp),
        "hour_sin": sin_hour,
        "hour_cos": cos_hour,
        # Volume features (raw passthrough + normalized).
        "download_mb": float(event.download_mb),
        "files_accessed": float(event.files_accessed),
        "download_zscore": download_z,
        "files_zscore": files_z,
        # Identity / novelty features.
        "is_new_ip": is_new_ip(event.ip, user_profile["known_ips"]),
        "is_new_device": is_new_device(event.device_id, user_profile["known_devices"]),
    }
