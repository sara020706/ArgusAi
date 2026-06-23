"""Shared normalization helpers for all Argus collectors.

Every collector's ``parse_line()`` ends by calling :func:`build_event`, which
calls each ``normalize_*`` function below. This guarantees a consistent,
well-typed :class:`~argus.schema.Event` regardless of source format.

Only the Python standard library (``re``, ``datetime``, ``math``, ``logging``)
is used here — no external dependencies.
"""

from __future__ import annotations

import logging
import math
import re
from datetime import datetime

from argus.schema import Event

logger = logging.getLogger(__name__)

UNKNOWN_DEVICE   = "unknown-device"
UNKNOWN_IP       = "0.0.0.0"
UNKNOWN_LOCATION = "unknown"

# ── Timestamp normalisation ───────────────────────────────────────────────────

_TS_FORMATS = [
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S.%f",
    "%m/%d/%Y %I:%M:%S %p",   # Windows: "6/16/2026 2:15:00 AM"
    "%m/%d/%Y %H:%M:%S",
    "%b %d %H:%M:%S",          # syslog: "Jun 16 02:15:00"
    "%b  %d %H:%M:%S",         # syslog single-digit day: "Jun  6 02:15:00"
]


def normalize_timestamp(raw: str | datetime) -> datetime:
    """Parse a raw timestamp value into a :class:`datetime`.

    Accepts the following formats:

    * ISO 8601 with or without fractional seconds.
    * ``"%Y-%m-%d %H:%M:%S"`` (SQL-style).
    * Windows Event Log: ``"6/16/2026 2:15:00 AM"``.
    * Linux syslog: ``"Jun 16 02:15:00"`` (year set to current year).
    * Unix timestamp as an integer-valued string: ``"1750039800"``.

    Args:
        raw: Timestamp string or an already-parsed :class:`datetime`.

    Returns:
        A :class:`datetime`. Falls back to ``datetime.now()`` with a warning
        if no format matches.
    """
    if isinstance(raw, datetime):
        return raw

    raw = str(raw).strip()

    # Unix timestamp
    if re.fullmatch(r"\d{9,11}", raw):
        try:
            return datetime.fromtimestamp(int(raw))
        except Exception:
            pass

    for fmt in _TS_FORMATS:
        try:
            dt = datetime.strptime(raw[:26], fmt)
            # Syslog lines lack a year — use current year.
            if dt.year == 1900:
                dt = dt.replace(year=datetime.now().year)
            return dt
        except ValueError:
            continue

    logger.warning("normalize_timestamp: unrecognized format %r — using now()", raw)
    return datetime.now()


# ── IP normalisation ──────────────────────────────────────────────────────────

_IP_PORT_RE = re.compile(r"^([\d.]+):\d+$")


def normalize_ip(raw: str | None) -> str:
    """Strip the port from an IP:port string and return a bare IP.

    Args:
        raw: An IP address string, optionally with a port suffix
            (``"192.168.1.5:54231"``), or ``None``.

    Returns:
        The bare IP string, or :data:`UNKNOWN_IP` if ``raw`` is empty/None.
    """
    if not raw:
        return UNKNOWN_IP
    raw = str(raw).strip()
    m = _IP_PORT_RE.match(raw)
    return m.group(1) if m else raw


# ── User-ID normalisation ─────────────────────────────────────────────────────

def normalize_user_id(raw: str | None) -> str:
    """Normalise a raw user identifier to a clean lowercase username.

    Handles:

    * Domain-prefixed names: ``"DOMAIN\\\\john"`` → ``"john"``
    * Email addresses: ``"john@corp.com"`` → ``"john"``
    * Leading/trailing whitespace.

    Args:
        raw: Raw username string or ``None``.

    Returns:
        A normalised lowercase string, or ``"unknown"`` if empty/None.
    """
    if not raw:
        return "unknown"
    user = str(raw).strip()
    # "DOMAIN\user" or "DOMAIN/user"
    if "\\" in user:
        user = user.split("\\")[-1]
    elif "/" in user and not user.startswith("/"):
        user = user.split("/")[-1]
    # "user@domain"
    if "@" in user:
        user = user.split("@")[0]
    return user.lower().strip() or "unknown"


# ── Download size normalisation ───────────────────────────────────────────────

_SIZE_RE = re.compile(r"([\d.]+)\s*(B|KB|MB|GB|TB)?", re.IGNORECASE)


def normalize_download_mb(raw: str | float | int | None) -> float:
    """Convert a raw transfer-size value to megabytes.

    Understands the following forms:

    * Plain number treated as **bytes** (e.g. ``5000`` → 0.00477 MB).
    * ``"500B"``, ``"4.88KB"``, ``"1.2MB"``, ``"0.5GB"``, ``"0.001TB"``.

    Args:
        raw: The raw size value. ``None`` or an unparseable string returns 0.0.

    Returns:
        Size in megabytes as a float.
    """
    if raw is None:
        return 0.0
    if isinstance(raw, (int, float)):
        # Bare numeric value assumed to be bytes.
        return float(raw) / (1024 * 1024)

    raw_str = str(raw).strip()
    m = _SIZE_RE.match(raw_str)
    if not m:
        return 0.0

    value = float(m.group(1))
    unit = (m.group(2) or "B").upper()

    multipliers = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}
    bytes_val = value * multipliers.get(unit, 1)
    return bytes_val / (1024 * 1024)


# ── File-count normalisation ──────────────────────────────────────────────────

_NON_NUMERIC_RE = re.compile(r"[^\d]")


def normalize_file_count(raw: str | int | None) -> int:
    """Parse a raw file-count value to a non-negative integer.

    Args:
        raw: An integer, a numeric string, or a string with non-numeric
            characters that will be stripped (e.g. ``"42 files"`` → 42).

    Returns:
        Integer file count, or 0 if unparseable or None.
    """
    if raw is None:
        return 0
    if isinstance(raw, int):
        return max(0, raw)
    cleaned = _NON_NUMERIC_RE.sub("", str(raw))
    try:
        return max(0, int(cleaned))
    except ValueError:
        return 0


# ── Event builder ─────────────────────────────────────────────────────────────

def build_event(
    user_id: str,
    timestamp: str | datetime,
    ip: str | None = None,
    device_id: str | None = None,
    download_mb: float | str | None = None,
    files_accessed: int | str | None = None,
    action: str = "login",
    location: str | None = None,
) -> Event:
    """Build a fully normalised :class:`~argus.schema.Event`.

    This is the single function all collectors call at the end of their
    ``parse_line()`` implementation. It applies every ``normalize_*``
    function so the caller never needs to call them individually.

    Args:
        user_id: Raw user identifier (domain prefix and email suffix stripped).
        timestamp: Raw timestamp in any format accepted by
            :func:`normalize_timestamp`.
        ip: Raw IP address, optionally with port (stripped automatically).
        device_id: Device or hostname string. Defaults to
            :data:`UNKNOWN_DEVICE` if ``None``.
        download_mb: Transfer size in any unit (see
            :func:`normalize_download_mb`).
        files_accessed: File-access count (see :func:`normalize_file_count`).
        action: Activity type string (e.g. ``"login"``, ``"download"``).
        location: Optional human-readable location string.

    Returns:
        A clean :class:`~argus.schema.Event` ready for the scoring engine.
    """
    return Event(
        user_id=normalize_user_id(user_id),
        timestamp=normalize_timestamp(timestamp),
        ip=normalize_ip(ip),
        device_id=normalize_user_id(device_id) if device_id else UNKNOWN_DEVICE,
        download_mb=normalize_download_mb(download_mb),
        files_accessed=normalize_file_count(files_accessed),
        action=action or "login",
        location=location or None,
    )
