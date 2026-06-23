"""Synthetic activity-data generator for Argus.

Produces realistic *normal* and *anomalous* user activity events for training
and testing the ML detector and the rest of the pipeline. Uses only the
standard library (``random``, ``math``, ``datetime``). Each role in
:data:`USER_PROFILES` has its own characteristic login time, download volume
and file-access behaviour.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from argus.features import build_feature_vector
from argus.schema import Event

# Behavioral templates per role. Values are the mean/std of gaussian draws.
USER_PROFILES = {
    "analyst": {"login_mean": 9.0, "login_std": 0.5, "dl_mean": 50, "dl_std": 15, "files_mean": 20, "files_std": 5},
    "developer": {"login_mean": 9.5, "login_std": 1.0, "dl_mean": 200, "dl_std": 50, "files_mean": 80, "files_std": 20},
    "executive": {"login_mean": 8.0, "login_std": 0.5, "dl_mean": 30, "dl_std": 10, "files_mean": 10, "files_std": 3},
    "sysadmin": {"login_mean": 8.5, "login_std": 1.5, "dl_mean": 500, "dl_std": 100, "files_mean": 150, "files_std": 40},
}

OFFICE_IPS = ["192.168.1.{}".format(i) for i in range(1, 20)]
DEVICES = ["laptop-{:02d}".format(i) for i in range(1, 15)]

# Numeric feature keys, in a fixed order, used to build ML training matrices.
NUMERIC_FEATURE_KEYS = [
    "hour",
    "day_of_week",
    "hour_sin",
    "hour_cos",
    "download_mb",
    "files_accessed",
    "download_zscore",
    "files_zscore",
    "is_weekend",
    "is_off_hours",
    "is_night_access",
    "is_new_ip",
    "is_new_device",
]


def _gaussian_clamped(mean: float, std: float, low: float, high: float) -> float:
    """Draw a gaussian sample clamped to ``[low, high]``.

    Args:
        mean: Mean of the gaussian.
        std: Standard deviation of the gaussian.
        low: Inclusive lower bound for the result.
        high: Inclusive upper bound for the result.

    Returns:
        A float sample within ``[low, high]``.
    """
    return max(low, min(high, random.gauss(mean, std)))


def _hour_to_time(date: datetime, hour_float: float) -> datetime:
    """Combine a calendar date with a fractional hour into a datetime.

    Args:
        date: The day to use (time component is ignored).
        hour_float: Hour of day as a float in 0-24.

    Returns:
        A datetime on ``date`` at the given hour and minute.
    """
    hour = int(hour_float) % 24
    minute = int((hour_float - int(hour_float)) * 60) % 60
    return date.replace(hour=hour, minute=minute, second=0, microsecond=0)


def generate_normal_event(
    user_id: str,
    role: str,
    date: datetime,
    known_ips: list[str],
    known_devices: list[str],
) -> Event:
    """Generate a realistic, benign workday event for a user.

    Login time, download size and file count are drawn from gaussians around
    the role's means and clamped to realistic, non-negative bounds. The IP and
    device are chosen from the user's known lists.

    Args:
        user_id: The user the event belongs to.
        role: One of the keys in :data:`USER_PROFILES`.
        date: The calendar day the event occurs on.
        known_ips: IPs considered normal for this user.
        known_devices: Devices considered normal for this user.

    Returns:
        A normal :class:`~argus.schema.Event`.
    """
    p = USER_PROFILES[role]
    hour = _gaussian_clamped(p["login_mean"], p["login_std"], 6.0, 19.0)
    download = _gaussian_clamped(p["dl_mean"], p["dl_std"], 0.0, p["dl_mean"] * 4)
    files = int(_gaussian_clamped(p["files_mean"], p["files_std"], 0.0, p["files_mean"] * 4))

    return Event(
        user_id=user_id,
        timestamp=_hour_to_time(date, hour),
        ip=random.choice(known_ips),
        device_id=random.choice(known_devices),
        download_mb=round(download, 1),
        files_accessed=files,
        action=random.choice(["login", "download", "file_access"]),
    )


def generate_anomalous_event(
    user_id: str,
    anomaly_type: str,
    date: datetime,
    known_ips: list[str],
    known_devices: list[str],
) -> Event:
    """Generate an anomalous event of a given type.

    Args:
        user_id: The user the event belongs to.
        anomaly_type: One of:

            * ``"night_login"`` - login between 01:00 and 04:00.
            * ``"data_exfil"`` - 2000-8000 MB download, 400-800 files.
            * ``"unknown_ip"`` - IP not in ``known_ips``.
            * ``"unknown_device"`` - device not in ``known_devices``.
            * ``"combined"`` - all of the above at once (worst case).
        date: The calendar day the event occurs on.
        known_ips: IPs considered normal for this user.
        known_devices: Devices considered normal for this user.

    Returns:
        An anomalous :class:`~argus.schema.Event`.
    """
    # Sensible defaults resembling a normal event; each anomaly type overrides.
    hour = random.uniform(9.0, 17.0)
    download = round(random.uniform(20.0, 200.0), 1)
    files = random.randint(10, 60)
    ip = random.choice(known_ips)
    device = random.choice(known_devices)

    unknown_ip = "185.45.{}.{}".format(random.randint(1, 254), random.randint(1, 254))
    unknown_device = "unknown-device-{:02d}".format(random.randint(1, 99))

    if anomaly_type == "night_login":
        hour = random.uniform(1.0, 4.0)
    elif anomaly_type == "data_exfil":
        download = round(random.uniform(2000.0, 8000.0), 1)
        files = random.randint(400, 800)
    elif anomaly_type == "unknown_ip":
        ip = unknown_ip
    elif anomaly_type == "unknown_device":
        device = unknown_device
    elif anomaly_type == "combined":
        hour = random.uniform(1.0, 4.0)
        download = round(random.uniform(2000.0, 8000.0), 1)
        files = random.randint(400, 800)
        ip = unknown_ip
        device = unknown_device
    else:
        raise ValueError(f"Unknown anomaly_type: {anomaly_type!r}")

    return Event(
        user_id=user_id,
        timestamp=_hour_to_time(date, hour),
        ip=ip,
        device_id=device,
        download_mb=download,
        files_accessed=files,
        action="download",
    )


def generate_dataset(
    n_users: int = 10,
    days: int = 30,
    anomaly_rate: float = 0.05,
) -> tuple[list[Event], list[bool]]:
    """Generate a full synthetic dataset of events with anomaly labels.

    Each user is assigned a random role. Roughly one normal event per workday
    is produced; weekends have ~80% fewer events. A random ``anomaly_rate``
    fraction of all events are replaced with anomalies of a random type.

    Args:
        n_users: Number of distinct users to simulate.
        days: Number of consecutive days to simulate.
        anomaly_rate: Fraction of events that should be anomalous (0-1).

    Returns:
        A ``(events, labels)`` tuple where ``labels[i]`` is ``True`` if
        ``events[i]`` is anomalous.
    """
    events: list[Event] = []
    labels: list[bool] = []
    anomaly_types = ["night_login", "data_exfil", "unknown_ip", "unknown_device", "combined"]
    start = datetime(2026, 1, 1)

    for u in range(n_users):
        user_id = f"user_{u:03d}"
        role = random.choice(list(USER_PROFILES.keys()))
        # Each user has a small, stable set of known IPs and devices.
        known_ips = random.sample(OFFICE_IPS, k=random.randint(1, 3))
        known_devices = random.sample(DEVICES, k=random.randint(1, 2))

        for d in range(days):
            day = start + timedelta(days=d)
            is_weekend = day.weekday() >= 5
            # ~1 event/workday; weekends get 80% fewer (so ~20% chance of one).
            n_events = 1 if not is_weekend else (1 if random.random() < 0.2 else 0)

            for _ in range(n_events):
                if random.random() < anomaly_rate:
                    atype = random.choice(anomaly_types)
                    events.append(
                        generate_anomalous_event(user_id, atype, day, known_ips, known_devices)
                    )
                    labels.append(True)
                else:
                    events.append(
                        generate_normal_event(user_id, role, day, known_ips, known_devices)
                    )
                    labels.append(False)

    return events, labels


def events_to_feature_matrix(
    events: list[Event],
    profiles: dict[str, dict],
) -> list[list[float]]:
    """Convert events into a 2D numeric matrix for ML training.

    Each row is the numeric feature vector for one event, derived via
    :func:`argus.features.build_feature_vector`. Boolean features are cast to
    ``0.0``/``1.0``. No numpy dependency — returns a list of lists.

    Args:
        events: The events to convert.
        profiles: Mapping of ``user_id`` to that user's scoring-profile dict
            (the shape ``build_feature_vector`` expects). Users not present
            fall back to a neutral zero-baseline profile.

    Returns:
        A list of equal-length lists of floats, one row per event, with columns
        in the order of :data:`NUMERIC_FEATURE_KEYS`.
    """
    neutral_profile = {
        "avg_download_mb": 0.0,
        "std_download_mb": 0.0,
        "avg_files_accessed": 0.0,
        "std_files_accessed": 0.0,
        "known_ips": [],
        "known_devices": [],
    }

    matrix: list[list[float]] = []
    for event in events:
        profile = profiles.get(event.user_id, neutral_profile)
        fv = build_feature_vector(event, profile)
        row = [float(fv[key]) for key in NUMERIC_FEATURE_KEYS]
        matrix.append(row)
    return matrix
