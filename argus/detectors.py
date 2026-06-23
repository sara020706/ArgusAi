"""Machine-learning anomaly detectors for Argus.

:class:`IsolationForestDetector` wraps scikit-learn's ``IsolationForest`` to add
an ML anomaly score as a third scoring layer on top of the rule and statistical
engines. It is intentionally optional: scikit-learn is only imported inside
:meth:`IsolationForestDetector.train`, so the core package imports cleanly
without it, and :meth:`IsolationForestDetector.score` returns ``0.0`` (a no-op
contribution) whenever the model is not trained — it never raises in the
scoring path.

The interface (``train`` / ``score`` / ``save`` / ``load``) is deliberately
small so an autoencoder or any other detector can be swapped in behind it.
"""

from __future__ import annotations

import pickle

from argus.synthetic.generator import NUMERIC_FEATURE_KEYS


class IsolationForestDetector:
    """An optional Isolation Forest anomaly-detection layer."""

    def __init__(self, contamination: float = 0.05, n_estimators: int = 100):
        """Configure (but do not train) the detector.

        Args:
            contamination: Expected fraction of anomalies in training data.
                Passed to scikit-learn's ``IsolationForest``.
            n_estimators: Number of trees in the forest.
        """
        self.contamination = contamination
        self.n_estimators = n_estimators
        self._model = None
        self.is_trained = False
        self._feature_keys: list[str] | None = None

    def train(self, feature_matrix: list[list[float]]) -> None:
        """Train the Isolation Forest on a feature matrix.

        Args:
            feature_matrix: A 2D list of numeric feature rows, e.g. from
                :func:`argus.synthetic.generator.events_to_feature_matrix`.

        Raises:
            ImportError: If scikit-learn is not installed, with guidance on how
                to install the optional ``ml`` extra.
            ValueError: If ``feature_matrix`` is empty.
        """
        try:
            from sklearn.ensemble import IsolationForest
        except ImportError as exc:  # pragma: no cover - depends on environment
            raise ImportError(
                "scikit-learn is required to train the ML detector. "
                "Install it with: pip install 'argus[ml]'  (or: pip install scikit-learn)"
            ) from exc

        if not feature_matrix:
            raise ValueError("Cannot train on an empty feature matrix.")

        self._model = IsolationForest(
            contamination=self.contamination,
            n_estimators=self.n_estimators,
            random_state=42,
        )
        self._model.fit(feature_matrix)
        # Persist the feature key order so scoring builds vectors identically.
        self._feature_keys = list(NUMERIC_FEATURE_KEYS)
        self.is_trained = True

    def _vector_to_row(self, feature_vector: dict) -> list[float]:
        """Project a feature-vector dict onto the trained column order.

        Args:
            feature_vector: The feature dict from ``build_feature_vector``.

        Returns:
            A list of floats ordered to match the training matrix columns.
        """
        keys = self._feature_keys or NUMERIC_FEATURE_KEYS
        return [float(feature_vector.get(key, 0.0)) for key in keys]

    def score(self, feature_vector: dict) -> float:
        """Score a single feature vector for anomalousness.

        Isolation Forest's ``score_samples`` returns higher (less negative)
        values for normal points and lower (more negative) values for
        anomalies. This is mapped to ``[0.0, 1.0]`` where ``1.0`` is most
        anomalous, using the model's learned ``offset_`` as the decision
        boundary.

        Args:
            feature_vector: The feature dict from ``build_feature_vector``.

        Returns:
            A float in ``[0.0, 1.0]``. Returns ``0.0`` if the model is not
            trained or if anything goes wrong (graceful fallback — never
            raises).
        """
        if not self.is_trained or self._model is None:
            return 0.0
        try:
            row = self._vector_to_row(feature_vector)
            # raw_score: higher = more normal. offset_ is the threshold such
            # that decision_function = score_samples - offset_ (negative =>
            # predicted anomaly).
            raw_score = float(self._model.score_samples([row])[0])
            offset = float(getattr(self._model, "offset_", -0.5))

            # Map raw_score relative to the offset into [0, 1]. Points well
            # below the threshold approach 1.0; points at/above it approach 0.0.
            anomaly = offset - raw_score
            # Scale: a margin of ~0.25 in the raw score saturates toward 1.0.
            normalized = anomaly / 0.25
            return max(0.0, min(1.0, normalized))
        except Exception:
            # Scoring must never break the pipeline.
            return 0.0

    def save(self, path: str) -> None:
        """Serialize the trained model to disk via pickle.

        Args:
            path: Destination file path.

        Raises:
            RuntimeError: If the detector has not been trained.
        """
        if not self.is_trained or self._model is None:
            raise RuntimeError("Cannot save an untrained detector.")
        payload = {
            "model": self._model,
            "feature_keys": self._feature_keys,
            "contamination": self.contamination,
            "n_estimators": self.n_estimators,
        }
        with open(path, "wb") as fh:
            pickle.dump(payload, fh)

    def load(self, path: str) -> None:
        """Load a previously saved model from disk.

        Args:
            path: Source file path produced by :meth:`save`.

        Side effects:
            Sets ``is_trained`` to ``True`` on success and restores the model,
            feature key order and hyperparameters.
        """
        with open(path, "rb") as fh:
            payload = pickle.load(fh)
        self._model = payload["model"]
        self._feature_keys = payload.get("feature_keys", list(NUMERIC_FEATURE_KEYS))
        self.contamination = payload.get("contamination", self.contamination)
        self.n_estimators = payload.get("n_estimators", self.n_estimators)
        self.is_trained = True
