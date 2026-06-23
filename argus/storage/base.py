"""Abstract storage interface for Argus.

Argus persists two kinds of data: per-user behavioral *profiles* and the
*scored events* it produces. Rather than hard-coding a single database, all
persistence goes through the :class:`ArgusStore` abstract base class. Host
applications can plug in the bundled :class:`~argus.storage.SQLiteStore` or
:class:`~argus.storage.MemoryStore`, or implement their own backed by whatever
database they already run.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from argus.schema import Event, ScoreResult

# Ordering used to compare risk levels (LOW < MEDIUM < HIGH < CRITICAL).
RISK_LEVEL_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


class ArgusStore(ABC):
    """Abstract persistence backend for profiles and scored events."""

    @abstractmethod
    def get_profile(self, user_id: str) -> dict | None:
        """Retrieve the stored profile for a user.

        Args:
            user_id: The user whose profile to load.

        Returns:
            The profile dict, or ``None`` if the user has no profile yet.
            Profile shape::

                {
                    "user_id": str,
                    "avg_download_mb": float,
                    "std_download_mb": float,
                    "avg_files_accessed": float,
                    "std_files_accessed": float,
                    "known_ips": list[str],
                    "known_devices": list[str],
                    "event_count": int,
                    "last_seen": str  # ISO datetime string
                }
        """

    @abstractmethod
    def save_profile(self, user_id: str, profile: dict) -> None:
        """Persist a user profile, overwriting any existing one.

        Args:
            user_id: The user the profile belongs to.
            profile: The profile dict (see :meth:`get_profile` for shape).
        """

    @abstractmethod
    def log_event(self, event: Event, result: ScoreResult) -> None:
        """Persist a scored event for later querying.

        Both the raw event fields and the :class:`ScoreResult` fields are
        stored so dashboards and APIs can reconstruct the full picture.

        Args:
            event: The original :class:`~argus.schema.Event`.
            result: The :class:`~argus.schema.ScoreResult` produced for it.
        """

    @abstractmethod
    def get_recent_alerts(
        self, limit: int = 50, min_risk_level: str = "MEDIUM"
    ) -> list[dict]:
        """Return recent scored events at or above a risk level.

        Args:
            limit: Maximum number of alerts to return.
            min_risk_level: Minimum risk level to include. Risk level order is
                ``LOW < MEDIUM < HIGH < CRITICAL``.

        Returns:
            A list of scored-event dicts ordered by timestamp descending.
        """

    @abstractmethod
    def get_user_events(self, user_id: str, limit: int = 100) -> list[dict]:
        """Return recent events for a specific user, newest first.

        Args:
            user_id: The user whose events to load.
            limit: Maximum number of events to return.

        Returns:
            A list of scored-event dicts, newest first.
        """

    @abstractmethod
    def get_stats(self) -> dict:
        """Return system-wide statistics.

        Returns:
            A dict of the shape::

                {
                    "total_events": int,
                    "total_users": int,
                    "alerts_today": int,
                    "high_risk_users": list[str]
                }
        """

    @abstractmethod
    def get_dna(self, user_id: str) -> dict | None:
        """Retrieve the stored BehavioralDNA dict for a user.

        Args:
            user_id: The user whose behavioral DNA to load.

        Returns:
            The serialized BehavioralDNA dict (see
            :func:`argus.dna.dna_to_dict`), or ``None`` if none exists.
        """

    @abstractmethod
    def save_dna(self, user_id: str, dna: dict) -> None:
        """Persist a BehavioralDNA dict for a user, overwriting any existing one.

        Args:
            user_id: The user the DNA belongs to.
            dna: The serialized BehavioralDNA dict.
        """
