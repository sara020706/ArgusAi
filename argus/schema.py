"""Data schemas for the Argus threat detection package.

This module defines the two core dataclasses used throughout Argus:

* :class:`Event` - a single user activity event submitted for scoring.
* :class:`ScoreResult` - the structured result returned after scoring.

Both are plain ``dataclasses`` from the standard library, so the package
has zero external dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Event:
    """A single user activity event to be scored for risk.

    Attributes:
        user_id: Unique identifier for the user who generated the event.
        timestamp: When the event occurred.
        ip: Source IP address of the event.
        device_id: Identifier of the device that generated the event.
        download_mb: Amount of data downloaded during the event, in megabytes.
        files_accessed: Number of files accessed during the event.
        action: The action performed (e.g. ``"login"``, ``"download"``,
            ``"file_access"``, ``"logout"``).
        location: Optional human-readable location of the event. Defaults to
            ``None`` when unknown.
    """

    user_id: str
    timestamp: datetime
    ip: str
    device_id: str
    download_mb: float
    files_accessed: int
    action: str
    location: str | None = None


@dataclass
class ScoreResult:
    """The structured result of scoring a single :class:`Event`.

    Attributes:
        user_id: The user the event belonged to.
        timestamp: The timestamp of the scored event.
        risk_score: Final risk score, clamped to the range 0-100.
        risk_level: Human-readable band: ``"LOW"``, ``"MEDIUM"``, ``"HIGH"``
            or ``"CRITICAL"``.
        rule_contributions: Mapping of rule name to the points that rule added.
        stat_contributions: Mapping of statistical signal name to points added.
        reasons: Ordered, human-readable explanation lines describing why the
            score was assigned.
        raw_features: The flat feature vector dictionary that was used to
            compute the score.
    """

    user_id: str
    timestamp: datetime
    risk_score: float
    risk_level: str
    rule_contributions: dict = field(default_factory=dict)
    stat_contributions: dict = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)
    raw_features: dict = field(default_factory=dict)
