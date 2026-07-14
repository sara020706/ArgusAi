"""Argus - AI-powered insider threat and anomalous behavior detection.

Public API:

    from argus import Event, ScoreResult, score
    from argus import ArgusEngine, UserProfile
    from argus.storage import ArgusStore, SQLiteStore, MemoryStore
    from argus.explainer import build_explanation, summarize_result

Two ways to use Argus:

* **Stateless** - call :func:`score` with an :class:`Event` and a profile dict
  you manage yourself (Phase 1 behaviour).
* **Stateful** - use :class:`ArgusEngine`, which loads/creates user profiles
  from a storage backend, scores the event, and updates the baseline
  automatically.
"""

from __future__ import annotations

from argus.correlator import correlate
from argus.detectors import IsolationForestDetector
from argus.dna import (
    BehavioralDNA,
    detect_drift,
    dna_from_dict,
    dna_to_dict,
    drift_to_score_bonus,
    update_dna,
)
from argus.explainer import build_explanation, summarize_result
from argus.integrations import ThreatIntelClient
from argus.profile import UserProfile
from argus.schema import Event, ScoreResult
from argus.scorer import cap_score, compute_score, get_risk_level
from argus.storage import ArgusStore, MemoryStore, SQLiteStore

__version__ = "0.1.0"

__all__ = [
    "Event",
    "ScoreResult",
    "score",
    "compute_score",
    "build_explanation",
    "summarize_result",
    "UserProfile",
    "ArgusStore",
    "SQLiteStore",
    "MemoryStore",
    "ArgusEngine",
    "IsolationForestDetector",
    "ThreatIntelClient",
    "correlate",
    "BehavioralDNA",
]


def score(event: Event, user_profile: dict) -> ScoreResult:
    """Score a single event against a user profile.

    This is the stateless entry point and is a thin convenience wrapper around
    :func:`argus.scorer.compute_score` using default weights.

    Args:
        event: The :class:`Event` to score.
        user_profile: The user's historical profile dict. See
            ``argus.features.build_feature_vector`` for the required keys.

    Returns:
        A :class:`ScoreResult` with the risk score, level, contributions and
        reasons.
    """
    return compute_score(event, user_profile)


class ArgusEngine:
    """Stateful scoring engine that manages user profiles via a storage backend.

    The engine loads (or creates) a user's profile, scores an incoming event,
    updates the user's behavioral baseline with that event, and persists both
    the updated profile and the scored event. This is the recommended entry
    point for applications that want Argus to manage profiles automatically.

    Applications with their own database can pass a custom
    :class:`~argus.storage.ArgusStore` implementation.
    """

    def __init__(
        self,
        store: ArgusStore | None = None,
        detector: IsolationForestDetector | None = None,
        threat_intel: ThreatIntelClient | None = None,
    ):
        """Initialize the engine with a storage backend and optional layers.

        Args:
            store: Storage backend. Defaults to ``SQLiteStore("argus.db")`` if
                ``None``. Pass :class:`~argus.storage.MemoryStore` for testing,
                or your own :class:`~argus.storage.ArgusStore` to use your
                app's database.
            detector: Optional ML anomaly detector. If ``None`` (default), the
                ML scoring layer is disabled and Argus uses rules + statistics
                only.
            threat_intel: Optional :class:`~argus.integrations.ThreatIntelClient`.
                If ``None`` (default), the IP-reputation layer is disabled.
        """
        self.store = store or SQLiteStore()
        self.detector = detector  # None = ML layer disabled
        self.threat_intel = threat_intel  # None = threat-intel layer disabled

    def get_or_create_profile(self, user_id: str) -> UserProfile:
        """Load a user's profile from the store, or create a fresh one.

        Args:
            user_id: The user to load or create a profile for.

        Returns:
            A :class:`~argus.profile.UserProfile`, hydrated from storage if it
            exists, otherwise empty.
        """
        stored = self.store.get_profile(user_id)
        if stored is not None:
            return UserProfile.from_dict(stored)
        return UserProfile(user_id)

    def score(self, event: Event) -> ScoreResult:
        """Score an event and update the user's baseline.

        Steps:
            1. Load or create the user's profile from the store.
            2. Score the event with Phase 1 :func:`compute_score`.
            3. Update the user's baseline with this event.
            4. Persist the updated profile and the scored event.
            5. Return the :class:`ScoreResult`.

        Args:
            event: The :class:`Event` to score.

        Returns:
            The :class:`ScoreResult` for the event.
        """
        profile = self.get_or_create_profile(event.user_id)

        # Score against the profile state *before* folding in this event, so a
        # user's own current event cannot mask its own anomaly.
        scoring_profile = profile.as_scoring_profile()

        # Cold-start handling: a brand-new user has no known IPs/devices, so
        # their very first event would otherwise always look like it came from
        # an unrecognized IP and device. We have no baseline to judge novelty
        # against yet, so treat the first event's IP/device as known and skip
        # the novelty penalty until there is history to compare against.
        if profile.event_count == 0:
            scoring_profile["known_ips"] = [event.ip]
            scoring_profile["known_devices"] = [event.device_id]

        result = compute_score(event, scoring_profile)

        # Apply optional layers on top of the base rule + statistical score
        # before persisting: ML anomaly, then IP threat intel, then multi-event
        # correlation (which needs this event included in the window), then the
        # behavioral DNA drift layer.
        self._apply_ml_layer(result)
        self._apply_threat_intel_layer(event, result)
        self._apply_correlation_layer(event, result)
        self._apply_dna_layer(event, result)

        # Learn from the event, then persist updated baseline and the result.
        profile.update(event)
        self.store.save_profile(event.user_id, profile.to_dict())
        self.store.log_event(event, result)

        return result

    def _apply_dna_layer(self, event: Event, result: ScoreResult) -> None:
        """Add behavioral-DNA drift points to a result, then update the DNA.

        Loads (or creates) the user's :class:`~argus.dna.BehavioralDNA`,
        detects drift *against the historical baseline before* folding in the
        current event, applies any drift score bonus to the result, then
        updates the fingerprint with this event and persists it.

        The drift detection step never raises (see
        :func:`~argus.dna.detect_drift`), so a malformed DNA blob cannot break
        scoring.

        Args:
            event: The event being scored.
            result: The :class:`ScoreResult` to augment in place.
        """
        stored = self.store.get_dna(event.user_id)
        dna = dna_from_dict(stored) if stored else BehavioralDNA(event.user_id)

        # Detect drift against the historical baseline *before* this event is
        # folded in, so the current event cannot mask its own anomaly.
        drift = detect_drift(dna)
        points, reason = drift_to_score_bonus(drift)
        if points > 0 and reason is not None:
            # Store the plain point value (not a tuple) so the explainer's
            # numeric ranking pool stays consistent with rule_contributions.
            result.stat_contributions["behavioral_dna"] = points
            result.reasons.append(reason)
            result.risk_score = cap_score(result.risk_score + points)
            result.risk_level = get_risk_level(result.risk_score)

        # Fold the current event into the fingerprint and persist it.
        update_dna(dna, event)
        self.store.save_dna(event.user_id, dna_to_dict(dna))

    def _apply_threat_intel_layer(self, event: Event, result: ScoreResult) -> None:
        """Add IP-reputation threat points to a result, in place.

        Only runs if a :class:`~argus.integrations.ThreatIntelClient` is
        configured. Adds the points and reason for a flagged IP, re-caps the
        score, and recomputes the risk level.

        Args:
            event: The event being scored (for its IP).
            result: The :class:`ScoreResult` to augment in place.
        """
        if self.threat_intel is None:
            return
        points, reason = self.threat_intel.get_threat_points(event.ip)
        if points <= 0 or reason is None:
            return
        result.stat_contributions["threat_intel"] = (points, reason)
        result.reasons.append(reason)
        result.risk_score = cap_score(result.risk_score + points)
        result.risk_level = get_risk_level(result.risk_score)

    def _apply_correlation_layer(self, event: Event, result: ScoreResult) -> None:
        """Add multi-event correlation bonus points to a result, in place.

        Loads the user's recent events from the store, appends a synthetic dict
        for the current (not-yet-persisted) event so it participates in the
        window, runs :func:`~argus.correlator.correlate`, and applies any bonus
        points and pattern reasons. Re-caps the score and recomputes the level.

        Args:
            event: The event being scored.
            result: The :class:`ScoreResult` to augment in place.
        """
        recent = self.store.get_user_events(event.user_id, limit=100)
        # Include the current event (not yet persisted) in the correlation
        # window so single-shot patterns can still fire on it.
        recent = recent + [
            {
                "user_id": event.user_id,
                "timestamp": event.timestamp.isoformat(),
                "ip": event.ip,
                "device_id": event.device_id,
                "download_mb": event.download_mb,
                "files_accessed": event.files_accessed,
                "action": event.action,
                "rule_contributions": result.rule_contributions,
                "stat_contributions": result.stat_contributions,
            }
        ]
        bonus, reasons = correlate(event.user_id, result, recent)
        if bonus <= 0:
            return
        result.stat_contributions["correlation"] = (bonus, "; ".join(reasons))
        result.reasons.extend(reasons)
        result.risk_score = cap_score(result.risk_score + bonus)
        result.risk_level = get_risk_level(result.risk_score)

    def _apply_ml_layer(self, result: ScoreResult) -> None:
        """Add the ML anomaly contribution to a result, in place.

        Only runs if a detector is configured and trained. Contributes up to
        20 additional points (so rules + statistics remain the primary signal),
        re-caps the score at 100, and recomputes the risk level.

        Args:
            result: The :class:`ScoreResult` to augment in place.
        """
        if self.detector is None or not self.detector.is_trained:
            return

        ml_score = self.detector.score(result.raw_features)
        ml_points = ml_score * 20.0  # max 20 additional points from ML
        if ml_points <= 0:
            return

        reason = f"ML anomaly score: {ml_score:.2f}"
        result.stat_contributions["ml_isolation_forest"] = (ml_points, reason)
        result.reasons.append(reason)
        result.risk_score = cap_score(result.risk_score + ml_points)
        result.risk_level = get_risk_level(result.risk_score)

    def train(
        self,
        events: list[Event] | None = None,
        n_users: int = 10,
        days: int = 30,
    ) -> None:
        """Train the ML detector and persist it to ``argus_model.pkl``.

        If ``events`` is provided, the detector trains on those. Otherwise a
        synthetic dataset is generated automatically. After training the model
        is saved to ``argus_model.pkl`` in the current directory.

        Args:
            events: Optional events to train on. If ``None``, synthetic data is
                generated via
                :func:`argus.synthetic.generator.generate_dataset`.
            n_users: Number of synthetic users (used only when ``events`` is
                ``None``).
            days: Number of synthetic days (used only when ``events`` is
                ``None``).

        Raises:
            RuntimeError: If no detector was configured on this engine.
        """
        from argus.synthetic.generator import (
            events_to_feature_matrix,
            generate_dataset,
        )

        if self.detector is None:
            raise RuntimeError(
                "No detector configured. Construct ArgusEngine with a detector, "
                "e.g. ArgusEngine(detector=IsolationForestDetector())."
            )

        if events is None:
            events, _labels = generate_dataset(n_users=n_users, days=days)

        # Build per-user scoring profiles from the training events so feature
        # z-scores reflect each user's own baseline.
        profiles: dict[str, dict] = {}
        per_user: dict[str, UserProfile] = {}
        for event in events:
            up = per_user.setdefault(event.user_id, UserProfile(event.user_id))
            up.update(event)
        for user_id, up in per_user.items():
            profiles[user_id] = up.as_scoring_profile()

        matrix = events_to_feature_matrix(events, profiles)
        self.detector.train(matrix)
        self.detector.save("argus_model.pkl")

    def get_recent_alerts(
        self, limit: int = 50, min_risk_level: str = "MEDIUM"
    ) -> list[dict]:
        """Return recent alerts from the store. Proxy to ``store.get_recent_alerts``.

        Args:
            limit: Maximum number of alerts to return.
            min_risk_level: Minimum risk level to include.

        Returns:
            A list of scored-event dicts, newest first.
        """
        return self.store.get_recent_alerts(limit=limit, min_risk_level=min_risk_level)

    def get_user_events(self, user_id: str, limit: int = 100) -> list[dict]:
        """Return recent events for a user. Proxy to ``store.get_user_events``.

        Args:
            user_id: The user whose events to return.
            limit: Maximum number of events to return.

        Returns:
            A list of scored-event dicts, newest first.
        """
        return self.store.get_user_events(user_id, limit=limit)

    def get_stats(self) -> dict:
        """Return system-wide statistics. Proxy to ``store.get_stats``.

        Returns:
            The system stats dict (see :meth:`ArgusStore.get_stats`).
        """
        return self.store.get_stats()

    def get_dna(self, user_id: str) -> BehavioralDNA | None:
        """Load and deserialize a user's behavioral DNA fingerprint.

        Args:
            user_id: The user whose DNA to load.

        Returns:
            The :class:`~argus.dna.BehavioralDNA`, or ``None`` if the user has
            no DNA profile yet.
        """
        data = self.store.get_dna(user_id)
        if not data:
            return None
        return dna_from_dict(data)
