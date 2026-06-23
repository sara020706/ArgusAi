"""Adaptive per-user behavioral baselines for Argus.

The :class:`UserProfile` maintains a rolling statistical baseline (mean and
standard deviation of download size and file-access count) plus the set of
known IPs and devices for a single user. Statistics are updated *incrementally*
using Welford's online algorithm, so the full event history never needs to be
stored or reprocessed. Profiles serialize to/from plain dicts so any
:class:`~argus.storage.ArgusStore` can persist them.
"""

from __future__ import annotations

import math
from datetime import datetime

from argus.schema import Event


class UserProfile:
    """Maintains an adaptive behavioral baseline for a single user.

    Updates incrementally via Welford's online algorithm — no raw history is
    retained. Designed to round-trip through a plain dict for storage.
    """

    def __init__(self, user_id: str):
        """Initialize an empty profile for ``user_id``.

        Args:
            user_id: The user this profile describes.
        """
        self.user_id = user_id
        self.avg_download_mb = 0.0
        self.std_download_mb = 0.0
        self.avg_files_accessed = 0.0
        self.std_files_accessed = 0.0
        self.known_ips: set[str] = set()
        self.known_devices: set[str] = set()
        self.event_count = 0
        self.last_seen: datetime | None = None
        # Welford's online algorithm state: running sum of squared deviations.
        self._download_M2 = 0.0
        self._files_M2 = 0.0

    def update(self, event: Event) -> None:
        """Incrementally fold a new event into the baseline statistics.

        Uses Welford's online algorithm to update the running mean and the M2
        accumulator for both download size and file-access count, then derives
        the (population) standard deviation. Also records the event's IP and
        device as known and advances ``last_seen``.

        In Phase 2 every event updates the baseline. Anomaly-aware filtering
        (so that malicious events do not poison the baseline) arrives in a
        later phase.

        Args:
            event: The :class:`~argus.schema.Event` to learn from.
        """
        self.event_count += 1
        n = self.event_count

        # --- Welford update for download size ---
        delta = event.download_mb - self.avg_download_mb
        self.avg_download_mb += delta / n
        delta2 = event.download_mb - self.avg_download_mb
        self._download_M2 += delta * delta2

        # --- Welford update for file-access count ---
        f_delta = event.files_accessed - self.avg_files_accessed
        self.avg_files_accessed += f_delta / n
        f_delta2 = event.files_accessed - self.avg_files_accessed
        self._files_M2 += f_delta * f_delta2

        # Population standard deviation (defined once we have >= 1 sample).
        if n > 0:
            self.std_download_mb = math.sqrt(self._download_M2 / n)
            self.std_files_accessed = math.sqrt(self._files_M2 / n)

        self.known_ips.add(event.ip)
        self.known_devices.add(event.device_id)

        if self.last_seen is None or event.timestamp > self.last_seen:
            self.last_seen = event.timestamp

    def to_dict(self) -> dict:
        """Serialize the profile to a plain, storage-friendly dict.

        Returns:
            A dict containing the baseline statistics, known IPs/devices as
            lists, event count, ISO ``last_seen`` string, and the internal
            Welford M2 accumulators so updates can resume after a reload.
        """
        return {
            "user_id": self.user_id,
            "avg_download_mb": self.avg_download_mb,
            "std_download_mb": self.std_download_mb,
            "avg_files_accessed": self.avg_files_accessed,
            "std_files_accessed": self.std_files_accessed,
            "known_ips": sorted(self.known_ips),
            "known_devices": sorted(self.known_devices),
            "event_count": self.event_count,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            # Internal Welford state, preserved so incremental updates survive
            # a serialize/deserialize round trip.
            "_download_M2": self._download_M2,
            "_files_M2": self._files_M2,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UserProfile":
        """Reconstruct a :class:`UserProfile` from a stored dict.

        Args:
            data: A dict previously produced by :meth:`to_dict` (or the profile
                shape returned by an :class:`~argus.storage.ArgusStore`).

        Returns:
            A populated :class:`UserProfile`. Missing optional keys fall back to
            empty/zero defaults so profiles stored by external backends (which
            may omit the internal Welford state) still load.
        """
        profile = cls(data["user_id"])
        profile.avg_download_mb = data.get("avg_download_mb", 0.0)
        profile.std_download_mb = data.get("std_download_mb", 0.0)
        profile.avg_files_accessed = data.get("avg_files_accessed", 0.0)
        profile.std_files_accessed = data.get("std_files_accessed", 0.0)
        profile.known_ips = set(data.get("known_ips", []))
        profile.known_devices = set(data.get("known_devices", []))
        profile.event_count = data.get("event_count", 0)

        last_seen = data.get("last_seen")
        profile.last_seen = (
            datetime.fromisoformat(last_seen) if last_seen else None
        )

        # Recover internal Welford state if present; otherwise reconstruct it
        # from the stored std so incremental updates remain approximately
        # correct after a round trip through a backend that dropped it.
        if "_download_M2" in data:
            profile._download_M2 = data["_download_M2"]
        else:
            profile._download_M2 = (
                profile.std_download_mb**2 * profile.event_count
            )
        if "_files_M2" in data:
            profile._files_M2 = data["_files_M2"]
        else:
            profile._files_M2 = (
                profile.std_files_accessed**2 * profile.event_count
            )
        return profile

    def as_scoring_profile(self) -> dict:
        """Return the profile in the dict shape the Phase 1 scorer expects.

        Returns:
            A dict with ``avg_download_mb``, ``std_download_mb``,
            ``avg_files_accessed``, ``std_files_accessed``, ``known_ips`` and
            ``known_devices`` (the last two as lists).
        """
        return {
            "avg_download_mb": self.avg_download_mb,
            "std_download_mb": self.std_download_mb,
            "avg_files_accessed": self.avg_files_accessed,
            "std_files_accessed": self.std_files_accessed,
            "known_ips": sorted(self.known_ips),
            "known_devices": sorted(self.known_devices),
        }

    def is_mature(self, min_events: int = 20) -> bool:
        """Report whether the profile has enough events to be reliable.

        Below ``min_events`` the statistical baseline is too noisy for
        deviation-based scoring to be trustworthy.

        Args:
            min_events: Minimum event count to consider the profile mature.
                Defaults to 20.

        Returns:
            ``True`` if ``event_count >= min_events``, else ``False``.
        """
        return self.event_count >= min_events
